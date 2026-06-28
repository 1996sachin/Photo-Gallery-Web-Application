"""Albums API"""
import hashlib
import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select
from pydantic import BaseModel
from models.database import AccessGrant, get_db, Album, Media, User, Tenant
from services.storage import get_file_data
from services.sync_service import log_sync_event
from services.tenant_service import get_current_tenant
from api.auth import get_verified_user as get_current_user
from services.audit_service import log_action
from services.security_service import sanitize_text

router = APIRouter()

class AlbumIn(BaseModel):
    title: str
    description: Optional[str] = None
    parent_id: Optional[str] = None


class ShareSettings(BaseModel):
    enabled: bool = True
    password: Optional[str] = None
    expires_at: Optional[datetime] = None


def _hash_share_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_share_expired(album: Album) -> bool:
    if not album.share_expires_at:
        return False
    now = datetime.now(timezone.utc)
    expires_at = album.share_expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


def _album_dict(a: Album, cu: User = None) -> dict:
    return {
        "id": str(a.id),
        "title": a.title,
        "description": a.description,
        "parent_id": str(a.parent_id) if a.parent_id else None,
        "is_shared": bool(a.is_shared),
        "is_mine": a.owner_id == cu.id if cu else False,

        "share_token": a.share_token,
        "share_has_password": bool(a.share_password_hash),
        "share_expires_at": a.share_expires_at.isoformat() if a.share_expires_at else None,
        "created_at": a.created_at.isoformat(),
    }


def _public_media_dict(m: Media, base: str) -> dict:
    return {
        "id": str(m.id),
        "media_type": m.media_type,
        "original_filename": m.original_filename,
        "title": m.title,
        "caption": m.caption,
        "thumbnail_url": f"{base}/api/media/shared/{m.share_token}/thumbnail" if m.thumbnail_path else None,
        "file_url": f"{base}/api/media/shared/{m.share_token}/file",
        "width": m.width,
        "height": m.height,
        "duration_seconds": m.duration_seconds,
        "created_at": m.created_at.isoformat(),
    }


async def _get_accessible_shared_album(token: str, password: Optional[str], db: AsyncSession, current_tenant: Optional[Tenant] = None) -> Album:
    r = await db.execute(select(Album).where(Album.share_token == token, Album.is_shared == True))
    album = r.scalar_one_or_none()
    if not album or _is_share_expired(album):
        raise HTTPException(404, "Shared album not found")
        
    # Enforce tenant boundary
    if current_tenant and album.tenant_id != current_tenant.id:
        raise HTTPException(404, "Shared album not found")
    if not current_tenant and album.tenant_id is not None:
        raise HTTPException(404, "Shared album not found")

    if album.share_password_hash and _hash_share_password(password or "") != album.share_password_hash:
        raise HTTPException(403, "Share password required")
    return album

@router.post("/")
async def create(p: AlbumIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    parent_uuid = uuid.UUID(p.parent_id) if p.parent_id else None
    a = Album(owner_id=cu.id, tenant_id=cu.tenant_id, title=sanitize_text(p.title), description=sanitize_text(p.description), parent_id=parent_uuid)
    db.add(a); await db.flush()
    await log_sync_event(db, cu.id, "created", album_id=a.id)
    await log_action(db, "create_album", cu.id, details={"album_id": str(a.id)}, ip_address=request.client.host if request else None)
    return _album_dict(a, cu)

@router.get("/")
async def list_albums(
    parent_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db), 
    cu: User = Depends(get_current_user)
):
    pid = None
    if parent_id and parent_id not in ("null", "undefined", ""):
        try:
            pid = uuid.UUID(parent_id)
        except ValueError:
            raise HTTPException(400, "Invalid parent_id format")
    
    if cu.role == "admin":
        q = select(Album).where(Album.parent_id == pid)
    else:
        granted_album_ids = select(AccessGrant.album_id).where(AccessGrant.grantee_id == cu.id, AccessGrant.album_id.is_not(None))
        q = select(Album).where(
            or_(
                Album.owner_id == cu.id, 
                Album.id.in_(granted_album_ids)
            ),
            Album.parent_id == pid
        )
    
    r = await db.execute(q.order_by(Album.created_at.desc()))
    return [_album_dict(a, cu) for a in r.scalars().all()]

@router.get("/{aid}")
async def get_one(aid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid)))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    # Check permissions (either owner or has access grant)
    if a.owner_id != cu.id and cu.role != "admin":
        granted = await db.execute(select(AccessGrant).where(AccessGrant.grantee_id == cu.id, AccessGrant.album_id == a.id))
        if not granted.scalar_one_or_none():
            raise HTTPException(403, "Access denied")
    return _album_dict(a, cu)

@router.delete("/{aid}")
async def delete(aid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid), Album.owner_id == cu.id))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    await log_sync_event(db, cu.id, "deleted", album_id=a.id)
    await db.delete(a)
    await log_action(db, "delete_album", cu.id, details={"album_id": aid}, ip_address=request.client.host if request else None)
    return {"status": "deleted"}

@router.get("/shared-with-me")
async def shared_with_me(db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    granted_album_ids = select(AccessGrant.album_id).where(AccessGrant.grantee_id == cu.id, AccessGrant.album_id.is_not(None))
    q = select(Album).where(Album.id.in_(granted_album_ids), Album.owner_id != cu.id)
    r = await db.execute(q.order_by(Album.created_at.desc()))
    return [_album_dict(a, cu) for a in r.scalars().all()]

@router.post("/{aid}/share")
async def share(aid: str, settings: ShareSettings = ShareSettings(), db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid), Album.owner_id == cu.id))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    if not settings.enabled:
        a.is_shared = False
        a.share_token = None
        a.share_password_hash = None
        a.share_expires_at = None
    else:
        a.is_shared = True
        a.share_token = a.share_token or secrets.token_urlsafe(32)
        if settings.password is not None:
            cleaned_password = settings.password.strip()
            a.share_password_hash = _hash_share_password(cleaned_password) if cleaned_password else None
        a.share_expires_at = settings.expires_at
    await log_action(
        db,
        "update_album_share",
        cu.id,
        details={
            "album_id": aid,
            "enabled": bool(a.is_shared),
            "has_password": bool(a.share_password_hash),
            "expires_at": a.share_expires_at.isoformat() if a.share_expires_at else None,
        },
        ip_address=request.client.host if request else None,
    )
    return _album_dict(a, cu)


@router.get("/shared/{token}")
async def shared_album(
    token: str,
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    current_tenant: Optional[Tenant] = Depends(get_current_tenant),
):
    album = await _get_accessible_shared_album(token, password, db, current_tenant)
    media_result = await db.execute(
        select(Media).where(Media.album_id == album.id).order_by(Media.created_at.desc())
    )
    app_url = os.getenv("APP_URL", "http://localhost:8000").rstrip("/")
    base = str(request.base_url).rstrip("/") if request else app_url
    return {
        "album": {
            "id": str(album.id),
            "title": album.title,
            "description": album.description,
            "share_has_password": bool(album.share_password_hash),
            "share_expires_at": album.share_expires_at.isoformat() if album.share_expires_at else None,
        },
        "items": [_public_media_dict(m, base) for m in media_result.scalars().all()],
    }


@router.get("/shared/media/{mid}/file")
async def shared_media_file(
    mid: str,
    token: str = Query(...),
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_tenant: Optional[Tenant] = Depends(get_current_tenant),
):
    album = await _get_accessible_shared_album(token, password, db, current_tenant)
    media_result = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.album_id == album.id))
    media = media_result.scalar_one_or_none()
    if not media:
        raise HTTPException(404, "Media not found")

    from fastapi.responses import Response, RedirectResponse
    from services.encryption_service import decrypt_data
    from services.storage import get_presigned_url, USE_CDN

    if not media.is_encrypted and USE_CDN:
        url = get_presigned_url(media.file_path)
        if url:
            return RedirectResponse(url)

    data = get_file_data(media.file_path)
    if media.is_encrypted:
        data = decrypt_data(data, media.encryption_iv)
    return Response(
        content=data, 
        media_type=media.mime_type,
        headers={"Cache-Control": "public, max-age=86400"}
    )
