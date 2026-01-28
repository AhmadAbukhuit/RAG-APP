import logging
import json
import os
import gzip
import shutil
import threading
from logging.handlers import TimedRotatingFileHandler
from settings.settings import settings
from services.storage_service import upload_and_cleanup

def get_file_logger(name="logging-service", backup_count=5):
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.propagate = False
        logger.setLevel(logging.INFO)

        os.makedirs(settings.LOG_FOLDER, exist_ok=True)
        log_file = os.path.join(settings.LOG_FOLDER, "app.log") 

        # Rotate daily at midnight
        handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=backup_count, # Keep recent files locally if needed
            encoding="utf-8",
            utc=True
        )
        handler.suffix = "%Y-%m-%d"

        # 1. Namer: Define the format of the rotated file (add .gz)
        handler.namer = lambda name: f"{name}.gz"

        # 2. Rotator: Custom logic to compress -> delete raw -> upload
        def rotator(src, dest):
            # A. Compress the raw rotated file
            try:
                with open(src, "rb") as f_in, gzip.open(dest, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            except Exception as e:
                print(f"Error compressing log file: {e}")
                return

            # B. Remove the uncompressed source file immediately
            if os.path.exists(src):
                os.remove(src)

            # C. Trigger MinIO Upload in Background (Non-blocking)
            # We pass 'dest' (the .gz file path) to the uploader
            upload_thread = threading.Thread(target=upload_and_cleanup, args=(dest,))
            upload_thread.start()

        handler.rotator = rotator

        # JSON formatter
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                if isinstance(record.msg, dict):
                    return json.dumps(record.msg, default=str)
                return str(record.msg)

        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger