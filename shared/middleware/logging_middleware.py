# middlewares/logging_middleware.py
import time
import uuid
from fastapi import Request

from shared.logger.logger import get_logger
from shared.context import request_id_ctx 

async def global_logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request_id_ctx.set(request_id)

    logger = get_logger()
    
    # Log Request
    logger.info(f"Incoming Request: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        
        process_time = time.time() - start_time
        
        # Log Response
        logger.info(
            f"Request Completed: {request.method} {request.url.path} "
            f"- Status: {response.status_code} - Duration: {process_time:.3f}s"
        )
        
        response.headers["X-Request-ID"] = request_id
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(
            f"Request Failed: {request.method} {request.url.path} "
            f"- Error: {str(e)} - Duration: {process_time:.3f}s"
        )
        raise e