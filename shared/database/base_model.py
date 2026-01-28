# shared/database/base_model.py
from beanie import Document, before_event, Insert, Replace
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional

from shared.context import jwt_claims_ctx

# --- Metadata model ---
class Metadata(BaseModel):
    created_by: Optional[str] = None
    modified_by: Optional[str] = None
    created_at: datetime = datetime.now(timezone.utc)
    modified_at: datetime = datetime.now(timezone.utc)

# --- Base document ---
class BaseDocument(Document):
    metadata: Metadata = Metadata()

    class Settings:
        abstract = True

# --- Hook for insert: set created_by and created_at ---
@before_event(Insert)
async def set_created_metadata(doc: BaseDocument):
    now = datetime.now(timezone.utc)
    doc.metadata.created_at = now
    doc.metadata.modified_at = now
    claims = jwt_claims_ctx.get(None)
    user = claims.get("sub") if claims else None
    if user:
        doc.metadata.created_by = user
        doc.metadata.modified_by = user

# --- Hook for replace: update modified metadata ---
@before_event(Replace)
async def set_modified_metadata(doc: BaseDocument):
    doc.metadata.modified_at = datetime.now(timezone.utc)
    claims = jwt_claims_ctx.get(None)
    user = claims.get("sub") if claims else None
    if user:
        doc.metadata.modified_by = user