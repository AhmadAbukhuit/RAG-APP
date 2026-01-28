import asyncio
import os
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from settings.settings import settings
from services.logger_service import handle_message
from utils.logger_util import get_file_logger

logger = get_file_logger()

class KafkaLogsConsumer:
    def __init__(self, topic, group_id, auto_offset_reset="latest", max_retries=5, retry_backoff=5):
        self.topic = topic
        self.group_id = group_id
        self.auto_offset_reset = auto_offset_reset
        self.max_retries = max_retries
        self.retry_backoff = retry_backoff
        self.consumer = None
        self._running = False

    async def start(self, handler, batch_size=1000, timeout_ms=100):
        self._running = True
        retries = 0

        while self._running:
            try:
                self.consumer = AIOKafkaConsumer(
                    self.topic,
                    group_id=self.group_id,
                    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS, # ✅ Use settings
                    auto_offset_reset=self.auto_offset_reset,
                    max_poll_records=batch_size,
                    enable_auto_commit=True
                )

                await self.consumer.start()
                print(f"✅ [LoggerService] Connected to Kafka: {settings.KAFKA_BOOTSTRAP_SERVERS}")
                retries = 0 # Reset retries on success

                while self._running:
                    result = await self.consumer.getmany(timeout_ms=timeout_ms, max_records=batch_size)
                    if not result:
                        continue
                    
                    for _, messages in result.items():
                        for msg in messages:
                            if not self._running: break
                            await handler(msg)
                            
                    # Auto-commit is enabled, but manual commit gives more control if needed
                    # await self.consumer.commit() 

            except KafkaConnectionError as e:
                retries += 1
                print(f"⚠️ Kafka connection failed ({retries}/{self.max_retries}): {e}")
                if self.max_retries != -1 and retries >= self.max_retries:
                    print("❌ Max retries reached. Exiting consumer.")
                    raise
                await asyncio.sleep(self.retry_backoff)
            except Exception as e:
                print(f"❌ Consumer error: {e}")
                await asyncio.sleep(1) # Prevent tight loop on unknown errors
            finally:
                if self.consumer:
                    await self.consumer.stop()
                    self.consumer = None

    def stop(self):
        self._running = False

async def start_consumer():
    consumer = KafkaLogsConsumer(
        topic=settings.KAFKA_LOGS_TOPIC,
        group_id=settings.KAFKA_LOGS_GROUP_ID,
    )
    # Start the loop
    await consumer.start(handle_message)