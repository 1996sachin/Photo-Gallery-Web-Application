import uuid, os, tempfile
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from models.database import get_db, Media, MediaEdit, User, MediaHistory
from api.auth import get_verified_user as get_current_user
from services.media_processor import apply_photo_edit, apply_video_trim, apply_video_edit
from services.storage import upload_file, download_file, generate_object_key

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
    
    # Versioning
    res_history = await db.execute(select(func.count(MediaHistory.id)).where(MediaHistory.media_id == m.id))
    if res_history.scalar() == 0:
        h = MediaHistory(
            media_id=m.id, user_id=cu.id,
            file_path=m.file_path, version_name="Original",
            file_size_bytes=m.file_size_bytes, encryption_iv=m.encryption_iv
        )
        db.add(h)

    tmp_orig = None
    tmp_edit = None
    try:
        # Download from Minio
        ext = Path(m.file_path).suffix or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_orig = tmp.name
        download_file(m.file_path, tmp_orig)

        out_name = f"edit_{uuid.uuid4()}.jpg"
        tmp_edit = str(EDIT_DIR / out_name)
        
        result = apply_photo_edit(tmp_orig, tmp_edit, p.edit_type, p.params)
        
        # Upload edited to Minio
        object_key = generate_object_key(str(cu.id), out_name, prefix="edited")
        upload_file(tmp_edit, object_key, content_type="image/jpeg")
        
        e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type=p.edit_type, edit_params=p.params, result_path=object_key)
        db.add(e); await db.flush()
        
        # Update media to point to edited version
        m.file_path = object_key
        m.width = result["width"]
        m.height = result["height"]
        
        return {"edit_id": str(e.id), "status": "edited", **result}
    finally:
        if tmp_orig and os.path.exists(tmp_orig): os.unlink(tmp_orig)
        if tmp_edit and os.path.exists(tmp_edit): os.unlink(tmp_edit)

@router.post("/video/trim")
async def trim_video(p: TrimIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(p.media_id), Media.uploader_id == cu.id, Media.media_type == "video"))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    if p.start_seconds >= p.end_seconds: raise HTTPException(400, "start must be < end")
    
    tmp_orig = None
    tmp_edit = None
    try:
        ext = Path(m.file_path).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_orig = tmp.name
        download_file(m.file_path, tmp_orig)

        out_name = f"trim_{uuid.uuid4()}{ext}"
        tmp_edit = str(EDIT_DIR / out_name)
        
        result = apply_video_trim(tmp_orig, tmp_edit, p.start_seconds, p.end_seconds)
        
        # Upload to Minio
        object_key = generate_object_key(str(cu.id), out_name, prefix="edited")
        upload_file(tmp_edit, object_key, content_type="video/mp4")
        
        e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type="trim", edit_params={"start": p.start_seconds, "end": p.end_seconds}, result_path=object_key)
        db.add(e); await db.flush()
        
        m.file_path = object_key
        m.duration_seconds = result["duration_seconds"]
        
        return {"edit_id": str(e.id), "status": "trimmed", **result}
    finally:
        if tmp_orig and os.path.exists(tmp_orig): os.unlink(tmp_orig)
        if tmp_edit and os.path.exists(tmp_edit): os.unlink(tmp_edit)

@router.post("/video")
async def edit_video(p: VideoEditIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Media).where(Media.id == uuid.UUID(p.media_id), Media.uploader_id == cu.id, Media.media_type == "video"))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    
    tmp_orig = None
    tmp_edit = None
    try:
        ext = Path(m.file_path).suffix or ".mp4"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp_orig = tmp.name
        download_file(m.file_path, tmp_orig)

        out_name = f"video_edit_{uuid.uuid4()}.mp4"
        tmp_edit = str(EDIT_DIR / out_name)
        
        result = apply_video_edit(tmp_orig, tmp_edit, p.params)
        
        # Upload to Minio
        object_key = generate_object_key(str(cu.id), out_name, prefix="edited")
        upload_file(tmp_edit, object_key, content_type="video/mp4")
        
        e = MediaEdit(media_id=m.id, editor_id=cu.id, edit_type="video_edit", edit_params=p.params, result_path=object_key)
        db.add(e); await db.flush()
        
        m.file_path = object_key
        m.duration_seconds = result["duration_seconds"]
        
        return {"edit_id": str(e.id), "status": "edited", **result}
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    finally:
        if tmp_orig and os.path.exists(tmp_orig): os.unlink(tmp_orig)
        if tmp_edit and os.path.exists(tmp_edit): os.unlink(tmp_edit)

@router.get("/{media_id}/history")
async def history(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(MediaEdit).where(MediaEdit.media_id == uuid.UUID(media_id)).order_by(MediaEdit.created_at.desc()))
    return [{"id": str(e.id),"edit_type": e.edit_type,"params": e.edit_params,"created_at": e.created_at.isoformat()} for e in r.scalars().all()]

@router.get("/{media_id}/versions")
async def get_versions(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(MediaHistory).where(MediaHistory.media_id == uuid.UUID(media_id)).order_by(MediaHistory.created_at.desc()))
    return [{"id": str(v.id), "name": v.version_name, "created_at": v.created_at.isoformat()} for v in r.scalars().all()]


@router.post("/{media_id}/restore-original")
async def restore_original(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    mid = uuid.UUID(media_id)
    r = await db.execute(select(Media).where(Media.id == mid, Media.uploader_id == cu.id))
    m = r.scalar_one_or_none()
    if not m: raise HTTPException(404)
    
    r_h = await db.execute(select(MediaHistory).where(MediaHistory.media_id == mid, MediaHistory.version_name == "Original"))
    orig = r_h.scalar_one_or_none()
    if not orig: raise HTTPException(400, "No original version found")
    
    m.file_path = orig.file_path
    m.file_size_bytes = orig.file_size_bytes
    m.encryption_iv = orig.encryption_iv
    
    return {"status": "restored"}
