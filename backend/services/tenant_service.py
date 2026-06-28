import os
from urllib.parse import urlparse
from fastapi import Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_db, Tenant

# Parse the base host from APP_URL env variable
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
parsed_app_url = urlparse(APP_URL)
base_host = parsed_app_url.netloc.split(":")[0].lower()

def get_subdomain(request: Request) -> str:
    host_header = request.headers.get("host", "")
    if not host_header:
        return ""
    
    # Strip port if any
    host = host_header.split(":")[0].lower()
    
    # If host is exactly the base host, or matches localhost, no subdomain
    if host == base_host or host in ("localhost", "127.0.0.1"):
        return ""
    
    # Check if host ends with the base host
    if base_host and host.endswith("." + base_host):
        subdomain = host[:-len(base_host)-1]
        return subdomain
    
    # Fallback parsing: if host has more parts than the base host
    parts = host.split(".")
    base_parts = base_host.split(".")
    if len(parts) > len(base_parts):
        return parts[0]
        
    return ""

async def get_current_tenant(request: Request, db: AsyncSession = Depends(get_db)) -> Tenant:
    subdomain = get_subdomain(request)
    if not subdomain or subdomain in ("www", "admin", "memories", "api"):
        return None
    
    stmt = select(Tenant).where(Tenant.slug == subdomain, Tenant.is_active == True)
    res = await db.execute(stmt)
    tenant = res.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant '{subdomain}' not found or inactive")
    return tenant
