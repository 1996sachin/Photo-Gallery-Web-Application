from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from models.database import get_db, Tenant, User
from api.auth import require_admin
from pydantic import BaseModel, constr
from uuid import UUID

router = APIRouter()

class TenantCreate(BaseModel):
    name: str
    slug: constr(pattern=r"^[a-z0-9-]+$") # enforce safe subdomain chars

class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    is_active: bool

    class Config:
        from_attributes = True

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None

@router.post("/", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate, 
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(require_admin)
):
    # Check if slug is already taken
    slug = payload.slug.strip().lower()
    if slug in ("www", "admin", "memories", "api"):
        raise HTTPException(status_code=400, detail=f"Subdomain '{slug}' is reserved.")
        
    stmt = select(Tenant).where(Tenant.slug == slug)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Subdomain '{slug}' is already taken.")

    tenant = Tenant(name=payload.name.strip(), slug=slug)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant

@router.get("/", response_model=List[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_db), 
    current_user: User = Depends(require_admin)
):
    stmt = select(Tenant).order_by(Tenant.created_at.desc())
    res = await db.execute(stmt)
    return res.scalars().all()

@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: UUID,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
        
    if payload.name is not None:
        tenant.name = payload.name.strip()
    if payload.is_active is not None:
        tenant.is_active = payload.is_active
        
    await db.commit()
    await db.refresh(tenant)
    return tenant
