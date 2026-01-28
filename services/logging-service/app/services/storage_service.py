import boto3
import os
import logging
from botocore.client import Config
from botocore.exceptions import ClientError
from settings.settings import settings

# Use a specific logger for storage actions to avoid infinite recursion
# (i.e., don't log upload events to the same logger that triggers uploads)
logger = logging.getLogger("storage-service")
logger.setLevel(logging.INFO)
sh = logging.StreamHandler()
logger.addHandler(sh)

def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
        config=Config(signature_version="s3v4"),
        region_name=settings.MINIO_REGION
    )

def ensure_bucket_exists(s3_client):
    try:
        s3_client.head_bucket(Bucket=settings.MINIO_BUCKET)
    except ClientError:
        try:
            s3_client.create_bucket(Bucket=settings.MINIO_BUCKET)
            logger.info(f"Created bucket: {settings.MINIO_BUCKET}")
        except Exception as e:
            logger.error(f"Failed to create bucket: {e}")

def upload_and_cleanup(file_path: str):
    """
    Uploads the file to MinIO and deletes it from local disk.
    This function is intended to be run in a background thread.
    """
    try:
        s3 = get_s3_client()
        ensure_bucket_exists(s3)

        file_name = os.path.basename(file_path)
        # Structure: logs/logging-service/2023-10-27.app.log.gz
        object_name = f"logs/{settings.SERVICE_NAME}/{file_name}"

        logger.info(f"Uploading {file_name} to MinIO...")
        
        s3.upload_file(file_path, settings.MINIO_BUCKET, object_name)
        
        logger.info(f"✅ Upload successful: {object_name}")

        # Cleanup local file to save space
        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        logger.error(f"❌ Failed to upload {file_path}: {e}")