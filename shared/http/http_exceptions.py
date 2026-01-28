# shared/http/http_exceptions.py
from fastapi import HTTPException
from shared.logger.logger import get_logger

logger = get_logger()  # Shared logger instance

class HttpError(HTTPException):
    def __init__(self, status_code: int, message: str = None, code: str = None):
        self.message = message or "An error occurred"
        self.code = code or self.__class__.__name__.upper()
        super().__init__(status_code=status_code)
        # Log debug info when error is created
        logger.debug(f"[HttpError Created] status_code={status_code}, code={self.code}")


class HttpBadRequestError(HttpError):
    def __init__(self, message: str = "Bad Request Error", code: str = "BAD_REQUEST_ERROR"):
        super().__init__(400, message, code)


class HttpUnauthorizedError(HttpError):
    def __init__(self, message: str = "Unauthorized Error", code: str = "UNAUTHORIZED_ERROR"):
        super().__init__(401, message, code)


class HttpForbiddenError(HttpError):
    def __init__(self, message: str = "Forbidden Error", code: str = "FORBIDDEN_ERROR"):
        super().__init__(403, message, code)


class HttpNotFoundError(HttpError):
    def __init__(self, message: str = "Not Found Error", code: str = "NOT_FOUND_ERROR"):
        super().__init__(404, message, code)


class HttpInternalServerError(HttpError):
    def __init__(self, message: str = "Internal Server Error", code: str = "INTERNAL_SERVER_ERROR"):
        super().__init__(500, message, code)