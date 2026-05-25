# Memories App v2

> A warm, full-stack photo and video memory vault for saving, organizing, editing, and sharing moments with the people who matter.

![React](https://img.shields.io/badge/React-18-61dafb?style=for-the-badge&logo=react&logoColor=111)
![Vite](https://img.shields.io/badge/Vite-5-646cff?style=for-the-badge&logo=vite&logoColor=fff)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=fff)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Async-336791?style=for-the-badge&logo=postgresql&logoColor=fff)
![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=fff)

## Overview

Memories App v2 is a private gallery experience built for families, friends, and loved ones. It lets users upload photos and videos, create albums, favorite important moments, tag people, leave comments, edit media, and keep profile/activity details in one cozy interface.

The project uses a React + Vite frontend and a FastAPI backend backed by PostgreSQL. Media processing is handled with Pillow and FFmpeg, while authentication uses JWT tokens with Gmail verification support.

## Highlights

- Photo and video uploads with drag-and-drop support
- Automatic thumbnail generation for images and videos
- EXIF-aware photo processing and auto-rotation
- Photo editor with filters, brightness, contrast, saturation, and rotation
- Video playback and trimming workflow
- Albums, favorites, people tagging, captions, and comments
- Search by title, caption, and original filename
- JWT authentication with 7-day tokens
- Gmail OTP verification and optional Google OAuth flow
- User profile management with avatar uploads and password changes
- User activity dashboard with online status and recent activity logs
- Warm golden visual design system for a personal memory-book feel

## Tech Stack

| Layer | Tools |
| --- | --- |
| Frontend | React 18, Vite, React Router, Zustand, Axios, Lucide React |
| Backend | FastAPI, SQLAlchemy async, Pydantic, Uvicorn |
| Database | PostgreSQL with asyncpg |
| Media | Pillow, FFmpeg, ffmpeg-python |
| Auth | JWT, bcrypt, Gmail OTP, Google OAuth-ready routes |
| Storage | Local upload folders, with an easy path to S3 via boto3 |

## Project Structure

```text
memories-v2/
├── backend/
│   ├── api/
│   │   ├── albums.py
│   │   ├── auth.py
│   │   ├── comments.py
│   │   ├── edits.py
│   │   ├── media.py
│   │   └── people.py
│   ├── migrations/
│   │   └── 001_init.sql
│   ├── models/
│   │   └── database.py
│   ├── services/
│   │   └── media_processor.py
│   ├── uploads/
│   ├── main.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── pages/
│   │   ├── stores/
│   │   ├── App.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- FFmpeg

Install FFmpeg:

```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg
```

### 1. Create the Database

```bash
psql -U postgres -c "CREATE DATABASE memoriesdb;"
psql -U postgres -d memoriesdb -f backend/migrations/001_init.sql
```

### 2. Start the Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/memoriesdb
SECRET_KEY=replace-with-a-long-random-secret
APP_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

Run the API:

```bash
uvicorn main:app --reload --port 8000
```

Backend URLs:

- API health: `http://localhost:8000/api/health`
- API docs: `http://localhost:8000/docs`

### 3. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the app at:

```text
http://localhost:5173
```

## Optional Email and Google Setup

Email verification and password reset require SMTP settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_TLS=true
```

Google OAuth routes are available when these values are configured:

```env
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
```

## Useful Commands

```bash
# Backend
cd backend
uvicorn main:app --reload --port 8000

# Frontend development
cd frontend
npm run dev

# Frontend production build
cd frontend
npm run build
```

## API Areas

| Area | Prefix | Purpose |
| --- | --- | --- |
| Auth | `/api/auth` | Register, login, profile, verification, avatars, activity |
| Media | `/api/media` | Upload, list, search, favorite, update, delete |
| Albums | `/api/albums` | Create and organize albums |
| Comments | `/api/comments` | Discuss photos and videos |
| People | `/api/people` | Tag and share with loved ones |
| Edits | `/api/edits` | Save photo/video edits and edit history |

## Production Notes

- Generate a strong secret with `python -c "import secrets; print(secrets.token_hex(32))"`.
- Serve the built frontend from `frontend/dist` or copy it into the backend `dist` directory.
- Run FastAPI with Gunicorn and Uvicorn workers for production.
- Put Nginx or another reverse proxy in front of the API.
- Move `uploads/` to durable storage such as S3 before hosting real user data.
- Keep `SECRET_KEY`, SMTP credentials, and OAuth credentials out of source control.

## Description

Memories App v2 is designed as a digital keepsake space: upload the media, enrich it with context, organize it into albums, and revisit it through a clean gallery built around photos, videos, people, and shared stories.
