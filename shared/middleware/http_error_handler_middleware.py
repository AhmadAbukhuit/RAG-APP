# middleware/http_error_handler_middleware.py
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.http.http_responses import HttpResponse
from shared.http.http_exceptions import HttpError
from shared.logger.logger import get_logger

logger = get_logger()

async def http_error_handler(request: Request, exc: Exception):
    """
    Custom error handler for all exceptions.
    Returns JSON response with HttpResponse structure.
    """
    if isinstance(exc, HttpError):
        # Custom application exception (Uses .message as defined in your class)
        return JSONResponse(
            status_code=exc.status_code,
            content=HttpResponse(
                status_code=exc.status_code,
                data=None,
                message=str(exc.message),
                code=getattr(exc, "code", "ERROR")
            ).dict()
        )

    if isinstance(exc, StarletteHTTPException):
        # Handles standard FastAPI/Starlette exceptions (404, 401, etc.)
        status_code = exc.status_code
        
        # Standard exceptions use .detail for the text description
        message = exc.detail if getattr(exc, "detail", None) else "HTTP Error"
        
        # Fallback for empty details on 404
        if status_code == 404 and message == "Not Found": 
             # (optional: customize 404 message further if needed)
             pass

        code = "NOT_FOUND" if status_code == 404 else f"HTTP_{status_code}"
        
        return JSONResponse(
            status_code=status_code,
            content=HttpResponse(
                status_code=status_code,
                data=None,
                message=message,
                code=code
            ).dict()
        )

    # Unhandled exceptions
    logger.error(f"Unexpected error in controller: {exc}")
    return JSONResponse(
        status_code=500,
        content=HttpResponse(
            status_code=500,
            data=None,
            message="Internal Server Error: " + str(exc),
            code="INTERNAL_SERVER_ERROR"
        ).dict()
    )