import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import require_admin
from models.database import AuditLog, Media, User, get_db
from services.audit_service import log_action

router = APIRouter()

VALID_ROLES = {"admin", "business", "client"}


class AdminUserUpdate(BaseModel):
    role: str


def user_to_dict(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role or "client",
        "email_verified": bool(user.email_verified),
        "mfa_enabled": bool(user.mfa_enabled),
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
    }


def audit_to_dict(log: AuditLog) -> dict:
    return {
        "id": str(log.id),
        "user_id": str(log.user_id) if log.user_id else None,
        "user_email": log.user.email if log.user else None,
        "action": log.action,
        "details": log.details or {},
        "ip_address": log.ip_address,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/stats")
async def stats(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users_by_role_result = await db.execute(
        select(User.role, func.count(User.id)).group_by(User.role)
    )
    users_by_role = {
        role or "client": count for role, count in users_by_role_result.all()
    }

    total_users = await db.scalar(select(func.count(User.id))) or 0
    verified_users = await db.scalar(
        select(func.count(User.id)).where(User.email_verified == True)
    ) or 0
    mfa_users = await db.scalar(
        select(func.count(User.id)).where(User.mfa_enabled == True)
    ) or 0
    media_count = await db.scalar(select(func.count(Media.id))) or 0
    total_storage = await db.scalar(select(func.coalesce(func.sum(Media.file_size_bytes), 0))) or 0

    media_by_type_result = await db.execute(
        select(Media.media_type, func.count(Media.id), func.coalesce(func.sum(Media.file_size_bytes), 0))
        .group_by(Media.media_type)
    )
    media_by_type = {
        media_type: {"count": count, "storage_bytes": int(storage or 0)}
        for media_type, count, storage in media_by_type_result.all()
    }

    latest_activity = await db.execute(
        select(AuditLog)
        .options(selectinload(AuditLog.user))
        .order_by(AuditLog.created_at.desc())
        .limit(8)
    )

    return {
        "total_users": total_users,
        "verified_users": verified_users,
        "mfa_users": mfa_users,
        "users_by_role": users_by_role,
        "media_count": media_count,
        "total_storage_bytes": int(total_storage or 0),
        "media_by_type": media_by_type,
        "latest_activity": [audit_to_dict(log) for log in latest_activity.scalars().all()],
    }


@router.get("/users")
async def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(User)
    count_q = select(func.count(User.id))

    filters = []
    if search:
        like = f"%{search}%"
        filters.append((User.email.ilike(like)) | (User.display_name.ilike(like)))
    if role:
        if role not in VALID_ROLES:
            raise HTTPException(400, "Invalid role")
        filters.append(User.role == role)

    for condition in filters:
        q = q.where(condition)
        count_q = count_q.where(condition)

    total = await db.scalar(count_q) or 0
    result = await db.execute(
        q.order_by(User.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    )

    return {
        "items": [user_to_dict(user) for user in result.scalars().all()],
        "page": page,
        "per_page": per_page,
        "total": total,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    payload: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
    request: Request = None,
):
    if payload.role not in VALID_ROLES:
        raise HTTPException(400, "Invalid role")

    target_id = uuid.UUID(user_id)
    target_result = await db.execute(select(User).where(User.id == target_id))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(404, "User not found")

    if target.id == admin.id and payload.role != "admin":
        admin_count = await db.scalar(select(func.count(User.id)).where(User.role == "admin")) or 0
        if admin_count <= 1:
            raise HTTPException(400, "Cannot remove the last admin")

    old_role = target.role or "client"
    target.role = payload.role
    await log_action(
        db,
        "admin_update_user_role",
        admin.id,
        details={"target_user_id": str(target.id), "old_role": old_role, "new_role": payload.role},
        ip_address=request.client.host if request else None,
    )
    return user_to_dict(target)


@router.get("/audit-logs")
async def list_audit_logs(
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = select(AuditLog).options(selectinload(AuditLog.user))
    count_q = select(func.count(AuditLog.id))

    if action:
        q = q.where(AuditLog.action.ilike(f"%{action}%"))
        count_q = count_q.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        uid = uuid.UUID(user_id)
        q = q.where(AuditLog.user_id == uid)
        count_q = count_q.where(AuditLog.user_id == uid)

    total = await db.scalar(count_q) or 0
    result = await db.execute(
        q.order_by(AuditLog.created_at.desc()).offset((page - 1) * per_page).limit(per_page)
    )

    return {
        "items": [audit_to_dict(log) for log in result.scalars().all()],
        "page": page,
        "per_page": per_page,
        "total": total,
    }
