import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Person, User
from api.auth import get_verified_user as get_current_user

router = APIRouter()

class PersonIn(BaseModel):
    name: str

@router.post("/")
async def create(p: PersonIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    person = Person(owner_id=cu.id, name=p.name)
    db.add(person); await db.flush()
    return {"id": str(person.id), "name": person.name, "avatar_url": None}

@router.get("/")
async def list_people(db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Person).where(Person.owner_id == cu.id).order_by(Person.name))
    return [{"id": str(p.id), "name": p.name, "avatar_url": p.avatar_url} for p in r.scalars().all()]
