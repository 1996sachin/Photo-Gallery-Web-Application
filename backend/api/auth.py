import uuid
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from email.message import EmailMessage
import secrets
import hashlib
import smtplib
import ssl
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import desc, select
from models.database import get_db, User, UserActivityEvent
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
    email_verified: bool = False
    email_verification_requested_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    total_online_seconds: int = 0
    last_activity: Optional[str] = None
    class Config: from_attributes = True


class Token(BaseModel):
    access_token: str; token_type: str; user: UserOut


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


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class ActivityEventOut(BaseModel):
    activity: str
    path: Optional[str] = None
    created_at: datetime
    class Config: from_attributes = True


class UserActivityOut(UserOut):
    online: bool = False
    current_session_started_at: Optional[datetime] = None
    recent_events: list[ActivityEventOut] = Field(default_factory=list)


def make_token(sub: str) -> str:
    return jwt.encode({"sub": sub, "exp": datetime.utcnow() + timedelta(minutes=EXPIRE_MIN)}, SECRET_KEY, algorithm=ALGORITHM)


def make_state_token(sub: str) -> str:
    return jwt.encode(
        {"sub": sub, "scope": "google_oauth", "exp": datetime.utcnow() + timedelta(minutes=10)},
        SECRET_KEY,
        algorithm=ALGORITHM,
    )


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _require_gmail(email: str):
    if not email.endswith("@gmail.com"):
        raise HTTPException(400, "Use a Gmail address to create and verify your account")


def password_strength(password: str) -> tuple[str, list[str]]:
    suggestions = []
    if len(password) < 8:
        suggestions.append("Use at least 8 characters")
    if password.lower() in {"password", "password123", "123456", "12345678", "qwerty"}:
        suggestions.append("Avoid common passwords")
    if not any(ch.islower() for ch in password):
        suggestions.append("Add a lowercase letter")
    if not any(ch.isupper() for ch in password):
        suggestions.append("Add an uppercase letter")
    if not any(ch.isdigit() for ch in password):
        suggestions.append("Add a number")
    if not any(not ch.isalnum() for ch in password):
        suggestions.append("Add a symbol")
    if len(password) >= 12 and len(suggestions) <= 1:
        return "strong", suggestions
    if len(suggestions) <= 2 and len(password) >= 8:
        return "medium", suggestions
    return "weak", suggestions


def require_not_weak_password(password: str, label: str = "Password"):
    strength, suggestions = password_strength(password)
    if strength == "weak":
        raise HTTPException(
            400,
            {
                "message": f"{label} is weak",
                "strength": strength,
                "suggestions": suggestions,
            },
        )


def _hash_otp(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _make_otp() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _mask_email(email: str) -> str:
    local, _, domain = email.strip().lower().partition("@")
    if not local or not domain:
        return "your Gmail account"
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[0] + ("*" * (len(local) - 2)) + local[-1]
    return f"{masked_local}@{domain}"


def _is_expired(expires_at: datetime) -> bool:
    now = datetime.utcnow()
    if expires_at.tzinfo is not None:
        now = now.replace(tzinfo=expires_at.tzinfo)
    return expires_at < now


def _is_online(last_seen_at: Optional[datetime]) -> bool:
    if not last_seen_at:
        return False
    now = datetime.utcnow()
    if last_seen_at.tzinfo is not None:
        now = now.replace(tzinfo=last_seen_at.tzinfo)
    return now - last_seen_at <= timedelta(minutes=2)


def _request_ip(request: Request) -> Optional[str]:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()[:64]
    return request.client.host[:64] if request.client else None


def record_activity(
    db: AsyncSession,
    user: User,
    activity: str,
    request: Optional[Request] = None,
    write_event: bool = True,
):
    now = datetime.utcnow()
    if user.last_seen_at:
        previous = user.last_seen_at
        if previous.tzinfo is not None:
            now_for_delta = now.replace(tzinfo=previous.tzinfo)
        else:
            now_for_delta = now
        gap_seconds = int((now_for_delta - previous).total_seconds())
        if 0 < gap_seconds <= 120:
            user.total_online_seconds = (user.total_online_seconds or 0) + gap_seconds
    user.last_seen_at = now
    user.last_activity = activity
    if activity in {"Signed in", "Registered", "Heartbeat"} and not user.current_session_started_at:
        user.current_session_started_at = now
    if activity == "Signed out":
        user.current_session_started_at = None
    if write_event:
        db.add(UserActivityEvent(
            user_id=user.id,
            activity=activity,
            path=str(request.url.path) if request else None,
            user_agent=(request.headers.get("user-agent")[:500] if request and request.headers.get("user-agent") else None),
            ip_address=_request_ip(request) if request else None,
        ))


def _route_activity_label(request: Request) -> str:
    path = request.url.path
    if path.endswith("/upload"):
        return "Uploaded media"
    if "/favorite" in path:
        return "Updated favorite"
    if "/api/albums" in path:
        return "Changed albums"
    if "/api/comments" in path:
        return "Changed comments"
    if "/api/people" in path:
        return "Managed people"
    if "/api/edits" in path:
        return "Edited media"
    if "/api/media" in path:
        return "Changed media"
    return f"{request.method} {path}"


def send_code_email(to_email: str, code: str, subject: str, purpose: str):
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise HTTPException(500, "SMTP is not configured")

    masked_email = _mask_email(to_email)
    purpose_title = purpose.capitalize()
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = "Undisclosed recipients:;"
    msg.set_content(
        f"Memories security code\n\n"
        f"{code}\n\n"
        f"Use this code to {purpose} for {masked_email}.\n"
        "This code expires in 10 minutes. Do not share it with anyone."
    )
    msg.add_alternative(
        f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f6f7;font-family:Arial,Helvetica,sans-serif;color:#1c1e21;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f6f7;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:520px;background:#ffffff;border:1px solid #dddfe2;border-radius:8px;">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid #e4e6eb;font-size:20px;font-weight:700;color:#1877f2;">
                Memories
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <div style="font-size:18px;font-weight:600;margin-bottom:12px;">{purpose_title}</div>
                <div style="font-size:15px;line-height:22px;margin-bottom:18px;">
                  Use this security code for <strong>{masked_email}</strong>.
                </div>
                <div style="font-size:32px;letter-spacing:8px;font-weight:700;padding:16px 18px;background:#f0f2f5;border-radius:6px;text-align:center;color:#050505;">
                  {code}
                </div>
                <div style="font-size:13px;line-height:20px;color:#65676b;margin-top:18px;">
                  This code expires in 10 minutes. Do not share this code with anyone.
                </div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
""",
        subtype="html",
    )

    context = ssl.create_default_context()
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
        if SMTP_TLS:
            server.starttls(context=context)
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg, to_addrs=[to_email])


def send_verification_email(to_email: str, code: str):
    send_code_email(
        to_email,
        code,
        "Memories security code",
        "verify your Gmail account",
    )


def send_password_reset_email(to_email: str, code: str):
    send_code_email(
        to_email,
        code,
        "Memories security code",
        "reset your password",
    )


def issue_email_otp(u: User):
    code = _make_otp()
    u.email_verification_token = _hash_otp(code)
    u.email_verification_requested_at = datetime.utcnow()
    u.email_verification_expires_at = datetime.utcnow() + timedelta(minutes=10)
    send_verification_email(u.email, code)


def issue_password_reset_otp(u: User):
    code = _make_otp()
    u.password_reset_token = _hash_otp(code)
    u.password_reset_requested_at = datetime.utcnow()
    u.password_reset_expires_at = datetime.utcnow() + timedelta(minutes=10)
    send_password_reset_email(u.email, code)


async def get_current_user(request: Request, token: str = Depends(oauth2), db: AsyncSession = Depends(get_db)) -> User:
    exc = HTTPException(status.HTTP_401_UNAUTHORIZED, "Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        uid = payload.get("sub")
        if not uid: raise exc
    except JWTError: raise exc
    r = await db.execute(select(User).where(User.id == uuid.UUID(uid)))
    u = r.scalar_one_or_none()
    if not u: raise exc
    is_auth_path = request.url.path.startswith("/api/auth")
    should_log_action = request.method != "GET" and not is_auth_path
    record_activity(
        db,
        u,
        _route_activity_label(request) if should_log_action else "Active",
        request,
        write_event=should_log_action,
    )
    return u


async def get_verified_user(cu: User = Depends(get_current_user)) -> User:
    if not cu.email_verified:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Verify your Gmail account before using the app")
    return cu


def _out(u: User) -> UserOut:
    return UserOut(
        id=str(u.id),
        email=u.email,
        display_name=u.display_name,
        avatar_url=u.avatar_url,
        bio=u.bio,
        email_verified=bool(u.email_verified),
        email_verification_requested_at=u.email_verification_requested_at,
        last_seen_at=u.last_seen_at,
        total_online_seconds=u.total_online_seconds or 0,
        last_activity=u.last_activity,
    )


@router.post("/register", response_model=Token)
async def register(payload: UserCreate, request: Request, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    _require_gmail(email)
    require_not_weak_password(payload.password)
    r = await db.execute(select(User).where(User.email == email))
    existing = r.scalar_one_or_none()
    if existing:
        if not pwd.verify(payload.password, existing.password_hash):
            raise HTTPException(400, "Email already registered. Sign in to continue.")
        if not existing.email_verified:
            issue_email_otp(existing)
        record_activity(db, existing, "Signed in", request)
        return Token(access_token=make_token(str(existing.id)), token_type="bearer", user=_out(existing))
    u = User(email=email, password_hash=pwd.hash(payload.password), display_name=payload.display_name)
    db.add(u); await db.flush()
    issue_email_otp(u)
    record_activity(db, u, "Registered", request)
    return Token(access_token=make_token(str(u.id)), token_type="bearer", user=_out(u))


@router.post("/token", response_model=Token)
async def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(User).where(User.email == _normalize_email(form.username)))
    u = r.scalar_one_or_none()
    if not u or not pwd.verify(form.password, u.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    record_activity(db, u, "Signed in", request)
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
async def reset_password(payload: PasswordResetConfirm, db: AsyncSession = Depends(get_db)):
    email = _normalize_email(payload.email)
    code = "".join(ch for ch in payload.code if ch.isdigit())
    if len(code) != 6:
        raise HTTPException(400, "Enter the 6 digit reset code")
    if len(payload.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters")
    require_not_weak_password(payload.password)

    r = await db.execute(select(User).where(User.email == email))
    u = r.scalar_one_or_none()
    if (
        not u
        or not u.password_reset_token
        or not u.password_reset_expires_at
        or _is_expired(u.password_reset_expires_at)
        or _hash_otp(code) != u.password_reset_token
    ):
        raise HTTPException(400, "Reset code is invalid or expired")

    u.password_hash = pwd.hash(payload.password)
    u.password_reset_token = None
    u.password_reset_expires_at = None
    return {"status": "reset", "message": "Password updated. Sign in with your new password."}


@router.get("/me", response_model=UserOut)
async def me(cu: User = Depends(get_current_user)):
    return _out(cu)


@router.post("/me/activity", response_model=UserOut)
async def heartbeat(request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    record_activity(db, cu, "Heartbeat", request, write_event=False)
    return _out(cu)


@router.post("/logout")
async def logout(request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    record_activity(db, cu, "Signed out", request)
    return {"status": "signed_out"}


@router.get("/users/activity", response_model=list[UserActivityOut])
async def users_activity(db: AsyncSession = Depends(get_db), cu: User = Depends(get_verified_user)):
    users_result = await db.execute(select(User).order_by(User.display_name))
    users = users_result.scalars().all()
    output = []
    for user in users:
        events_result = await db.execute(
            select(UserActivityEvent)
            .where(UserActivityEvent.user_id == user.id)
            .order_by(desc(UserActivityEvent.created_at))
            .limit(5)
        )
        output.append(UserActivityOut(
            **_out(user).model_dump(),
            online=_is_online(user.last_seen_at),
            current_session_started_at=user.current_session_started_at,
            recent_events=events_result.scalars().all(),
        ))
    return output


@router.patch("/me", response_model=UserOut)
async def update_me(payload: UserUpdate, request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    if payload.display_name is not None:
        name = payload.display_name.strip()
        if not name:
            raise HTTPException(400, "Display name is required")
        cu.display_name = name[:100]

    if payload.bio is not None:
        cu.bio = payload.bio.strip()[:1000] or None

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

    record_activity(db, cu, "Updated profile", request)
    return _out(cu)


@router.patch("/me/password")
async def change_password(payload: PasswordChange, request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    if not pwd.verify(payload.current_password, cu.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    if len(payload.new_password) < 6:
        raise HTTPException(400, "New password must be at least 6 characters")
    require_not_weak_password(payload.new_password, "New password")
    if pwd.verify(payload.new_password, cu.password_hash):
        raise HTTPException(400, "New password must be different from the current password")
    cu.password_hash = pwd.hash(payload.new_password)
    cu.password_reset_token = None
    cu.password_reset_expires_at = None
    record_activity(db, cu, "Changed password", request)
    return {"status": "updated", "message": "Password updated"}


@router.post("/me/avatar", response_model=UserOut)
async def upload_avatar(request: Request, file: UploadFile = File(...), db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
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
    record_activity(db, cu, "Updated profile photo", request)
    return _out(cu)


@router.post("/me/request-email-verification")
async def request_email_verification(request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    if cu.email_verified:
        return {"status": "verified", "message": "Email is already verified"}
    _require_gmail(cu.email.lower())
    issue_email_otp(cu)
    record_activity(db, cu, "Requested email verification", request)
    return {
        "status": "requested",
        "message": "Verification code sent to your Gmail account.",
        "requested_at": cu.email_verification_requested_at.isoformat(),
    }


@router.post("/me/verify-email-otp", response_model=UserOut)
async def verify_email_otp(payload: EmailOtpVerify, request: Request, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
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
    record_activity(db, cu, "Verified email", request)
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
