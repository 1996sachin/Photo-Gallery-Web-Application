"""Comments API"""
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Comment, User
from api.auth import get_verified_user as get_current_user
from services.audit_service import log_action
from services.security_service import sanitize_text
from fastapi import APIRouter, Depends, HTTPException, Request

router = APIRouter()

class CommentIn(BaseModel):
    media_id: str
    body: str

@router.post("/")
async def add(p: CommentIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    c = Comment(media_id=uuid.UUID(p.media_id), author_id=cu.id, body=sanitize_text(p.body))
    db.add(c); await db.flush()
    await log_action(db, "add_comment", cu.id, details={"media_id": p.media_id, "comment_id": str(c.id)}, ip_address=request.client.host if request else None)
    return {"id": str(c.id), "body": c.body, "author_id": str(c.author_id), "created_at": c.created_at.isoformat()}

@router.get("/{media_id}")
async def list_comments(media_id: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Comment).where(Comment.media_id == uuid.UUID(media_id)).order_by(Comment.created_at))
    return [{"id": str(c.id),"body": c.body,"author_id": str(c.author_id),"created_at": c.created_at.isoformat()} for c in r.scalars().all()]

@router.delete("/{cid}")
async def delete(cid: str, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    r = await db.execute(select(Comment).where(Comment.id == uuid.UUID(cid), Comment.author_id == cu.id))
    c = r.scalar_one_or_none()
    if not c: raise HTTPException(404)
    await db.delete(c)
    await log_action(db, "delete_comment", cu.id, details={"comment_id": cid}, ip_address=request.client.host if request else None)
    return {"status": "deleted"}
