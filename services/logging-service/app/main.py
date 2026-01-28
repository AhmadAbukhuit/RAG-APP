import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

# Correct import path based on the folder structure
from controllers.logger_kafka_controller import start_consumer
from utils.logger_util import get_file_logger
from settings.settings import settings

logger = get_file_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    logger.info({"service": "logging-service", "message": "Starting logging service..."})
    
    # Run consumer in background task
    task = asyncio.create_task(start_consumer())
    
    yield
    
    # --- SHUTDOWN ---
    logger.info({"service": "logging-service", "message": "Shutting down logging service..."})
    # Ideally, you would call consumer.stop() here if you exposed the consumer instance
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title=settings.SERVICE_NAME,
    description=settings.SERVICE_DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {"status": 200, "message": "Logging Service Running"}