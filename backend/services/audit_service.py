from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from models.database import AuditLog
import uuid

async def log_action(
    db: AsyncSession,
    action: str,
    user_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None
):
    log = AuditLog(
        user_id=user_id,
        action=action,
        details=details or {},
        ip_address=ip_address
    )
    db.add(log)
    await db.flush()
