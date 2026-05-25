-- Memories App v2 - PostgreSQL Schema
-- psql -U postgres -d memoriesdb -f 001_init.sql

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  VARCHAR(100) NOT NULL,
    avatar_url    TEXT,
    bio           TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verification_requested_at TIMESTAMPTZ,
    email_verification_token TEXT,
    email_verification_expires_at TIMESTAMPTZ,
    password_reset_token TEXT,
    password_reset_requested_at TIMESTAMPTZ,
    password_reset_expires_at TIMESTAMPTZ,
    last_seen_at TIMESTAMPTZ,
    current_session_started_at TIMESTAMPTZ,
    total_online_seconds INTEGER DEFAULT 0,
    last_activity TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_activity_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity TEXT NOT NULL,
    path TEXT,
    user_agent TEXT,
    ip_address VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Albums
CREATE TABLE albums (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    cover_media_id UUID,
    is_shared     BOOLEAN DEFAULT FALSE,
    share_token   VARCHAR(64) UNIQUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Media (photos & videos)
CREATE TABLE media (
    id                UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    uploader_id       UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    album_id          UUID REFERENCES albums(id) ON DELETE SET NULL,
    filename          VARCHAR(500) NOT NULL,
    original_filename VARCHAR(500) NOT NULL,
    file_path         TEXT NOT NULL,
    thumbnail_path    TEXT,
    media_type        VARCHAR(10) NOT NULL CHECK (media_type IN ('photo','video')),
    mime_type         VARCHAR(100) NOT NULL,
    file_size_bytes   BIGINT NOT NULL,
    width             INTEGER,
    height            INTEGER,
    duration_seconds  FLOAT,
    taken_at          TIMESTAMPTZ,
    title             VARCHAR(300),
    caption           TEXT,
    location_name     VARCHAR(200),
    latitude          DECIMAL(10,8),
    longitude         DECIMAL(11,8),
    is_favorite       BOOLEAN DEFAULT FALSE,
    view_count        INTEGER DEFAULT 0,
    metadata          JSONB DEFAULT '{}',
    created_at        TIMESTAMPTZ DEFAULT NOW(),
    updated_at        TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE albums ADD CONSTRAINT fk_album_cover
    FOREIGN KEY (cover_media_id) REFERENCES media(id) ON DELETE SET NULL;

-- Tags
CREATE TABLE tags (
    id   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) UNIQUE NOT NULL
);
CREATE TABLE media_tags (
    media_id UUID REFERENCES media(id) ON DELETE CASCADE,
    tag_id   UUID REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (media_id, tag_id)
);

-- People
CREATE TABLE people (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    owner_id   UUID REFERENCES users(id) ON DELETE CASCADE,
    name       VARCHAR(100) NOT NULL,
    email      VARCHAR(255),
    access_level VARCHAR(10) DEFAULT 'view' CHECK (access_level IN ('view','edit')),
    invite_token VARCHAR(64) UNIQUE,
    invite_sent_at TIMESTAMPTZ,
    accepted_at TIMESTAMPTZ,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TABLE media_people (
    media_id  UUID REFERENCES media(id)  ON DELETE CASCADE,
    person_id UUID REFERENCES people(id) ON DELETE CASCADE,
    PRIMARY KEY (media_id, person_id)
);

-- Comments
CREATE TABLE comments (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    media_id   UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    author_id  UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    body       TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Reactions
CREATE TABLE reactions (
    id         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    media_id   UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    emoji      VARCHAR(10) NOT NULL DEFAULT '❤️',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (media_id, user_id, emoji)
);

-- Album members (sharing)
CREATE TABLE album_members (
    album_id  UUID REFERENCES albums(id) ON DELETE CASCADE,
    user_id   UUID REFERENCES users(id)  ON DELETE CASCADE,
    role      VARCHAR(20) DEFAULT 'viewer' CHECK (role IN ('viewer','contributor','admin')),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (album_id, user_id)
);

-- Edit history
CREATE TABLE media_edits (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    media_id    UUID NOT NULL REFERENCES media(id) ON DELETE CASCADE,
    editor_id   UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    edit_type   VARCHAR(50) NOT NULL,
    edit_params JSONB NOT NULL DEFAULT '{}',
    result_path TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_media_album      ON media(album_id);
CREATE INDEX idx_media_uploader   ON media(uploader_id);
CREATE INDEX idx_media_taken      ON media(taken_at DESC NULLS LAST);
CREATE INDEX idx_media_type       ON media(media_type);
CREATE INDEX idx_media_favorite   ON media(uploader_id, is_favorite) WHERE is_favorite;
CREATE INDEX idx_media_metadata   ON media USING GIN(metadata);
CREATE INDEX idx_comments_media   ON comments(media_id);
CREATE INDEX idx_reactions_media  ON reactions(media_id);
CREATE INDEX idx_albums_owner     ON albums(owner_id);
CREATE INDEX idx_albums_token     ON albums(share_token) WHERE share_token IS NOT NULL;
CREATE INDEX idx_people_owner     ON people(owner_id);
CREATE UNIQUE INDEX idx_people_owner_email ON people(owner_id, email) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX idx_people_invite_token ON people(invite_token) WHERE invite_token IS NOT NULL;
CREATE INDEX idx_user_activity_user_created ON user_activity_events(user_id, created_at DESC);
