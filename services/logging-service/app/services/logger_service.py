import json
from utils.logger_util import get_file_logger

logger = get_file_logger()

async def handle_message(msg):
    """
    Process a single Kafka message.
    Decodes bytes -> JSON -> Dict -> Logs to file.
    """
    try:
        # 1. Deserialize bytes to string, then to dict
        if msg.value:
            value_str = msg.value.decode("utf-8")
            log_entry = json.loads(value_str)
            
            # 2. Log the dictionary (JsonFormatter handles the rest)
            logger.info(log_entry)
            
    except json.JSONDecodeError:
        # Handle cases where message isn't valid JSON
        logger.warning({
            "service": "logging-service",
            "message": "Received non-JSON log entry",
            "raw_data": str(msg.value)
        })
    except Exception as e:
        logger.error({
            "service": "logging-service",
            "message": "Error processing log message",
            "error": str(e),
            "topic": msg.topic,
            "partition": msg.partition
        })