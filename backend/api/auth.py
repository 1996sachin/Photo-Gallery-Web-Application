import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from pathlib import Path
from email.message import EmailMessage
import secrets
import hashlib
import smtplib
import ssl
import httpx
import pyotp
import qrcode
import io
import base64
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from models.database import get_db, User
from services.audit_service import log_action
from services.security_service import sanitize_text
from services.limiter import limiter
import os

router = APIRouter()
SECRET_KEY = os.getenv("SECRET_KEY", "change-in-production")
ALGORITHM  = "HS256"
EXPIRE_MIN = 60 * 24 * 7
AVATAR_DIR = Path("uploads/avatars")
ALLOWED_AVATAR = {"image/jpeg", "image/png", "image/webp", "image/gif"}
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", APP_URL)
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
    role: str = "client"
    email_verified: bool = False
    email_verification_requested_at: Optional[datetime] = None
    class Config: from_attributes = True


class Token(BaseModel):
    access_token: str; token_type: str; user: UserOut
    mfa_required: bool = False
    mfa_token: Optional[str] = None


class MfaSetup(BaseModel):
    secret: str
    otpauth_url: str
    qr_code: str  # base64


class MfaVerify(BaseModel):
    code: str
    secret: Optional[str] = None
    mfa_token: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None


class EmailOtpVerify(BaseModel):
    code: str


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    email: str
    code: str
    password: str


def make_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)}, SECRET_KEY, algorithm=ALGORITHM)


def make_mfa_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "mfa": True, "exp": datetime.utcnow() + timedelta(minutes=10)}, SECRET_KEY, algorithm=ALGORITHM)


def make_state_token(sub: str) -> str:
    return jwt.encode(
        {"sub": sub, "scope": "google_oauth", "exp": datetime.utcnow() + timedelta(minutes=10)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _require_gmail(email: str):
    # Gmail-only restriction removed; any email domain is now allowed.
    pass


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _make_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.now(timezone.utc)
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < now


def send_code_email(to_email: str, code: str, subject: str, purpose: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise HTTPException(500, "SMTP is not configured")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        f"Enter this code in Memories to {purpose}:\n\n"
        f"{code}\n\n"
        "This code expires in 10 minutes."
    )

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            if SMTP_TLS:
                server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"FAILED TO SEND EMAIL: {e}")
        # In local dev, we don't want to crash the app just because email failed.
        # The user can find the code in the logs if they are watching.
        print(f"EMAIL CONTENT: {purpose} code for {to_email} is {code}")


def send_verification_email(to_email: str, code: str):
    send_code_email(
        to_email,
        code,
        "Your Memories verification code",
        "verify your Gmail account",
    )


def send_password_reset_email(to_email: str, code: str):
    send_code_email(
        to_email,
        code,
        "Your Memories password reset code",
        "reset your password",
    )


def issue_email_otp(u: User):
    code = _make_otp()
    u.email_verification_token = _hash_otp(code)
    u.email_verification_requested_at = datetime.now(timezone.utc)
    u.email_verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    send_verification_email(u.email, code)


def issue_password_reset_otp(u: User):
    code = _make_otp()
    u.password_reset_token = _hash_otp(code)
    u.password_reset_requested_at = datetime.now(timezone.utc)
    u.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    send_password_reset_email(u.email, code)


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


async def get_verified_user(cu: User = Depends(get_current_user)) -> User:
    if not cu.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verify your Gmail account before using the app")
    return cu


class RoleChecker:
    def __init__(self, *allowed_roles: str):
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, cu: User = Depends(get_verified_user)) -> User:
        if cu.role not in self.allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return cu


require_admin = RoleChecker("admin")
require_business_or_admin = RoleChecker("business", "admin")


def _out(u: User) -> UserOut:
    return UserOut(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        bio=u.bio,
        role=u.role or "client",
        email_verified=bool(u.email_verified),
        email_verification_requested_at=u.email_verification_requested_at,
    )


@router.get("/mfa/setup", response_model=MfaSetup)
async def mfa_setup(cu: User = Depends(get_current_user)):
    if cu.mfa_enabled:
        raise HTTPException(400, "MFA is already enabled")
    
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(name=cu.email, issuer_name="Memories")
    
    img = qrcode.make(otpauth_url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    qr_base64 = base64.b64encode(buf.getvalue()).decode()
    
    return MfaSetup(secret=secret, otpauth_url=otpauth_url, qr_code=qr_base64)


@router.post("/mfa/enable")
async def mfa_enable(payload: MfaVerify, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    if cu.mfa_enabled:
        raise HTTPException(400, "MFA is already enabled")
    if not payload.secret:
        raise HTTPException(400, "Secret is required for first-time enablement")
    
    totp = pyotp.TOTP(payload.secret)
    if not totp.verify(payload.code):
        raise HTTPException(400, "Invalid MFA code")
    
    cu.mfa_secret = payload.secret
    cu.mfa_enabled = True
    await log_action(db, "mfa_enabled", cu.id, ip_address=request.client.host if request else None)
    return {"status": "enabled"}


@router.post("/mfa/disable")
async def mfa_disable(payload: MfaVerify, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user), request: Request = None):
    if not cu.mfa_enabled:
        raise HTTPException(400, "MFA is not enabled")
    
    totp = pyotp.TOTP(cu.mfa_secret)
    if not totp.verify(payload.code):
        raise HTTPException(400, "Invalid MFA code")
    
    cu.mfa_secret = None
    cu.mfa_enabled = False
    await log_action(db, "mfa_disabled", cu.id, ip_address=request.client.host if request else None)
    return {"status": "disabled"}


@router.post("/mfa/verify", response_model=Token)
async def mfa_verify(payload: MfaVerify, db: AsyncSession = Depends(get_db), request: Request = None):
    if not payload.mfa_token:
        raise HTTPException(400, "MFA token is required")
    
    try:
        data = jwt.decode(payload.mfa_token, SECRET_KEY, algorithms=[ALGORITHM])
        if not data.get("mfa"): raise JWTError()
        uid = data.get("sub")
    except JWTError:
        raise HTTPException(401, "Invalid or expired MFA token")
    
    r = await db.execute(select(User).where(User.id == uuid.UUID(uid)))
    u = r.scalar_one_or_none()
    if not u or not u.mfa_enabled:
        raise HTTPException(401, "User not found or MFA not enabled")
    
    totp = pyotp.TOTP(u.mfa_secret)
    if not totp.verify(payload.code):
        await log_action(db, "mfa_failed", u.id, ip_address=request.client.host if request else None)
        raise HTTPException(401, "Invalid MFA code")
    
    await log_action(db, "login_success_mfa", u.id, ip_address=request.client.host if request else None)
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.post("/register", response_model=Token)
@limiter.limit("5/minute")
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db), request: Request = None):
    email = _normalize_email(payload.email)
    _require_gmail(email)
    r = await db.execute(select(User).where(User.email == email))
    existing = r.scalar_one_or_none()
    if existing:
        if not pwd.verify(payload.password, existing.password_hash):
            raise HTTPException(400, "Email already registered. Sign in to continue.")
        if not existing.email_verified:
            issue_email_otp(existing)
        return Token(access_token=make_token(str(existing.id)), token_type="bearer", user=_out(existing))
    user_count = await db.scalar(select(func.count(User.id))) or 0
    u = User(
        email=email,
        password_hash=pwd.hash(payload.password),
        display_name=payload.display_name,
        role="admin" if user_count == 0 else "client",
    )
    db.add(u); await db.flush()
    await log_action(db, "register", u.id, ip_address=request.client.host if request else None)
    issue_email_otp(u)
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.post("/token", response_model=Token)
@limiter.limit("5/minute")
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db), request: Request = None):
    r = await db.execute(select(User).where(User.email == _normalize_email(form.username)))
    u = r.scalar_one_or_none()
    if not u or not pwd.verify(form.password, u.password_hash):
        if u: await log_action(db, "login_failed", u.id, ip_address=request.client.host if request else None)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    
    if u.mfa_enabled:
        await log_action(db, "mfa_required", u.id, ip_address=request.client.host if request else None)
        return Token(
            access_token="", token_type="bearer", user=_out(u),
            mfa_required=True, mfa_token=make_mfa_token(str(u.id))
        )
    
    await log_action(db, "login_success", u.id, ip_address=request.client.host if request else None)
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.post("/forgot-password")
async def forgot_password(payload: PasswordResetRequest, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    _require_gmail(email)
    r = await db.execute(select(User).where(User.email == email))
    u = r.scalar_one_or_none()
    if u:
        issue_password_reset_otp(u)
    return {"status": "requested", "message": "If this Gmail account exists, a reset code has been sent."}


@router.post("/reset-password")
async def reset_password(payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db), request: Request = None):
    email = _normalize_email(payload.email)
    code = "".join(ch for ch in payload.code if ch.isdigit())
    if len(code) != 6:
        raise HTTPException(400, "Enter the 6 digit reset code")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")

    r = await db.execute(select(User).where(User.email == email))
    u = r.scalar_one_or_none()
    if (
        not u
        or not u.password_reset_token
        or not u.password_reset_expires_at
        or _is_expired(u.password_reset_expires_at)
        or _hash_otp(code) != u.password_reset_token
    ):
        if u: await log_action(db, "password_reset_failed", u.id, ip_address=request.client.host if request else None)
        raise HTTPException(400, "Reset code is invalid or expired")

    u.password_hash = pwd.hash(payload.password)
    u.password_reset_token = None
    u.password_reset_expires_at = None
    await log_action(db, "password_reset_success", u.id, ip_address=request.client.host if request else None)
    return {"status": "reset", "message": "Password updated. Sign in with your new password."}


@router.get("/me", response_model=UserOut)
async def me(cu: User = Depends(get_current_user)):
    return _out(cu)


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    if payload.display_name is not None:
        name = sanitize_text(payload.display_name.strip())
        if not name:
            raise HTTPException(400, "Display name is required")
        cu.display_name = name[:100]

    if payload.bio is not None:
        cu.bio = sanitize_text(payload.bio.strip())[:1000] or None

    if payload.email is not None:
        email = _normalize_email(payload.email)
        if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
            raise HTTPException(400, "Valid email is required")
        _require_gmail(email)
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
    cu.avatar_url = f"{APP_URL}/uploads/avatars/{name}"
    return _out(cu)


@router.post("/me/request-email-verification")
async def request_email_verification(cu: User = Depends(get_current_user)):
    if cu.email_verified:
        return {"status": "verified", "message": "Email is already verified"}
    _require_gmail(cu.email.lower())
    issue_email_otp(cu)
    return {
        "status": "requested",
        "message": "Verification code sent to your Gmail account.",
        "requested_at": cu.email_verification_requested_at.isoformat(),
    }


@router.post("/me/verify-email-otp", response_model=UserOut)
async def verify_email_otp(payload: EmailOtpVerify, cu: User = Depends(get_current_user)):
    code = "".join(ch for ch in payload.code if ch.isdigit())
    if len(code) != 6:
        raise HTTPException(400, "Enter the 6 digit verification code")
    if not cu.email_verification_token or not cu.email_verification_expires_at:
        raise HTTPException(400, "Request a new verification code")
    if _is_expired(cu.email_verification_expires_at):
        raise HTTPException(400, "Verification code expired")
    if _hash_otp(code) != cu.email_verification_token:
        raise HTTPException(400, "Invalid verification code")
    cu.email_verified = True
    cu.email_verification_token = None
    cu.email_verification_expires_at = None
    return _out(cu)


@router.get("/verify-email", response_class=HTMLResponse)
async def verify_email(token: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email_verification_token == token))
    u = r.scalar_one_or_none()
    if not u or not u.email_verification_expires_at or _is_expired(u.email_verification_expires_at):
        raise HTTPException(400, "Verification link is invalid or expired")
    u.email_verified = True
    u.email_verification_token = None
    u.email_verification_expires_at = None
    await db.commit()
    return HTMLResponse(
        "<html><body><h1>Email verified</h1>"
        "<p>Your Gmail account is verified. You can close this tab and return to Memories.</p>"
        f"<script>setTimeout(function(){{ window.location.href='{FRONTEND_URL}/profile'; }}, 1200)</script>"
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
        f"<script>setTimeout(function(){{ window.location.href='{FRONTEND_URL}/profile'; }}, 1000)</script>"
        "</body></html>"
    )
