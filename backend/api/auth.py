import uuid
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from email.message import EmailMessage
import secrets
import smtplib
import ssl
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models.database import get_db, User
import os

router = APIRouter()
SECRET_KEY = os.getenv("SECRET_KEY", "change-in-production")
ALGORITHM  = "HS256"
EXPIRE_MIN = 60 * 24 * 7
AVATAR_DIR = Path("uploads/avatars")
ALLOWED_AVATAR = {"image/jpeg", "image/png", "image/webp", "image/gif"}
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM") or SMTP_USERNAME
SMTP_TLS = os.getenv("SMTP_TLS", "true").lower() != "false"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", f"{APP_URL}/api/auth/google/callback")

pwd  = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


class UserCreate(BaseModel):
    email: str
    password: str
    display_name: str


class UserOut(BaseModel):
    id: str; email: str; display_name: str; avatar_url: Optional[str] = None
    bio: Optional[str] = None
    email_verified: bool = False
    email_verification_requested_at: Optional[datetime] = None
    class Config: from_attributes = True


class Token(BaseModel):
    access_token: str; token_type: str; user: UserOut


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None


def make_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)}, SECRET_KEY, algorithm=ALGORITHM)


def make_state_token(sub: str) -> str:
    return jwt.encode(
        {"sub": sub, "scope": "google_oauth", "exp": datetime.utcnow() + timedelta(minutes=10)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def send_verification_email(to_email: str, token: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise HTTPException(500, "SMTP is not configured")

    link = f"{APP_URL}/api/auth/verify-email?token={token}"
    msg = EmailMessage()
    msg["Subject"] = "Verify your Memories Gmail account"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        "Verify your Memories account by opening this link:\n\n"
        f"{link}\n\n"
        "This link expires in 24 hours."
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls(context=context)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)


async def get_current_user(token: str = Depends(oauth2), db: AsyncSession = Depends(get_db)) -> User:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid: raise exc
    except JWTError: raise exc
    r = await db.execute(select(User).where(User.id == uuid.UUID(uid)))
    u = r.scalar_one_or_none()
    if not u: raise exc
    return u


def _out(u: User) -> UserOut:
    return UserOut(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        bio=u.bio,
        email_verified=bool(u.email_verified),
        email_verification_requested_at=u.email_verification_requested_at,
    )


@router.post("/register", response_model=Token)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email == payload.email))
    if r.scalar_one_or_none(): raise HTTPException(400, "Email already registered")
    u = User(email=payload.email, password_hash=pwd.hash(payload.password), display_name=payload.display_name)
    db.add(u); await db.flush()
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.post("/token", response_model=Token)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email == form.username))
    u = r.scalar_one_or_none()
    if not u or not pwd.verify(form.password, u.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.get("/me", response_model=UserOut)
async def me(cu: User = Depends(get_current_user)):
    return _out(cu)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    if payload.display_name is not None:
        name = payload.display_name.strip()
        if not name:
            raise HTTPException(400, "Display name is required")
        cu.display_name = name[:100]

    if payload.bio is not None:
        cu.bio = payload.bio.strip()[:1000] or None

    if payload.email is not None:
        email = payload.email.strip().lower()
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise HTTPException(400, "Valid email is required")
        if email != cu.email:
            r = await db.execute(select(User).where(User.email == email, User.id != cu.id))
            if r.scalar_one_or_none():
                raise HTTPException(400, "Email already registered")
            cu.email = email
            cu.email_verified = False
            cu.email_verification_requested_at = None

    return _out(cu)


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(file: UploadFile = File(...), cu: User = Depends(get_current_user)):
    mime = file.content_type or ""
    if mime not in ALLOWED_AVATAR:
        raise HTTPException(400, f"Unsupported avatar type: {mime}")
    ext = Path(file.filename or "avatar").suffix.lower() or ".jpg"
    name = f"{cu.id}{ext}"
    AVATAR_DIR.mkdir(parents=True, exist_ok=True)
    dest = AVATAR_DIR / name
    size = 0
    with dest.open("wb") as f:
        while chunk := await file.read(1 << 20):
            size += len(chunk)
            if size > 5 * 1024 * 1024:
                dest.unlink(missing_ok=True)
                raise HTTPException(413, "Avatar too large (max 5 MB)")
            f.write(chunk)
    cu.avatar_url = f"http://localhost:8000/uploads/avatars/{name}"
    return _out(cu)


@router.post("/me/request-email-verification")
async def request_email_verification(cu: User = Depends(get_current_user)):
    if cu.email_verified:
        return {"status": "verified", "message": "Email is already verified"}
    if not cu.email.lower().endswith("@gmail.com"):
        raise HTTPException(400, "Use a Gmail address before requesting Gmail verification")
    token = secrets.token_urlsafe(32)
    cu.email_verification_token = token
    cu.email_verification_requested_at = datetime.utcnow()
    cu.email_verification_expires_at = datetime.utcnow() + timedelta(hours=24)
    send_verification_email(cu.email, token)
    return {
        "status": "requested",
        "message": "Verification email sent to your Gmail account.",
        "requested_at": cu.email_verification_requested_at.isoformat(),
    }


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email_verification_token == token))
    u = r.scalar_one_or_none()
    if not u or not u.email_verification_expires_at or u.email_verification_expires_at < datetime.utcnow():
        raise HTTPException(400, "Verification link is invalid or expired")
    u.email_verified = True
    u.email_verification_token = None
    u.email_verification_expires_at = None
    await db.commit()
    return HTMLResponse(
        "<html><body><h1>Email verified</h1>"
        "<p>Your Gmail account is verified. You can close this tab and return to Memories.</p>"
        "<script>setTimeout(function(){ window.location.href='/profile'; }, 1200)</script>"
        "</body></html>"
    )


@router.get("/google/start")
async def google_start(cu: User = Depends(get_current_user)):
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(500, "Google OAuth is not configured")
    state = make_state_token(str(cu.id))
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    url = httpx.URL("https://accounts.google.com/o/oauth2/v2/auth", params=params)
    return {"auth_url": str(url)}


@router.get("/google/callback", response_class=HTMLResponse)
async def google_callback(request: Request, code: str, state: str, db: AsyncSession = Depends(get_db)):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth is not configured")
    try:
        payload = jwt.decode(state, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "google_oauth":
            raise JWTError()
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        raise HTTPException(400, "Invalid OAuth state")

    async with httpx.AsyncClient(timeout=20) as client:
        token_res = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if token_res.status_code >= 400:
            raise HTTPException(400, "Could not exchange Google OAuth code")
        access_token = token_res.json().get("access_token")
        info_res = await client.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if info_res.status_code >= 400:
            raise HTTPException(400, "Could not fetch Google profile")

    info = info_res.json()
    email = (info.get("email") or "").lower()
    if not email.endswith("@gmail.com"):
        raise HTTPException(400, "Google account is not a Gmail address")
    if not info.get("email_verified"):
        raise HTTPException(400, "Google did not report this email as verified")

    r = await db.execute(select(User).where(User.id == user_id))
    u = r.scalar_one_or_none()
    if not u:
        raise HTTPException(404, "User not found")
    if email != u.email:
        dupe = await db.execute(select(User).where(User.email == email, User.id != u.id))
        if dupe.scalar_one_or_none():
            raise HTTPException(400, "Google email already belongs to another user")
        u.email = email
    u.email_verified = True
    u.email_verification_token = None
    u.email_verification_expires_at = None
    await db.commit()
    return HTMLResponse(
        "<html><body><h1>Google account verified</h1>"
        "<p>Your Gmail account is verified. Returning to Memories...</p>"
        "<script>setTimeout(function(){ window.location.href='/profile'; }, 1000)</script>"
        "</body></html>"
    )
