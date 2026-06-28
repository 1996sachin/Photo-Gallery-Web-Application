"""
Memories App v2 — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.limiter import limiter

from models.database import create_tables, get_db, AsyncSessionLocal
from api.auth import router as auth_router, get_user_from_token
from api.media import router as media_router
from api.albums import router as albums_router
from api.comments import router as comments_router
from api.people import router as people_router
from api.edits import router as edits_router
from api.admin import router as admin_router
from api.admin_tenants import router as admin_tenants_router
from api.access import router as access_router
from api.activity import router as activity_router
from api.sync import router as sync_router
from services.websocket_manager import manager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure all upload directories exist
    for d in ["uploads/originals", "uploads/thumbnails", "uploads/edited", "uploads/avatars"]:
        os.makedirs(os.path.join(os.getcwd(), d), exist_ok=True)
    
    await create_tables()
    from services.storage import ensure_bucket
    ensure_bucket()
    yield


app = FastAPI(title="Memories API", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:8000").split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(auth_router,     prefix="/api/auth",     tags=["auth"])
app.include_router(media_router,    prefix="/api/media",    tags=["media"])
app.include_router(albums_router,   prefix="/api/albums",   tags=["albums"])
app.include_router(comments_router, prefix="/api/comments", tags=["comments"])
app.include_router(people_router,   prefix="/api/people",   tags=["people"])
app.include_router(edits_router,    prefix="/api/edits",    tags=["edits"])
app.include_router(admin_router,    prefix="/api/admin",    tags=["admin"])
app.include_router(admin_tenants_router, prefix="/api/admin/tenants", tags=["admin_tenants"])
app.include_router(access_router,   prefix="/api/access",   tags=["access"])
app.include_router(activity_router, prefix="/api/activity", tags=["activity"])
app.include_router(sync_router,     prefix="/api/sync",     tags=["sync"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    token = token or websocket.cookies.get("memories_access_token")
    logger.info("Incoming WebSocket connection attempt")
    if not token:
        logger.warning("WebSocket connection rejected: Missing token")
        await websocket.close(code=1008)
        return
    async with AsyncSessionLocal() as db:
        user = await get_user_from_token(token, db)
    
    if not user:
        logger.warning("WebSocket connection rejected: Invalid token")
        await websocket.close(code=1008)
        return
    
    await manager.connect(str(user.id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(str(user.id), websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user.id}: {e}")
        manager.disconnect(str(user.id), websocket)

@app.get("/api/health")
async def health(): return {"status": "ok"}

from fastapi.responses import FileResponse

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    f = f"dist/{full_path}"
    if os.path.exists(f) and os.path.isfile(f):
        return FileResponse(f)
    return FileResponse("dist/index.html")
