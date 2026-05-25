"""
Media processor — Pillow + FFmpeg
"""
import asyncio, uuid
from pathlib import Path
from typing import Optional
import ffmpeg
from PIL import Image, ExifTags, ImageEnhance, ImageOps
from sqlalchemy import update
from models.database import AsyncSessionLocal, Media

THUMB_SIZE = (640, 640)


# ── Async entrypoints ──────────────────────────────────────────────────────────

async def process_photo(media_id: str, file_path: str, thumb_dir: str):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _photo_sync, file_path, thumb_dir)
        await _update(media_id, result)
    except Exception as e:
        print(f"[photo] {media_id}: {e}")


async def process_video(media_id: str, file_path: str, thumb_dir: str):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _video_sync, file_path, thumb_dir)
        await _update(media_id, result)
    except Exception as e:
        print(f"[video] {media_id}: {e}")


# ── Sync photo processing ──────────────────────────────────────────────────────

def _photo_sync(file_path: str, thumb_dir: str) -> dict:
    img = Image.open(file_path)
    img = ImageOps.exif_transpose(img)   # auto-rotate from EXIF
    w, h = img.size

    # Thumbnail
    tname = f"thumb_{Path(file_path).stem}.jpg"
    tpath = str(Path(thumb_dir) / tname)
    t = img.copy(); t.thumbnail(THUMB_SIZE, Image.LANCZOS)
    t.convert("RGB").save(tpath, "JPEG", quality=85)

    # EXIF
    meta, taken_at = {}, None
    try:
        exif = img._getexif() or {}
        for tag, val in exif.items():
            name = ExifTags.TAGS.get(tag, str(tag))
            try: meta[name] = str(val)
            except: pass
        if "DateTime" in meta:
            from datetime import datetime
            taken_at = datetime.strptime(meta["DateTime"], "%Y:%m:%d %H:%M:%S")
    except: pass

    return {"width": w, "height": h, "thumbnail_path": tpath, "media_metadata": meta, "taken_at": taken_at}


# ── Sync video processing ──────────────────────────────────────────────────────

def _video_sync(file_path: str, thumb_dir: str) -> dict:
    probe = ffmpeg.probe(file_path)
    vs = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    duration = float(probe["format"].get("duration", 0))
    w = int(vs.get("width", 0)) if vs else None
    h = int(vs.get("height", 0)) if vs else None

    seek = min(2.0, duration / 2) if duration > 0 else 0
    tname = f"thumb_{Path(file_path).stem}.jpg"
    tpath = str(Path(thumb_dir) / tname)
    (ffmpeg.input(file_path, ss=seek).output(tpath, vframes=1, vf=f"scale={THUMB_SIZE[0]}:-1").overwrite_output().run(quiet=True))

    return {
        "width": w, "height": h, "duration_seconds": duration,
        "thumbnail_path": tpath,
        "media_metadata": {"codec": vs.get("codec_name") if vs else None, "duration": duration},
    }


# ── Edit operations ────────────────────────────────────────────────────────────

def apply_photo_edit(source: str, output: str, edit_type: str, params: dict) -> dict:
    img = Image.open(source).convert("RGB")
    img = ImageOps.exif_transpose(img)

    if edit_type == "crop":
        img = img.crop((params["x"], params["y"], params["x"] + params["width"], params["y"] + params["height"]))

    elif edit_type == "rotate":
        img = img.rotate(-params.get("degrees", 0), expand=True)

    elif edit_type == "flip":
        img = ImageOps.mirror(img) if params.get("direction") == "horizontal" else ImageOps.flip(img)

    elif edit_type == "filter":
        name = params.get("name", "")
        if name == "grayscale":
            img = img.convert("L").convert("RGB")
        elif name == "sepia":
            r, g, b = img.split()
            r = r.point(lambda i: min(255, int(i * 1.1)))
            g = g.point(lambda i: min(255, int(i * 0.9)))
            b = b.point(lambda i: min(255, int(i * 0.7)))
            img = Image.merge("RGB", (r, g, b))
        elif name == "warm":
            r, g, b = img.split()
            r = r.point(lambda i: min(255, int(i * 1.12)))
            b = b.point(lambda i: int(i * 0.88))
            img = Image.merge("RGB", (r, g, b))
        elif name == "cool":
            r, g, b = img.split()
            r = r.point(lambda i: int(i * 0.88))
            b = b.point(lambda i: min(255, int(i * 1.12)))
            img = Image.merge("RGB", (r, g, b))
        elif name == "fade":
            img = ImageEnhance.Contrast(img).enhance(0.82)
            img = ImageEnhance.Color(img).enhance(0.72)
            img = ImageEnhance.Brightness(img).enhance(1.08)
        elif name == "vivid":
            img = ImageEnhance.Color(img).enhance(1.7)
            img = ImageEnhance.Contrast(img).enhance(1.1)
        elif name == "golden":
            img = ImageEnhance.Color(img).enhance(1.4)
            r, g, b = img.split()
            r = r.point(lambda i: min(255, int(i * 1.08)))
            b = b.point(lambda i: int(i * 0.92))
            img = Image.merge("RGB", (r, g, b))
            img = ImageEnhance.Brightness(img).enhance(1.04)

    elif edit_type == "adjust":
        for key, Enh in [("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast), ("saturation", ImageEnhance.Color)]:
            if key in params:
                img = Enh(img).enhance(float(params[key]))

    img.save(output, "JPEG", quality=92)
    return {"width": img.width, "height": img.height}


def apply_video_trim(source: str, output: str, start: float, end: float) -> dict:
    duration = end - start
    (ffmpeg.input(source, ss=start, t=duration).output(output, codec="copy").overwrite_output().run(quiet=True))
    return {"duration_seconds": duration}


# ── DB update helper ───────────────────────────────────────────────────────────

async def _update(media_id: str, updates: dict):
    import uuid as _uuid
    async with AsyncSessionLocal() as session:
        await session.execute(update(Media).where(Media.id == _uuid.UUID(media_id)).values(**{k: v for k, v in updates.items() if v is not None}))
        await session.commit()
