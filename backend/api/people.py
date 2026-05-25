import uuid
import secrets
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from models.database import get_db, Person, User
from api.auth import (
    FRONTEND_URL,
    SMTP_FROM,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_TLS,
    SMTP_USERNAME,
    get_verified_user as get_current_user,
    _mask_email,
)

router = APIRouter()

class PersonIn(BaseModel):
    name: str
    email: str
    access_level: str = "view"


class PersonAccessUpdate(BaseModel):
    access_level: str


class PersonInviteUpdate(BaseModel):
    email: Optional[str] = None


def _normalize_gmail(email: str) -> str:
    email = email.strip().lower()
    if not email.endswith("@gmail.com"):
        raise HTTPException(400, "Use a Gmail address for people invites")
    return email


def _normalize_access(access_level: str) -> str:
    access_level = access_level.strip().lower()
    if access_level not in {"view", "edit"}:
        raise HTTPException(400, "Access must be view or edit")
    return access_level


async def _ensure_unique_email(db: AsyncSession, owner_id, email: str, person_id=None):
    query = select(Person).where(Person.owner_id == owner_id, Person.email == email)
    if person_id is not None:
        query = query.where(Person.id != person_id)
    r = await db.execute(query)
    if r.scalar_one_or_none():
        raise HTTPException(400, "This Gmail address is already added")


def _person_out(p: Person):
    return {
        "id": str(p.id),
        "name": p.name,
        "email": p.email,
        "access_level": p.access_level or "view",
        "avatar_url": p.avatar_url,
        "invite_sent_at": p.invite_sent_at.isoformat() if p.invite_sent_at else None,
        "accepted_at": p.accepted_at.isoformat() if p.accepted_at else None,
    }


def _send_people_invite(owner: User, person: Person):
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        raise HTTPException(500, "SMTP is not configured")

    invite_url = f"{FRONTEND_URL}/people?invite={person.invite_token}"
    masked_email = _mask_email(person.email)
    access_level = person.access_level or "view"
    msg = EmailMessage()
    msg["Subject"] = f"{owner.display_name} shared Memories with you"
    msg["From"] = SMTP_FROM
    msg["To"] = "Undisclosed recipients:;"
    msg.set_content(
        f"{owner.display_name} invited you to Memories with {access_level} access.\n\n"
        f"This invite was sent for {masked_email}.\n\n"
        f"Open this link with your Gmail account:\n{invite_url}\n\n"
        "View access lets you see shared memories. Edit access lets you help update them."
    )
    msg.add_alternative(
        f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:0;background:#f5f6f7;font-family:Arial,Helvetica,sans-serif;color:#1c1e21;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f5f6f7;padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border:1px solid #dddfe2;border-radius:8px;">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid #e4e6eb;font-size:20px;font-weight:700;color:#1877f2;">
                Memories
              </td>
            </tr>
            <tr>
              <td style="padding:24px;">
                <div style="font-size:18px;font-weight:600;margin-bottom:12px;">Memories invite</div>
                <div style="font-size:15px;line-height:22px;margin-bottom:18px;">
                  <strong>{owner.display_name}</strong> invited you to Memories with <strong>{access_level}</strong> access.
                  This invite was sent for <strong>{masked_email}</strong>.
                </div>
                <a href="{invite_url}" style="display:inline-block;background:#1877f2;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;padding:12px 18px;border-radius:6px;">
                  Open Memories
                </a>
                <div style="font-size:13px;line-height:20px;color:#65676b;margin-top:18px;">
                  View access lets you see shared memories. Edit access lets you help update them.
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
        server.send_message(msg, to_addrs=[person.email])

@router.post("/")
async def create(p: PersonIn, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    email = _normalize_gmail(str(p.email))
    access_level = _normalize_access(p.access_level)
    name = p.name.strip()[:100]
    if not name:
        raise HTTPException(400, "Name is required")

    await _ensure_unique_email(db, cu.id, email)

    person = Person(
        owner_id=cu.id,
        name=name,
        email=email,
        access_level=access_level,
        invite_token=secrets.token_urlsafe(32),
        invite_sent_at=datetime.utcnow(),
    )
    db.add(person); await db.flush()
    _send_people_invite(cu, person)
    return _person_out(person)

@router.get("/")
async def list_people(db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Person).where(Person.owner_id == cu.id).order_by(Person.name))
    return [_person_out(p) for p in r.scalars().all()]


@router.patch("/{person_id}/access")
async def update_access(person_id: str, payload: PersonAccessUpdate, db: AsyncSession = Depends(get_db), cu: User = Depends(get_current_user)):
    r = await db.execute(select(Person).where(Person.id == uuid.UUID(person_id), Person.owner_id == cu.id))
    person = r.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    person.access_level = _normalize_access(payload.access_level)
    return _person_out(person)


@router.post("/{person_id}/resend")
async def resend_invite(
    person_id: str,
    payload: Optional[PersonInviteUpdate] = None,
    db: AsyncSession = Depends(get_db),
    cu: User = Depends(get_current_user),
):
    r = await db.execute(select(Person).where(Person.id == uuid.UUID(person_id), Person.owner_id == cu.id))
    person = r.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Person not found")
    if payload and payload.email is not None:
        email = _normalize_gmail(payload.email)
        await _ensure_unique_email(db, cu.id, email, person.id)
        person.email = email
    if not person.email:
        raise HTTPException(400, "This person does not have a Gmail address")
    email = _normalize_gmail(person.email)
    if email != person.email:
        await _ensure_unique_email(db, cu.id, email, person.id)
        person.email = email
    person.invite_token = secrets.token_urlsafe(32)
    person.invite_sent_at = datetime.utcnow()
    _send_people_invite(cu, person)
    return _person_out(person)


@router.get("/invite/{token}", response_class=HTMLResponse)
async def invite_landing(token: str, db: AsyncSession = Depends(get_db)):
    r = await db.execute(select(Person).where(Person.invite_token == token))
    person = r.scalar_one_or_none()
    if not person:
        raise HTTPException(404, "Invite not found")
    return HTMLResponse(
        "<html><body>"
        "<h1>Memories invite</h1>"
        f"<p>You were invited as {person.email} with {person.access_level or 'view'} access.</p>"
        f"<p><a href='{FRONTEND_URL}/login'>Open Memories</a> and sign in with this Gmail address.</p>"
        "</body></html>"
    )
