# shared/logger/logger.py
import logging
import os
import asyncio
import json
import threading
from datetime import datetime, timezone
from shared.context import request_id_ctx
from aiokafka import AIOKafkaProducer 

_lock = threading.Lock()

class KafkaLogHandler(logging.Handler):
    def __init__(self, bootstrap_servers: str, topic: str, queue_size: int = 10000):
        super().__init__()
        self.topic = topic
        self.bootstrap_servers = bootstrap_servers
        self.queue_size = queue_size
        self.producer = None
        self.queue = None
        self.loop = None
        self.is_ready = False

    def _initialize_async_resources(self):
        """
        Attempts to grab the running loop of the main application.
        """
        if self.loop is None:
            try:
                self.loop = asyncio.get_running_loop()
            except RuntimeError:
                # ❌ DO NOT create a new loop here. It causes zombie loops.
                # Just return; we will fallback to print() until the loop is ready.
                return
        
        if self.queue is None and self.loop:
            self.queue = asyncio.Queue(maxsize=self.queue_size)

        if self.producer is None and self.loop:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=self.bootstrap_servers, 
                loop=self.loop
            )
            # Start the background task
            self.loop.create_task(self.start_producer_and_consumer())
            self.is_ready = True

    async def start_producer_and_consumer(self):
        """
        Tries to connect to Kafka. If it fails, it retries in a loop 
        without crashing the application.
        """
        backoff = 2
        while True:
            try:
                # 1. Try to start the producer
                await self.producer.start()
                
                # 2. If successful, log it (only once)
                print(f"✅ Kafka Logger connected to {self.bootstrap_servers}", flush=True)
                
                # 3. Start draining the queue (this runs forever until shutdown)
                await self.consume_queue()
                
                # If consume_queue returns, it means we are shutting down
                break

            except asyncio.CancelledError:
                # Task was cancelled during sleep or start
                break

            except Exception as e:
                # 4. Connection failed? Wait and retry.
                print(f"⚠️ Kafka Logger connection failed: {e}. Retrying in {backoff}s...", flush=True)
                try:
                    await asyncio.sleep(backoff)
                    # Exponential backoff (cap at 30s)
                    backoff = min(backoff * 2, 30) 
                except asyncio.CancelledError:
                    break

    async def consume_queue(self):
        while True:
            try:
                log_entry = await self.queue.get()
                message = json.dumps(log_entry).encode('utf-8')
                await self.producer.send(self.topic, value=message, key=b"log_key")
                self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ KAFKA QUEUE ERROR: {e}", flush=True)

    def emit(self, record):
        # 1. Always format the log entry
        try:
            request_id = request_id_ctx.get("system")
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
                "level": record.levelname,
                "request_id": request_id,
                "service": os.getenv("SERVICE_NAME", "unknown-service"),
                "message": record.getMessage(),
                "logger": record.name
            }
            if isinstance(record.msg, dict):
                log_entry.update({k: v for k, v in record.msg.items() if k != "message"})

            # 2. Try to initialize if not ready
            if not self.is_ready:
                self._initialize_async_resources()

            # 3. Dispatch to Async Loop if available
            if self.is_ready and self.loop and self.loop.is_running():
                try:
                    self.loop.call_soon_threadsafe(self.queue.put_nowait, log_entry)
                except asyncio.QueueFull:
                    # Fallback to print if queue is full
                    print(f"⚠️ LOG QUEUE FULL: {log_entry['message']}", flush=True)
            else:
                # 4. Fallback: If loop isn't running (e.g. startup), just print json to stdout
                # This ensures we don't lose startup logs
                print(json.dumps(log_entry), flush=True)

        except Exception as e:
            print(f"❌ LOG HANDLER FATAL ERROR: {e}", flush=True)

def get_logger():
    service_name = os.getenv("SERVICE_NAME", "unknown-service")
    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.getenv("KAFKA_LOGS_TOPIC", "logs")
    log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.DEBUG)

    with _lock:
        logger = logging.getLogger(service_name)
        
        # Only configure if handlers haven't been set up
        if not logger.handlers:
            logger.setLevel(log_level)
            logger.propagate = False
            
            # 1. Add Console Handler (Always useful for local dev & immediate feedback)
            console_handler = logging.StreamHandler()
            console_handler.setLevel(log_level)
            formatter = logging.Formatter(
                '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

            # 2. Add Kafka Handler (if not disabled via env var)
            if os.getenv("ENABLE_KAFKA_LOGGING", "true").lower() == "true":
                kafka_handler = KafkaLogHandler(bootstrap_servers, topic)
                kafka_handler.setLevel(log_level)
                logger.addHandler(kafka_handler)

    return logger