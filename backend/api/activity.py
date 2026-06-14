from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from models.database import AuditLog, User, get_db
from api.auth import get_verified_user

router = APIRouter()

@router.get("/")
async def get_activity(
    target_id: Optional[str] = Query(None),
    target_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_verified_user)
):
    """Returns the audit logs for the current user's actions and actions on their items."""
    q = select(AuditLog).where(AuditLog.user_id == cu.id)
    
    if target_id and target_type:
        if target_type == "media":
            q = q.where(AuditLog.details["media_id"].astext == target_id)
        elif target_type == "album":
            q = q.where(AuditLog.details["album_id"].astext == target_id)

    q = q.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(q)
    logs = result.scalars().all()
    
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "details": log.details,
            "ip_address": log.ip_address,
            "created_at": log.created_at.isoformat()
        }
        for log in logs
    ]
