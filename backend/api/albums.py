"""Albums API"""
import hashlib
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Album, Media, User
from api.auth import get_verified_user as get_current_user
from services.audit_service import log_action
from services.security_service import sanitize_text

router = APIRouter()

class AlbumIn(BaseModel):
    title: str
    description: Optional[str] = None


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


def _album_dict(a: Album) -> dict:
    return {
        "id": str(a.id),
        "title": a.title,
        "description": a.description,
        "is_shared": bool(a.is_shared),
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
        "thumbnail_url": f"{base}/uploads/thumbnails/{m.thumbnail_path.split('/')[-1]}" if m.thumbnail_path else None,
        "file_url": f"{base}/api/albums/shared/media/{m.id}/file",
        "width": m.width,
        "height": m.height,
        "duration_seconds": m.duration_seconds,
        "created_at": m.created_at.isoformat(),
    }


async def _get_accessible_shared_album(token: str, password: Optional[str], db: AsyncSession) -> Album:
    r = await db.execute(select(Album).where(Album.share_token == token, Album.is_shared == True))
    album = r.scalar_one_or_none()
    if not album or _is_share_expired(album):
        raise HTTPException(404, "Shared album not found")
    if album.share_password_hash and _hash_share_password(password or "") != album.share_password_hash:
        raise HTTPException(403, "Share password required")
    return album

@router.post("/")
async def create(p: AlbumIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    a = Album(owner_id=cu.id, title=sanitize_text(p.title), description=sanitize_text(p.description))
    db.add(a); await db.flush()
    await log_action(db, "create_album", cu.id, details={"album_id": str(a.id)}, ip_address=request.client.host if request else None)
    return _album_dict(a)

@router.get("/")
async def list_albums(db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Album).where(Album.owner_id == cu.id).order_by(Album.created_at.desc()))
    return [_album_dict(a) for a in r.scalars().all()]

@router.delete("/{aid}")
async def delete(aid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid), Album.owner_id == cu.id))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    await db.delete(a)
    await log_action(db, "delete_album", cu.id, details={"album_id": aid}, ip_address=request.client.host if request else None)
    return {"status": "deleted"}

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
    return _album_dict(a)


@router.get("/shared/{token}")
async def shared_album(
    token: str,
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None,
):
    album = await _get_accessible_shared_album(token, password, db)
    media_result = await db.execute(
        select(Media).where(Media.album_id == album.id).order_by(Media.created_at.desc())
    )
    base = str(request.base_url).rstrip("/") if request else "http://localhost:8000"
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
):
    album = await _get_accessible_shared_album(token, password, db)
    media_result = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.album_id == album.id))
    media = media_result.scalar_one_or_none()
    if not media:
        raise HTTPException(404, "Media not found")

    from pathlib import Path
    import aiofiles
    from fastapi.responses import Response
    from services.media_processor import decrypt_file

    path = Path(media.file_path)
    if not path.exists():
        raise HTTPException(404, "File not found")
    async with aiofiles.open(path, "rb") as f:
        data = await f.read()
    if media.media_type == "document":
        data = decrypt_file(data)
    return Response(content=data, media_type=media.mime_type)
