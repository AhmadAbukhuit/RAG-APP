# shared/logger/logger_decorators.py
import functools
import inspect
from time import time
from shared.logger.logger import get_logger
from shared.context import request_id_ctx

def log_method_call(func):
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger()
        request_id = request_id_ctx.get("system")
        
        logger.debug(f"[{request_id}] Calling async {func.__name__}")
        start = time()
        
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            duration = time() - start
            logger.debug(f"[{request_id}] {func.__name__} completed in {duration:.3f}s")

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger()
        request_id = request_id_ctx.get("system")
        
        logger.debug(f"[{request_id}] Calling sync {func.__name__}")
        start = time()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time() - start
            logger.debug(f"[{request_id}] {func.__name__} completed in {duration:.3f}s")

    # Detect if the function is async and return the appropriate wrapper
    if inspect.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper