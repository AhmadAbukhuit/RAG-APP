from typing import Any, Generic, TypeVar
from pydantic import BaseModel

from shared.logger.logger import get_logger

logger = get_logger()  # Shared logger instance

T = TypeVar("T")

class HttpResponse(BaseModel, Generic[T]):
    status_code: int
    code: str
    message: str
    data: Any = None

    def log_debug(self):
        logger.debug(f"[HttpResponse] status_code={self.status_code}, code={self.code}, message={self.message}, data={self.data}")

class HttpOkResponse(HttpResponse[T]):
    def __init__(self, data: T = None, message: str = "Success", code: str = "OK"):
        super().__init__(status_code=200, code=code, message=message, data=data)
        self.log_debug()

class HttpCreatedResponse(HttpResponse[T]):
    def __init__(self, data: T = None, message: str = "Created Successfully", code: str = "CREATED"):
        super().__init__(status_code=201, code=code, message=message, data=data)
        self.log_debug()

class HttpAcceptedResponse(HttpResponse[T]):
    def __init__(self, data: T = None, message: str = "Accepted", code: str = "ACCEPTED"):
        super().__init__(status_code=202, code=code, message=message, data=data)
        self.log_debug()

class HttpNoContentResponse(HttpResponse[None]):
    def __init__(self, message: str = "No Content", code: str = "NO_CONTENT"):
        super().__init__(status_code=204, code=code, message=message, data=None)
        self.log_debug()