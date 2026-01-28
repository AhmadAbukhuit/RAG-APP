import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVICE_NAME: str = os.getenv("SERVICE_NAME", "logging-service")
    SERVICE_DESCRIPTION: str = "Logging Service"
    VERSION: str = "1.0.0"

    # External services
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379")

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_LOGS_TOPIC: str = os.getenv("KAFKA_LOGS_TOPIC", "logs")
    KAFKA_LOGS_GROUP_ID: str = os.getenv("KAFKA_LOGS_GROUP_ID", "logs-group")

    # Local Storage
    LOG_FOLDER: str = os.getenv("LOG_FOLDER", "/storage-shared/logs")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "DEBUG")

    # MinIO (S3 Compatible)
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
    MINIO_ACCESS_KEY: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    MINIO_SECRET_KEY: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    MINIO_BUCKET: str = os.getenv("MINIO_BUCKET", "logs-bucket")
    MINIO_REGION: str = os.getenv("MINIO_REGION", "us-east-1")

    class Config:
        env_file = ".env"

settings = Settings()