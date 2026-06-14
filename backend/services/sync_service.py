from sqlalchemy.ext.asyncio import AsyncSession
from models.database import SyncEvent
from typing import Optional, Dict, Any
import uuid

async def log_sync_event(
    db: AsyncSession,
    user_id: uuid.UUID,
    event_type: str,
    media_id: Optional[uuid.UUID] = None,
    album_id: Optional[uuid.UUID] = None,
    details: Optional[Dict[str, Any]] = None
):
    event = SyncEvent(
        user_id=user_id,
        event_type=event_type,
        media_id=media_id,
        album_id=album_id,
        details=details or {}
    )
    db.add(event)
    # We don't commit here, we let the caller handle it (usually the API router)
