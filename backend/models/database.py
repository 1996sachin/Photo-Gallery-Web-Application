import uuid
from datetime import datetime
from sqlalchemy import (Column, String, Boolean, Integer, BigInteger, Float,
                        Text, DateTime, ForeignKey, Numeric, CheckConstraint, UniqueConstraint)
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, relationship
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/memoriesdb")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except:
            await session.rollback()
            raise

async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_requested_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_token TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verification_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_requested_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT 'client'"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_secret TEXT"))
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS mfa_enabled BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE albums ADD COLUMN IF NOT EXISTS share_password_hash TEXT"))
        await conn.execute(text("ALTER TABLE albums ADD COLUMN IF NOT EXISTS share_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS is_encrypted BOOLEAN DEFAULT FALSE"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS privacy VARCHAR(20) DEFAULT 'private'"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS share_token VARCHAR(64) UNIQUE"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS share_password_hash TEXT"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS share_expires_at TIMESTAMPTZ"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS malware_scan_status VARCHAR(20) DEFAULT 'pending'"))
        await conn.execute(text("ALTER TABLE media ADD COLUMN IF NOT EXISTS malware_scan_result TEXT"))
        await conn.run_sync(AccessGrant.__table__.create, checkfirst=True)
        admin_email = os.getenv("ADMIN_EMAIL")
        if admin_email:
            await conn.execute(
                text("UPDATE users SET role = 'admin' WHERE lower(email) = lower(:email)"),
                {"email": admin_email},
            )


class User(Base):
    __tablename__ = "users"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    display_name  = Column(String(100), nullable=False)
    role          = Column(String(20), CheckConstraint("role IN ('admin', 'business', 'client')"), default='client')
    avatar_url    = Column(Text)
    bio           = Column(Text)
    mfa_secret    = Column(Text)
    mfa_enabled   = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)
    email_verification_requested_at = Column(DateTime(timezone=True))
    email_verification_token = Column(Text)
    email_verification_expires_at = Column(DateTime(timezone=True))
    password_reset_token = Column(Text)
    password_reset_requested_at = Column(DateTime(timezone=True))
    password_reset_expires_at = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at    = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    albums        = relationship("Album", back_populates="owner", foreign_keys="Album.owner_id")
    media         = relationship("Media", back_populates="uploader")


class Album(Base):
    __tablename__ = "albums"
    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title          = Column(String(200), nullable=False)
    description    = Column(Text)
    cover_media_id = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="SET NULL"))
    is_shared      = Column(Boolean, default=False)
    share_token    = Column(String(64), unique=True)
    share_password_hash = Column(Text)
    share_expires_at = Column(DateTime(timezone=True))
    created_at     = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at     = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    owner          = relationship("User", back_populates="albums", foreign_keys=[owner_id])
    media          = relationship("Media", back_populates="album", foreign_keys="Media.album_id")


class Media(Base):
    __tablename__ = "media"
    __table_args__ = (CheckConstraint("media_type IN ('photo','video','document')", name="ck_media_type"),)
    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploader_id       = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    album_id          = Column(UUID(as_uuid=True), ForeignKey("albums.id", ondelete="SET NULL"))
    filename          = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path         = Column(Text, nullable=False)
    thumbnail_path    = Column(Text)
    is_encrypted      = Column(Boolean, default=False)
    media_type        = Column(String(10), nullable=False)
    mime_type         = Column(String(100), nullable=False)
    file_size_bytes   = Column(BigInteger, nullable=False)
    width             = Column(Integer)
    height            = Column(Integer)
    duration_seconds  = Column(Float)
    taken_at          = Column(DateTime(timezone=True))
    title             = Column(String(300))
    caption           = Column(Text)
    location_name     = Column(String(200))
    latitude          = Column(Numeric(10, 8))
    longitude         = Column(Numeric(11, 8))
    is_favorite       = Column(Boolean, default=False)
    privacy           = Column(String(20), CheckConstraint("privacy IN ('private','shared')"), default="private")
    share_token       = Column(String(64), unique=True)
    share_password_hash = Column(Text)
    share_expires_at  = Column(DateTime(timezone=True))
    malware_scan_status = Column(String(20), default="pending")
    malware_scan_result = Column(Text)
    view_count        = Column(Integer, default=0)
    media_metadata    = Column("metadata", JSONB, default={})
    created_at        = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at        = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    uploader  = relationship("User", back_populates="media")
    album     = relationship("Album", back_populates="media", foreign_keys=[album_id])
    comments  = relationship("Comment", back_populates="media", cascade="all, delete")
    reactions = relationship("Reaction", back_populates="media", cascade="all, delete")
    edits     = relationship("MediaEdit", back_populates="media", cascade="all, delete")


class Comment(Base):
    __tablename__ = "comments"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id   = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    author_id  = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    body       = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)
    media  = relationship("Media", back_populates="comments")
    author = relationship("User")


class Reaction(Base):
    __tablename__ = "reactions"
    __table_args__ = (UniqueConstraint("media_id", "user_id", "emoji"),)
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id   = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    emoji      = Column(String(10), nullable=False, default="❤️")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    media = relationship("Media", back_populates="reactions")
    user  = relationship("User")


class Person(Base):
    __tablename__ = "people"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name       = Column(String(100), nullable=False)
    avatar_url = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class MediaEdit(Base):
    __tablename__ = "media_edits"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id    = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"), nullable=False)
    editor_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    edit_type   = Column(String(50), nullable=False)
    edit_params = Column(JSONB, default={})
    result_path = Column(Text)
    created_at  = Column(DateTime(timezone=True), default=datetime.utcnow)
    media  = relationship("Media", back_populates="edits")
    editor = relationship("User")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action     = Column(String(100), nullable=False)
    details    = Column(JSONB, default={})
    ip_address = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    user = relationship("User")


class AccessGrant(Base):
    __tablename__ = "access_grants"
    __table_args__ = (
        UniqueConstraint("owner_id", "grantee_id", "album_id", "media_id", name="uq_access_grant_scope"),
        CheckConstraint("album_id IS NOT NULL OR media_id IS NOT NULL", name="ck_access_grant_target"),
    )
    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id   = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    grantee_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    album_id   = Column(UUID(as_uuid=True), ForeignKey("albums.id", ondelete="CASCADE"))
    media_id   = Column(UUID(as_uuid=True), ForeignKey("media.id", ondelete="CASCADE"))
    permission = Column(String(20), CheckConstraint("permission IN ('view','comment')"), default="view")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    owner = relationship("User", foreign_keys=[owner_id])
    grantee = relationship("User", foreign_keys=[grantee_id])
    album = relationship("Album")
    media = relationship("Media")
