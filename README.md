# Memories App v2 — Setup Guide
# Warm & Cozy · For All Loved Ones · Full Stack

## Quick Start

### 1. Database (PostgreSQL)
```bash
psql -U postgres -c "CREATE DATABASE memoriesdb;"
psql -U postgres -d memoriesdb -f backend/migrations/001_init.sql
```

### 2. Backend (Python 3.11+)
```bash
cd backend

# Install FFmpeg first:
# Ubuntu: sudo apt install ffmpeg
# macOS:  brew install ffmpeg

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Create .env
echo 'DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/memoriesdb' > .env
echo 'SECRET_KEY=your-random-secret-here' >> .env

uvicorn main:app --reload --port 8000
# API docs → http://localhost:8000/docs
```

### 3. Frontend (Node 18+)
```bash
cd frontend
npm install
npm run dev
# App → http://localhost:5173
```

---

## Features
| Feature | Status |
|---------|--------|
| Upload photos (JPG PNG WEBP HEIC GIF) | ✅ |
| Upload videos (MP4 MOV WEBM AVI) | ✅ |
| Auto thumbnail generation (Pillow + FFmpeg) | ✅ |
| EXIF metadata extraction + auto-rotation | ✅ |
| Full video player (ReactPlayer) | ✅ |
| Photo editor: 8 filters, brightness/contrast/saturation, rotation | ✅ |
| Video trim (FFmpeg) | ✅ |
| Edit history saved in database | ✅ |
| Albums with optional shareable links | ✅ |
| Favorites gallery | ✅ |
| People / loved ones tagging | ✅ |
| Comments on every photo & video | ✅ |
| Search (title, caption, filename) | ✅ |
| JWT authentication (7-day tokens) | ✅ |
| Warm & cozy golden design system | ✅ |

---

## Project Structure
```
memories-v2/
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css          ← Warm golden design system
│   │   ├── hooks/useAuth.js   ← Zustand auth + axios
│   │   ├── stores/mediaStore.js
│   │   ├── components/
│   │   │   ├── Layout.jsx     ← Dark sidebar + header
│   │   │   ├── MediaCard.jsx  ← Hover effects + fav
│   │   │   ├── UploadModal.jsx← Drag & drop + progress
│   │   │   └── PhotoEditor.jsx← 8 filters + adjustments
│   │   └── pages/
│   │       ├── LoginPage.jsx  ← Split-panel login
│   │       ├── GalleryPage.jsx
│   │       ├── AlbumsPage.jsx
│   │       ├── FavoritesPage.jsx
│   │       ├── PeoplePage.jsx
│   │       └── MediaViewPage.jsx ← Video player + comments
│   └── package.json
└── backend/
    ├── main.py
    ├── requirements.txt
    ├── api/
    │   ├── auth.py
    │   ├── media.py
    │   ├── albums.py
    │   ├── comments.py
    │   ├── people.py
    │   └── edits.py
    ├── models/database.py
    ├── services/media_processor.py
    └── migrations/001_init.sql
```

## Production Tips
- Swap `uploads/` for S3 (add boto3 in media_processor.py)
- Use a strong random SECRET_KEY: `python -c "import secrets; print(secrets.token_hex(32))"`
- Run with gunicorn: `gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker`
- Serve frontend via nginx and proxy `/api` to gunicorn
