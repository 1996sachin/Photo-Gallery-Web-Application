"""Albums API"""
import uuid, secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Album, User
from api.auth import get_current_user

router = APIRouter()

class AlbumIn(BaseModel):
    title: str
    description: Optional[str] = None

@router.post("/")
async def create(p: AlbumIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    a = Album(owner_id=cu.id, title=p.title, description=p.description)
    db.add(a); await db.flush()
    return {"id": str(a.id), "title": a.title, "description": a.description, "is_shared": False, "share_token": None, "created_at": a.created_at.isoformat()}

@router.get("/")
async def list_albums(db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Album).where(Album.owner_id == cu.id).order_by(Album.created_at.desc()))
    return [{"id": str(a.id),"title": a.title,"description": a.description,"is_shared": a.is_shared,"share_token": a.share_token,"created_at": a.created_at.isoformat()} for a in r.scalars().all()]

@router.delete("/{aid}")
async def delete(aid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid), Album.owner_id == cu.id))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    await db.delete(a); return {"status": "deleted"}

@router.post("/{aid}/share")
async def share(aid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Album).where(Album.id == uuid.UUID(aid), Album.owner_id == cu.id))
    a = r.scalar_one_or_none()
    if not a: raise HTTPException(404)
    if a.is_shared: a.is_shared = False; a.share_token = None
    else: a.is_shared = True; a.share_token = secrets.token_urlsafe(32)
    return {"is_shared": a.is_shared, "share_token": a.share_token}
