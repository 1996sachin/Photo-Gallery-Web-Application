import uuid, os, mimetypes
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query, BackgroundTasks, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import aiofiles

from models.database import get_db, Media, User, Album
from api.auth import get_verified_user as get_current_user
from services.media_processor import process_photo, process_video

router = APIRouter()
UPLOAD_DIR = Path("uploads/originals")
THUMB_DIR  = Path("uploads/thumbnails")
ALLOWED_PHOTO = {"image/jpeg","image/png","image/webp","image/gif","image/heic"}
ALLOWED_VIDEO = {"video/mp4","video/quicktime","video/webm","video/avi","video/x-msvideo"}
MAX_SIZE = 500 * 1024 * 1024


def to_dict(m: Media, base="http://localhost:8000"):
    return {
        "id": str(m.id), "media_type": m.media_type,
        "filename": m.filename, "original_filename": m.original_filename,
        "title": m.title, "caption": m.caption,
        "thumbnail_url": f"{base}/uploads/thumbnails/{Path(m.thumbnail_path).name}" if m.thumbnail_path else None,
        "file_url": f"{base}/uploads/originals/{m.filename}",
        "width": m.width, "height": m.height,
        "duration_seconds": m.duration_seconds,
        "is_favorite": m.is_favorite, "view_count": m.view_count,
        "taken_at": m.taken_at.isoformat() if m.taken_at else None,
        "location_name": m.location_name,
        "file_size_bytes": m.file_size_bytes,
        "created_at": m.created_at.isoformat(),
        "album_id": str(m.album_id) if m.album_id else None,
    }


@router.post("/upload")
async def upload(
    bg: BackgroundTasks,
    file: UploadFile = File(...),
    album_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    caption: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_current_user),
):
    mime = file.content_type or mimetypes.guess_type(file.filename or "")[0] or ""
    is_photo = mime in ALLOWED_PHOTO
    is_video = mime in ALLOWED_VIDEO
    if not (is_photo or is_video):
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

    m = Media(
        uploader_id=cu.id,
        album_id=album_uuid,
        filename=name, original_filename=file.filename or name,
        file_path=str(dest), media_type="photo" if is_photo else "video",
        mime_type=mime, file_size_bytes=size,
        title=title, caption=caption,
    )
    db.add(m); await db.flush()
    if is_photo: bg.add_task(process_photo, str(m.id), str(dest), str(THUMB_DIR))
    else:        bg.add_task(process_video, str(m.id), str(dest), str(THUMB_DIR))
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
    q = select(Media).where(Media.uploader_id == cu.id)
    if album_id:      q = q.where(Media.album_id == uuid.UUID(album_id))
    if media_type in ("photo","video"): q = q.where(Media.media_type == media_type)
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
    if not m: raise HTTPException(404, "Not found")
    await db.execute(update(Media).where(Media.id == m.id).values(view_count=Media.view_count + 1))
    return to_dict(m)


@router.patch("/{mid}/favorite")
async def toggle_fav(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    m.is_favorite = not m.is_favorite
    return {"is_favorite": m.is_favorite}


@router.patch("/{mid}")
async def update_media(mid: str, payload: dict, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    allowed = {"title","caption","location_name","album_id"}
    updates = {k: v for k, v in payload.items() if k in allowed}
    if not updates: raise HTTPException(400, "No valid fields")
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
    return {"status": "updated"}


@router.delete("/{mid}")
async def delete_media(mid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(mid), Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    for p in [m.file_path, m.thumbnail_path]:
        if p: Path(p).unlink(missing_ok=True)
    await db.delete(m)
    return {"status": "deleted"}
