from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_db, SyncEvent, User
from api.auth import get_verified_user as get_current_user
from typing import List, Optional

router = APIRouter()

@router.get("/delta")
async def get_sync_delta(
    since_id: int = Query(0, description="The last sequence ID the client received"),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_current_user)
):
    """
    Returns incremental changes (created, updated, deleted) for media and albums
    since the provided 'since_id'.
    """
    q = select(SyncEvent).where(
        SyncEvent.user_id == cu.id,
        SyncEvent.id > since_id
    ).order_by(SyncEvent.id.asc()).limit(limit)
    
    r = await db.execute(q)
    events = r.scalars().all()
    
    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "media_id": str(e.media_id) if e.media_id else None,
                "album_id": str(e.album_id) if e.album_id else None,
                "details": e.details,
                "created_at": e.created_at.isoformat()
            } for e in events
        ],
        "has_more": len(events) == limit,
        "last_id": events[-1].id if events else since_id
    }
