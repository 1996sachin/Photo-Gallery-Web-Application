import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.auth import get_verified_user
from models.database import AccessGrant, Album, Media, User, get_db
from services.audit_service import log_action

router = APIRouter()


class GrantIn(BaseModel):
    grantee_email: str
    target_type: str
    target_id: str
    permission: str = "view"


def grant_to_dict(grant: AccessGrant) -> dict:
    return {
        "id": str(grant.id),
        "owner_id": str(grant.owner_id),
        "grantee_id": str(grant.grantee_id),
        "grantee_email": grant.grantee.email if grant.grantee else None,
        "album_id": str(grant.album_id) if grant.album_id else None,
        "media_id": str(grant.media_id) if grant.media_id else None,
        "permission": grant.permission,
        "created_at": grant.created_at.isoformat() if grant.created_at else None,
    }


async def _ensure_owner(db: AsyncSession, user: User, target_type: str, target_id: uuid.UUID):
    if target_type == "album":
        result = await db.execute(select(Album).where(Album.id == target_id, Album.owner_id == user.id))
        target = result.scalar_one_or_none()
    elif target_type == "media":
        result = await db.execute(select(Media).where(Media.id == target_id, Media.uploader_id == user.id))
        target = result.scalar_one_or_none()
    else:
        raise HTTPException(400, "target_type must be album or media")
    if not target:
        raise HTTPException(404, "Target not found")
    return target


@router.get("/")
async def list_grants(
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_verified_user),
):
    q = select(AccessGrant).options(selectinload(AccessGrant.grantee)).where(AccessGrant.owner_id == cu.id)
    if target_type and target_id:
        tid = uuid.UUID(target_id)
        if target_type == "album":
            q = q.where(AccessGrant.album_id == tid)
        elif target_type == "media":
            q = q.where(AccessGrant.media_id == tid)
        else:
            raise HTTPException(400, "target_type must be album or media")
    result = await db.execute(q.order_by(AccessGrant.created_at.desc()))
    return [grant_to_dict(grant) for grant in result.scalars().all()]


@router.post("/")
async def create_grant(
    payload: GrantIn,
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_verified_user),
    request: Request = None,
):
    if payload.permission not in {"view", "comment"}:
        raise HTTPException(400, "permission must be view or comment")
    target_id = uuid.UUID(payload.target_id)
    await _ensure_owner(db, cu, payload.target_type, target_id)

    grantee_result = await db.execute(select(User).where(User.email == payload.grantee_email.strip().lower()))
    grantee = grantee_result.scalar_one_or_none()
    if not grantee:
        raise HTTPException(404, "User not found")
    if grantee.id == cu.id:
        raise HTTPException(400, "You already own this content")

    existing = await db.execute(
        select(AccessGrant).where(
            AccessGrant.owner_id == cu.id,
            AccessGrant.grantee_id == grantee.id,
            AccessGrant.album_id == (target_id if payload.target_type == "album" else None),
            AccessGrant.media_id == (target_id if payload.target_type == "media" else None),
        )
    )
    grant = existing.scalar_one_or_none()
    if grant:
        grant.permission = payload.permission
    else:
        grant = AccessGrant(
            owner_id=cu.id,
            grantee_id=grantee.id,
            album_id=target_id if payload.target_type == "album" else None,
            media_id=target_id if payload.target_type == "media" else None,
            permission=payload.permission,
        )
        db.add(grant)
        await db.flush()

    await log_action(
        db,
        "create_access_grant",
        cu.id,
        details={"grant_id": str(grant.id), "target_type": payload.target_type, "target_id": payload.target_id, "grantee_id": str(grantee.id)},
        ip_address=request.client.host if request else None,
    )
    return grant_to_dict(grant)


@router.delete("/{grant_id}")
async def delete_grant(
    grant_id: str,
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_verified_user),
    request: Request = None,
):
    result = await db.execute(select(AccessGrant).where(AccessGrant.id == uuid.UUID(grant_id), AccessGrant.owner_id == cu.id))
    grant = result.scalar_one_or_none()
    if not grant:
        raise HTTPException(404)
    await log_action(db, "delete_access_grant", cu.id, details={"grant_id": grant_id}, ip_address=request.client.host if request else None)
    await db.delete(grant)
    return {"status": "deleted"}
