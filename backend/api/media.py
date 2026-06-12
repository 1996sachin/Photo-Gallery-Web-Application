import hashlib, secrets, uuid, os, mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, select, update
import aiofiles

from models.database import AccessGrant, get_db, Media, User, Album
from api.auth import get_verified_user as get_current_user
from services.media_processor import process_photo, process_video
from services.audit_service import log_action
from services.security_service import sanitize_text
from services.malware_scanner import scan_file

router = APIRouter()
UPLOAD_DIR = Path("uploads/originals")
THUMB_DIR  = Path("uploads/thumbnails")
ALLOWED_PHOTO = {"image/jpeg","image/png","image/webp","image/gif","image/heic"}
ALLOWED_VIDEO = {"video/mp4","video/quicktime","video/webm","video/avi","video/x-msvideo"}
ALLOWED_DOCS  = {"application/pdf", "text/plain", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
MAX_SIZE = 500 * 1024 * 1024


def to_dict(m: Media, base="http://localhost:8000"):
    file_url = f"{base}/api/media/{m.id}/file"
    
    return {
        "id": str(m.id), "media_type": m.media_type,
        "filename": m.filename, "original_filename": m.original_filename,
        "title": m.title, "caption": m.caption,
        "thumbnail_url": f"{base}/uploads/thumbnails/{Path(m.thumbnail_path).name}" if m.thumbnail_path else None,
        "file_url": file_url,
        "width": m.width, "height": m.height,
        "duration_seconds": m.duration_seconds,
        "is_favorite": m.is_favorite, "view_count": m.view_count,
        "taken_at": m.taken_at.isoformat() if m.taken_at else None,
        "location_name": m.location_name,
        "file_size_bytes": m.file_size_bytes,
        "created_at": m.created_at.isoformat(),
        "album_id": str(m.album_id) if m.album_id else None,
        "privacy": m.privacy,
        "share_token": m.share_token,
        "share_has_password": bool(m.share_password_hash),
        "share_expires_at": m.share_expires_at.isoformat() if m.share_expires_at else None,
        "malware_scan_status": m.malware_scan_status,
    }


def _hash_share_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _is_expired(expires_at) -> bool:
    if not expires_at:
        return False
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= now


def _public_media_dict(m: Media, base: str) -> dict:
    return {
        "id": str(m.id),
        "media_type": m.media_type,
        "original_filename": m.original_filename,
        "title": m.title,
        "caption": m.caption,
        "thumbnail_url": f"{base}/uploads/thumbnails/{Path(m.thumbnail_path).name}" if m.thumbnail_path else None,
        "file_url": f"{base}/api/media/shared/{m.share_token}/file",
        "width": m.width,
        "height": m.height,
        "duration_seconds": m.duration_seconds,
        "share_expires_at": m.share_expires_at.isoformat() if m.share_expires_at else None,
    }


async def _can_access_media(db: AsyncSession, media: Media, user: User) -> bool:
    if media.uploader_id == user.id or user.role == "admin":
        return True
    conditions = [AccessGrant.media_id == media.id]
    if media.album_id:
        conditions.append(AccessGrant.album_id == media.album_id)
    grant = await db.execute(select(AccessGrant).where(AccessGrant.grantee_id == user.id, or_(*conditions)))
    return grant.scalar_one_or_none() is not None


async def _get_shared_media(token: str, password: Optional[str], db: AsyncSession) -> Media:
    r = await db.execute(select(Media).where(Media.share_token == token, Media.privacy == "shared"))
    media = r.scalar_one_or_none()
    if not media or _is_expired(media.share_expires_at):
        raise HTTPException(404, "Shared media not found")
    if media.share_password_hash and _hash_share_password(password or "") != media.share_password_hash:
        raise HTTPException(403, "Share password required")
    return media


@router.get("/{mid}/file")
async def get_media_file(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    from services.media_processor import decrypt_file
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid)))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    
    if not await _can_access_media(db, m, cu):
        raise HTTPException(404)

    path = Path(m.file_path)
    if not path.exists(): raise HTTPException(404)

    async with aiofiles.open(path, "rb") as f:
        data = await f.read()
    
    if m.is_encrypted:
        data = decrypt_file(data)
    
    from fastapi.responses import Response
    return Response(content=data, media_type=m.mime_type)


@router.post("/upload")
async def upload(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    album_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_current_user),
    request: Request = None,
):
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    is_photo = mime in ALLOWED_PHOTO
    is_video = mime in ALLOWED_VIDEO
    is_doc   = mime in ALLOWED_DOCS
    if not (is_photo or is_video or is_doc):
        raise HTTPException(400, f"Unsupported type: {mime}")

    album_uuid = uuid.UUID(album_id) if album_id else None
    if album_uuid:
        r = await db.execute(select(Album).where(Album.id == album_uuid, Album.owner_id == cu.id))
        if not r.scalar_one_or_none():
            raise HTTPException(404, "Album not found")

    ext  = Path(file.filename or "file").suffix.lower()
    name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / name
    size = 0

    async with aiofiles.open(dest, "wb") as f:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > MAX_SIZE:
                await f.close(); dest.unlink(missing_ok=True)
                raise HTTPException(413, "File too large (max 500 MB)")
            await f.write(chunk)

    scan_ok, scan_result = scan_file(str(dest))
    if not scan_ok:
        dest.unlink(missing_ok=True)
        await log_action(db, "upload_blocked_malware", cu.id, details={"filename": file.filename, "result": scan_result}, ip_address=request.client.host if request else None)
        raise HTTPException(400, f"Upload blocked by malware scan: {scan_result}")

    from services.media_processor import process_photo, process_video, process_document, encrypt_path

    media_type = "photo" if is_photo else ("video" if is_video else "document")
    is_encrypted = False
    if is_doc:
        is_encrypted = encrypt_path(str(dest))
    m = Media(
        uploader_id=cu.id,
        album_id=album_uuid,
        filename=name, original_filename=file.filename or name,
        file_path=str(dest), media_type=media_type,
        mime_type=mime, file_size_bytes=size,
        title=sanitize_text(title), caption=sanitize_text(caption),
        is_encrypted=is_encrypted,
        malware_scan_status="clean",
        malware_scan_result=scan_result,
    )
    db.add(m); await db.flush()

    await log_action(db, "upload", cu.id, details={"media_id": str(m.id), "type": media_type}, ip_address=request.client.host if request else None)

    if is_photo: bg.add_task(process_photo, str(m.id), str(dest), str(THUMB_DIR))
    elif is_video: bg.add_task(process_video, str(m.id), str(dest), str(THUMB_DIR))
    elif is_doc: bg.add_task(process_document, str(m.id), str(dest), str(THUMB_DIR))

    return {"id": str(m.id), "status": "uploaded", "media_type": m.media_type}


@router.get("/")
async def list_media(
    album_id: Optional[str] = None,
    media_type: Optional[str] = None,
    search: Optional[str] = None,
    favorites_only: bool = False,
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_current_user),
):
    if cu.role == "admin":
        q = select(Media)
    else:
        granted_albums = select(AccessGrant.album_id).where(AccessGrant.grantee_id == cu.id, AccessGrant.album_id.is_not(None))
        granted_media = select(AccessGrant.media_id).where(AccessGrant.grantee_id == cu.id, AccessGrant.media_id.is_not(None))
        q = select(Media).where(
            or_(
                Media.uploader_id == cu.id,
                Media.album_id.in_(granted_albums),
                Media.id.in_(granted_media),
            )
        )
    if album_id:      q = q.where(Media.album_id == uuid.UUID(album_id))
    if media_type in ("photo","video","document"): q = q.where(Media.media_type == media_type)
    if favorites_only: q = q.where(Media.is_favorite == True)
    if search:
        like = f"%{search}%"
        q = q.where((Media.title.ilike(like)) | (Media.caption.ilike(like)) | (Media.original_filename.ilike(like)))
    q = q.order_by(Media.taken_at.desc().nullslast(), Media.created_at.desc())
    q = q.offset((page - 1) * per_page).limit(per_page)
    r = await db.execute(q)
    return [to_dict(m) for m in r.scalars().all()]


@router.get("/{mid}")
async def get_one(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid)))
    m = r.scalar_one_or_none()
    if not m or not await _can_access_media(db, m, cu): raise HTTPException(404, "Not found")
    await db.execute(update(Media).where(Media.id == m.id).values(view_count=Media.view_count + 1))
    return to_dict(m)


@router.post("/{mid}/share")
async def share_media(mid: str, payload: dict, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m:
        raise HTTPException(404)
    enabled = bool(payload.get("enabled", True))
    if not enabled:
        m.privacy = "private"
        m.share_token = None
        m.share_password_hash = None
        m.share_expires_at = None
    else:
        m.privacy = "shared"
        m.share_token = m.share_token or secrets.token_urlsafe(32)
        if "password" in payload:
            password = (payload.get("password") or "").strip()
            m.share_password_hash = _hash_share_password(password) if password else None
        expires_at = payload.get("expires_at")
        m.share_expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00")) if expires_at else None
    await log_action(db, "update_media_share", cu.id, details={"media_id": mid, "enabled": m.privacy == "shared"}, ip_address=request.client.host if request else None)
    return to_dict(m)


@router.get("/shared/{token}")
async def get_shared_media(token: str, password: Optional[str] = Query(None), db: AsyncSession = Depends(get_db), request: Request = None):
    m = await _get_shared_media(token, password, db)
    base = str(request.base_url).rstrip("/") if request else "http://localhost:8000"
    return _public_media_dict(m, base)


@router.get("/shared/{token}/file")
async def get_shared_media_file(token: str, password: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    from fastapi.responses import Response
    from services.media_processor import decrypt_file

    m = await _get_shared_media(token, password, db)
    path = Path(m.file_path)
    if not path.exists():
        raise HTTPException(404)
    async with aiofiles.open(path, "rb") as f:
        data = await f.read()
    if m.is_encrypted:
        data = decrypt_file(data)
    return Response(content=data, media_type=m.mime_type)


@router.patch("/{mid}/favorite")
async def toggle_fav(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    m.is_favorite = not m.is_favorite
    return {"is_favorite": m.is_favorite}


@router.patch("/{mid}")
async def update_media(mid: str, payload: dict, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    allowed = {"title","caption","location_name","album_id"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates: raise HTTPException(400, "No valid fields")
    
    if "title" in updates: updates["title"] = sanitize_text(updates["title"])
    if "caption" in updates: updates["caption"] = sanitize_text(updates["caption"])
    if "location_name" in updates: updates["location_name"] = sanitize_text(updates["location_name"])

    if "album_id" in updates:
        if updates["album_id"]:
            album_uuid = uuid.UUID(updates["album_id"])
            r = await db.execute(select(Album).where(Album.id == album_uuid, Album.owner_id == cu.id))
            if not r.scalar_one_or_none():
                raise HTTPException(404, "Album not found")
            updates["album_id"] = album_uuid
        else:
            updates["album_id"] = None
    await db.execute(update(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id).values(**updates))
    await log_action(db, "update_media", cu.id, details={"media_id": mid, "fields": list(updates.keys())}, ip_address=request.client.host if request else None)
    return {"status": "updated"}


@router.delete("/{mid}")
async def delete_media(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    for p in [m.file_path, m.thumbnail_path]:
        if p: Path(p).unlink(missing_ok=True)
    await db.delete(m)
    await log_action(db, "delete_media", cu.id, details={"media_id": mid}, ip_address=request.client.host if request else None)
    return {"status": "deleted"}
