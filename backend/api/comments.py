"""Comments API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Comment, User
from api.auth import get_verified_user as get_current_user

router = APIRouter()

class CommentIn(BaseModel):
    media_id: str
    body: str

@router.post("/")
async def add(p: CommentIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    c = Comment(media_id=uuid.UUID(p.media_id), author_id=cu.id, body=p.body)
    db.add(c); await db.flush()
    return {"id": str(c.id), "body": c.body, "author_id": str(c.author_id), "created_at": c.created_at.isoformat()}

@router.get("/{media_id}")
async def list_comments(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Comment).where(Comment.media_id == uuid.UUID(media_id)).order_by(Comment.created_at))
    return [{"id": str(c.id),"body": c.body,"author_id": str(c.author_id),"created_at": c.created_at.isoformat()} for c in r.scalars().all()]

@router.delete("/{cid}")
async def delete(cid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Comment).where(Comment.id == uuid.UUID(cid), Comment.author_id == cu.id))
    c = r.scalar_one_or_none()
    if not c: raise HTTPException(404)
    await db.delete(c); return {"status": "deleted"}
