# shared/context.py
from contextvars import ContextVar
from typing import Optional

request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
auth_token_ctx: ContextVar[Optional[str]] = ContextVar("auth_token", default=None)
refresh_token_ctx: ContextVar[Optional[str]] = ContextVar("refresh_token", default=None)
jwt_claims_ctx: ContextVar[Optional[dict]] = ContextVar("jwt_claims", default=None)