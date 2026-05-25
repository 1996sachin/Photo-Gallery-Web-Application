import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Media, MediaEdit, User
from api.auth import get_verified_user as get_current_user
from services.media_processor import apply_photo_edit, apply_video_trim, apply_video_edit

router = APIRouter()
EDIT_DIR = Path("uploads/edited")
EDIT_DIR.mkdir(parents=True, exist_ok=True)

class PhotoEditIn(BaseModel):
    media_id: str; edit_type: str; params: dict

class TrimIn(BaseModel):
    media_id: str; start_seconds: float; end_seconds: float

class VideoEditIn(BaseModel):
    media_id: str
    params: dict

@router.post("/photo")
async def edit_photo(p: PhotoEditIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(p.media_id), Media.uploader_id == cu.id, Media.media_type == "photo"))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    out_name = f"edit_{uuid.uuid4()}.jpg"
    out_path = str(EDIT_DIR / out_name)
    result = apply_photo_edit(m.file_path, out_path, p.edit_type, p.params)
    e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type=p.edit_type, edit_params=p.params, result_path=out_path)
    db.add(e); await db.flush()
    return {"edit_id": str(e.id), "result_url": f"http://localhost:8000/uploads/edited/{out_name}", **result}

@router.post("/video/trim")
async def trim_video(p: TrimIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(p.media_id), Media.uploader_id == cu.id, Media.media_type == "video"))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    if p.start_seconds >= p.end_seconds: raise HTTPException(400, "start must be < end")
    ext = Path(m.file_path).suffix
    out_name = f"trim_{uuid.uuid4()}{ext}"
    out_path = str(EDIT_DIR / out_name)
    result = apply_video_trim(m.file_path, out_path, p.start_seconds, p.end_seconds)
    e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type="trim", edit_params={"start": p.start_seconds, "end": p.end_seconds}, result_path=out_path)
    db.add(e); await db.flush()
    return {"edit_id": str(e.id), "result_url": f"http://localhost:8000/uploads/edited/{out_name}", **result}

@router.post("/video")
async def edit_video(p: VideoEditIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(p.media_id), Media.uploader_id == cu.id, Media.media_type == "video"))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    out_name = f"video_edit_{uuid.uuid4()}.mp4"
    out_path = str(EDIT_DIR / out_name)
    try:
        result = apply_video_edit(m.file_path, out_path, p.params)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type="video_edit", edit_params=p.params, result_path=out_path)
    db.add(e); await db.flush()
    return {"edit_id": str(e.id), "result_url": f"http://localhost:8000/uploads/edited/{out_name}", **result}

@router.get("/{media_id}/history")
async def history(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(MediaEdit).where(MediaEdit.media_id == uuid.UUID(media_id)).order_by(MediaEdit.created_at.desc()))
    return [{"id": str(e.id),"edit_type": e.edit_type,"params": e.edit_params,"created_at": e.created_at.isoformat()} for e in r.scalars().all()]
