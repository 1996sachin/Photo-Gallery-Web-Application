"""
Memories App v2 — FastAPI Backend
Run: uvicorn main:app --reload --port 8000
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from services.limiter import limiter

from models.database import create_tables
from api.auth import router as auth_router
from api.media import router as media_router
from api.albums import router as albums_router
from api.comments import router as comments_router
from api.people import router as people_router
from api.edits import router as edits_router
from api.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    for d in ["uploads/originals", "uploads/thumbnails", "uploads/edited", "uploads/avatars"]:
        os.makedirs(d, exist_ok=True)
    await create_tables()
    yield


app = FastAPI(title="Memories API", version="2.0.0", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", 
        "http://localhost:5174", 
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000"
    ],
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

@app.get("/api/health")
async def health(): return {"status": "ok"}

from fastapi.responses import FileResponse
import os

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    f = f"dist/{full_path}"
    if os.path.exists(f) and os.path.isfile(f):
        return FileResponse(f)
    return FileResponse("dist/index.html")
