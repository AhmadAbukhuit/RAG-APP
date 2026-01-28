import asyncio
import json
import os
from typing import Callable, Awaitable, Any, Optional
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError, NodeNotReadyError

from shared.logger.logger import get_logger

# Configure logger
logger = get_logger()

class KafkaConsumerService:
    def __init__(
        self,
        topic: str,
        group_id: str,
        bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        value_deserializer: Optional[Callable[[bytes], Any]] = None,
        max_concurrent_tasks: int = 32,
        auto_offset_reset: str = "earliest",
    ):
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        
        # Safe deserializer that handles None (tombstones) and encoding errors
        self.value_deserializer = value_deserializer or self._default_deserializer
        
        self.max_concurrent_tasks = max_concurrent_tasks
        self.auto_offset_reset = auto_offset_reset

        self.consumer: Optional[AIOKafkaConsumer] = None
        self.semaphore = asyncio.Semaphore(max_concurrent_tasks)
        self.tasks: set[asyncio.Task] = set()
        self._stopping = asyncio.Event()

    @staticmethod
    def _default_deserializer(value: bytes):
        if value is None:
            return None
        try:
            return json.loads(value.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("Failed to deserialize message, returning raw bytes")
            return value

    async def start(
        self,
        message_handler: Callable[[Any], Awaitable[None]],
        retries: int = 10,
        retry_delay: int = 5,
    ):
        """
        Connects to Kafka and starts the consumption loop.
        
        :param message_handler: Async function to process messages. 
                                Receives the deserialized value (or record object depending on preference).
        """
        for attempt in range(1, retries + 1):
            try:
                self.consumer = AIOKafkaConsumer(
                    self.topic,
                    bootstrap_servers=self.bootstrap_servers,
                    group_id=self.group_id,
                    value_deserializer=self.value_deserializer,
                    auto_offset_reset=self.auto_offset_reset,
                    enable_auto_commit=True,
                )
                await self.consumer.start()
                logger.info(f"[KafkaConsumerService] Connected to {self.bootstrap_servers}, topic={self.topic}")
                break
            except (KafkaConnectionError, NodeNotReadyError, OSError) as e:
                logger.warning(f"[KafkaConsumerService] Connection Retry {attempt}/{retries}: {e}")
                if attempt == retries:
                    logger.error("[KafkaConsumerService] Max retries reached. Could not connect.")
                    raise
                await asyncio.sleep(retry_delay)

        await self._consume_loop(message_handler)

    async def _consume_loop(self, handler: Callable[[Any], Awaitable[None]]):
        assert self.consumer is not None
        try:
            while not self._stopping.is_set():
                try:
                    # Use a short timeout to allow checking self._stopping frequently
                    results = await self.consumer.getmany(timeout_ms=1000, max_records=100)
                    
                    for _, msgs in results.items():
                        for msg in msgs:
                            # Backpressure: wait if too many tasks are running
                            await self.semaphore.acquire()
                            
                            task = asyncio.create_task(self._safe_handle(handler, msg))
                            self.tasks.add(task)
                            task.add_done_callback(self.tasks.discard)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"[KafkaConsumerService] Unexpected error in consume loop: {e}")
                    await asyncio.sleep(1) # Prevent tight loop on error

        finally:
            await self.stop()

    async def _safe_handle(self, handler, msg):
        try:
            # We pass the full message object (msg) so handler can access metadata (topic, partition, key)
            # msg.value contains the deserialized data
            await handler(msg)
        except Exception as e:
            logger.error(f"[KafkaConsumerService] Error processing message: {e}")
        finally:
            self.semaphore.release()

    async def stop(self):
        """Gracefully stops the consumer and waits for pending tasks."""
        if self._stopping.is_set() and not self.consumer:
            return

        logger.info("[KafkaConsumerService] Stopping...")
        self._stopping.set()

        # 1. Stop fetching new messages
        if self.consumer:
            await self.consumer.stop()
            self.consumer = None

        # 2. Wait for pending tasks to finish
        if self.tasks:
            logger.info(f"[KafkaConsumerService] Waiting for {len(self.tasks)} pending tasks...")
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        logger.info("[KafkaConsumerService] Stopped cleanly")