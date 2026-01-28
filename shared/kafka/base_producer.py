import asyncio
import json
import os
from typing import Any, Optional
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError, NodeNotReadyError

from shared.logger.logger import get_logger

# Configure logger
logger = get_logger()

class KafkaProducerService:
    def __init__(
        self,
        bootstrap_servers: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"),
        value_serializer=None,
        retries: int = 5,
        retry_delay: int = 5,
    ):
        self.bootstrap_servers = bootstrap_servers
        # Default serializer: JSON -> UTF-8 bytes
        self.value_serializer = value_serializer or self._default_serializer
        self.retries = retries
        self.retry_delay = retry_delay
        self._producer: Optional[AIOKafkaProducer] = None

    @staticmethod
    def _default_serializer(value: Any) -> bytes:
        if value is None:
            return None # Allows sending tombstones (null payloads)
        return json.dumps(value).encode("utf-8")

    async def start(self):
        for attempt in range(1, self.retries + 1):
            try:
                self._producer = AIOKafkaProducer(
                    bootstrap_servers=self.bootstrap_servers,
                    value_serializer=self.value_serializer,
                )
                await self._producer.start()
                logger.info(f"[KafkaProducerService] Connected to {self.bootstrap_servers}")
                return
            except (KafkaConnectionError, NodeNotReadyError, OSError) as e:
                logger.warning(f"[KafkaProducerService] Connection Retry {attempt}/{self.retries}: {e}")
                if attempt == self.retries:
                    logger.error("[KafkaProducerService] Max retries reached.")
                    raise
                await asyncio.sleep(self.retry_delay)

    async def send(self, topic: str, value: Any, key: Optional[bytes] = None):
        """
        Sends a message and awaits acknowledgment.
        """
        if not self._producer:
            raise RuntimeError("Producer not started. Call await producer.start() first.")
        
        try:
            # send_and_wait ensures the broker received the message
            await self._producer.send_and_wait(topic, value=value, key=key)
        except Exception as e:
            logger.error(f"[KafkaProducerService] Failed to send message to {topic}: {e}")
            raise

    async def stop(self):
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("[KafkaProducerService] Stopped cleanly")