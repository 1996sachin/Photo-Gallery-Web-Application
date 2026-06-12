"""
Media processor — Pillow + FFmpeg
"""
import asyncio, uuid, mimetypes, os, tempfile
from pathlib import Path
from typing import Optional
import ffmpeg
from PIL import Image, ExifTags, ImageEnhance, ImageOps
from sqlalchemy import update
from cryptography.fernet import Fernet
from models.database import AsyncSessionLocal, Media

THUMB_SIZE = (640, 640)
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None


def encrypt_file(data: bytes) -> bytes:
    if not cipher: return data
    return cipher.encrypt(data)


def decrypt_file(data: bytes) -> bytes:
    if not cipher: return data
    return cipher.decrypt(data)


def encrypt_path(file_path: str) -> bool:
    if not cipher:
        return False
    path = Path(file_path)
    data = path.read_bytes()
    path.write_bytes(cipher.encrypt(data))
    return True


def decrypt_path_to_temp(file_path: str, suffix: Optional[str] = None) -> str:
    path = Path(file_path)
    data = decrypt_file(path.read_bytes())
    with tempfile.NamedTemporaryFile(suffix=suffix or path.suffix, delete=False) as tmp:
        tmp.write(data)
        return tmp.name


# ── Async entrypoints ──────────────────────────────────────────────────────────

async def process_photo(media_id: str, file_path: str, thumb_dir: str):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _photo_sync, file_path, thumb_dir)
        result["is_encrypted"] = await loop.run_in_executor(None, encrypt_path, file_path)
        await _update(media_id, result)
    except Exception as e:
        print(f"[photo] {media_id}: {e}")


async def process_video(media_id: str, file_path: str, thumb_dir: str):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _video_sync, file_path, thumb_dir)
        if result.get("file_path"):
            result["is_encrypted"] = await loop.run_in_executor(None, encrypt_path, result["file_path"])
        await _update(media_id, result)
    except Exception as e:
        print(f"[video] {media_id}: {e}")


async def process_document(media_id: str, file_path: str, thumb_dir: str):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _document_sync, file_path, thumb_dir)
        result["is_encrypted"] = bool(cipher)
        await _update(media_id, result)
    except Exception as e:
        print(f"[document] {media_id}: {e}")


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
    playable_path = _make_playable_video(file_path)
    probe = ffmpeg.probe(playable_path)
    vs = next((s for s in probe["streams"] if s["codec_type"] == "video"), None)
    duration = float(probe["format"].get("duration", 0))
    w = int(vs.get("width", 0)) if vs else None
    h = int(vs.get("height", 0)) if vs else None

    seek = min(2.0, duration / 2) if duration > 0 else 0
    tname = f"thumb_{Path(playable_path).stem}.jpg"
    tpath = str(Path(thumb_dir) / tname)
    (ffmpeg.input(playable_path, ss=seek).output(tpath, vframes=1, vf=f"scale={THUMB_SIZE[0]}:-1").overwrite_output().run(quiet=True))

    return {
        "width": w, "height": h, "duration_seconds": duration,
        "thumbnail_path": tpath,
        "file_path": playable_path,
        "filename": Path(playable_path).name,
        "mime_type": "video/mp4",
        "media_metadata": {"codec": vs.get("codec_name") if vs else None, "duration": duration},
    }


def _make_playable_video(file_path: str) -> str:
    source = Path(file_path)
    output = source.with_name(f"playable_{source.stem}.mp4")
    try:
        probe = ffmpeg.probe(str(source))
        video = next((s for s in probe["streams"] if s["codec_type"] == "video"), {})
        audio = next((s for s in probe["streams"] if s["codec_type"] == "audio"), None)
        is_mp4 = source.suffix.lower() == ".mp4"
        is_h264 = video.get("codec_name") == "h264"
        if is_mp4 and is_h264:
            return str(source)
        stream = ffmpeg.input(str(source))
        kwargs = {"vcodec": "libx264", "movflags": "+faststart", "pix_fmt": "yuv420p"}
        if audio:
            kwargs["acodec"] = "aac"
            ffmpeg.output(stream.video, stream.audio, str(output), **kwargs).overwrite_output().run(quiet=True)
        else:
            ffmpeg.output(stream.video, str(output), **kwargs).overwrite_output().run(quiet=True)
        return str(output)
    except Exception as exc:
        print(f"[video-transcode] {file_path}: {exc}")
        return str(source)


# ── Sync document processing ───────────────────────────────────────────────────

def _document_sync(file_path: str, thumb_dir: str) -> dict:
    source = Path(file_path)
    mime_type = mimetypes.guess_type(file_path)[0] or ""
    tname = f"thumb_{source.stem}.jpg"
    tpath = Path(thumb_dir) / tname

    if mime_type == "application/pdf":
        try:
            # If it's a document, it might be encrypted. We need to decrypt it to a temp file for pdf2image.
            with open(file_path, "rb") as f:
                data = decrypt_file(f.read())
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            
            from pdf2image import convert_from_path
            pages = convert_from_path(tmp_path, first_page=1, last_page=1, size=THUMB_SIZE[0])
            Path(tmp_path).unlink(missing_ok=True)
            
            if pages:
                pages[0].save(str(tpath), "JPEG")
                return {"thumbnail_path": str(tpath)}
        except Exception as e:
            print(f"[pdf-thumb] {file_path}: {e}")

    # Fallback to generic icon (this would ideally be a static file, but we'll use a placeholder colored image)
    icon = Image.new("RGB", THUMB_SIZE, color=(120, 120, 130))
    icon.save(str(tpath), "JPEG")
    return {"thumbnail_path": str(tpath)}


# ── Edit operations ────────────────────────────────────────────────────────────

def apply_photo_edit(source: str, output: str, edit_type: str, params: dict) -> dict:
    img = Image.open(source).convert("RGB")
    img = ImageOps.exif_transpose(img)

    if edit_type == "composite":
        img = _apply_photo_composite(img, params)

    elif edit_type == "crop":
        if "aspect" in params:
            img = _center_crop_aspect(img, params["aspect"])
        else:
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
        for key, Enh in [("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast), ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)]:
            if key in params:
                img = Enh(img).enhance(float(params[key]))

    img.save(output, "JPEG", quality=92)
    return {"width": img.width, "height": img.height}


def _center_crop_aspect(img: Image.Image, aspect: str) -> Image.Image:
    ratios = {
        "1:1": 1,
        "4:5": 4 / 5,
        "3:2": 3 / 2,
        "4:3": 4 / 3,
        "16:9": 16 / 9,
        "9:16": 9 / 16,
    }
    target = ratios.get(aspect)
    if not target:
        return img
    w, h = img.size
    current = w / h
    if current > target:
        new_w = int(h * target)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / target)
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def _apply_named_filter(img: Image.Image, name: str) -> Image.Image:
    if name in ("bw", "grayscale"):
        return img.convert("L").convert("RGB")
    if name == "sepia":
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(i * 1.1)))
        g = g.point(lambda i: min(255, int(i * 0.9)))
        b = b.point(lambda i: min(255, int(i * 0.7)))
        return Image.merge("RGB", (r, g, b))
    if name == "warm":
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(i * 1.12)))
        b = b.point(lambda i: int(i * 0.88))
        return Image.merge("RGB", (r, g, b))
    if name == "cool":
        r, g, b = img.split()
        r = r.point(lambda i: int(i * 0.88))
        b = b.point(lambda i: min(255, int(i * 1.12)))
        return Image.merge("RGB", (r, g, b))
    if name == "fade":
        img = ImageEnhance.Contrast(img).enhance(0.82)
        img = ImageEnhance.Color(img).enhance(0.72)
        return ImageEnhance.Brightness(img).enhance(1.08)
    if name == "vivid":
        img = ImageEnhance.Color(img).enhance(1.7)
        return ImageEnhance.Contrast(img).enhance(1.1)
    if name == "golden":
        img = ImageEnhance.Color(img).enhance(1.4)
        r, g, b = img.split()
        r = r.point(lambda i: min(255, int(i * 1.08)))
        b = b.point(lambda i: int(i * 0.92))
        img = Image.merge("RGB", (r, g, b))
        return ImageEnhance.Brightness(img).enhance(1.04)
    return img


def _apply_photo_composite(img: Image.Image, params: dict) -> Image.Image:
    if params.get("crop_aspect") and params.get("crop_aspect") != "original":
        img = _center_crop_aspect(img, params["crop_aspect"])
    if params.get("flip_horizontal"):
        img = ImageOps.mirror(img)
    if params.get("flip_vertical"):
        img = ImageOps.flip(img)
    if params.get("rotation"):
        img = img.rotate(-float(params["rotation"]), expand=True)
    if params.get("filter") and params.get("filter") != "original":
        img = _apply_named_filter(img, params["filter"])
    for key, Enh in [("brightness", ImageEnhance.Brightness), ("contrast", ImageEnhance.Contrast), ("saturation", ImageEnhance.Color), ("sharpness", ImageEnhance.Sharpness)]:
        if key in params:
            img = Enh(img).enhance(float(params[key]))
    return img


def apply_video_trim(source: str, output: str, start: float, end: float) -> dict:
    duration = end - start
    (ffmpeg.input(source, ss=start, t=duration).output(output, codec="copy").overwrite_output().run(quiet=True))
    return {"duration_seconds": duration}


def apply_video_edit(source: str, output: str, params: dict) -> dict:
    probe = ffmpeg.probe(source)
    source_duration = float(probe["format"].get("duration", 0))
    start = max(0, float(params.get("start_seconds", 0) or 0))
    end = float(params.get("end_seconds", source_duration) or source_duration)
    if source_duration > 0:
        end = min(end, source_duration)
    if end <= start:
        raise ValueError("end must be greater than start")

    stream = ffmpeg.input(source, ss=start, t=end - start)
    video = stream.video
    audio = stream.audio

    brightness = float(params.get("brightness", 1))
    contrast = float(params.get("contrast", 1))
    saturation = float(params.get("saturation", 1))
    eq_brightness = max(-1, min(1, brightness - 1))
    filters = []
    if brightness != 1 or contrast != 1 or saturation != 1:
        filters.append(f"eq=brightness={eq_brightness}:contrast={contrast}:saturation={saturation}")
    filter_name = params.get("filter", "original")
    if filter_name == "bw":
        filters.append("hue=s=0")
    elif filter_name == "warm":
        filters.append("colorbalance=rs=.08:bs=-.06")
    elif filter_name == "cool":
        filters.append("colorbalance=rs=-.06:bs=.08")
    elif filter_name == "vivid":
        filters.append("eq=saturation=1.35:contrast=1.08")
    elif filter_name == "fade":
        filters.append("eq=saturation=.75:contrast=.85:brightness=.04")

    rotation = int(params.get("rotation", 0) or 0) % 360
    if rotation == 90:
        filters.append("transpose=1")
    elif rotation == 180:
        filters.append("transpose=1,transpose=1")
    elif rotation == 270:
        filters.append("transpose=2")
    if params.get("flip_horizontal"):
        filters.append("hflip")
    if params.get("flip_vertical"):
        filters.append("vflip")

    filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
    output_kwargs = {
        "vcodec": "libx264",
        "acodec": "aac",
        "movflags": "+faststart",
        "pix_fmt": "yuv420p",
        "vf": ",".join(filters),
    }
    try:
        ffmpeg.output(stream.video, stream.audio, output, **output_kwargs).overwrite_output().run(quiet=True)
    except ffmpeg.Error:
        ffmpeg.output(stream.video, output, **{k: v for k, v in output_kwargs.items() if k != "acodec"}).overwrite_output().run(quiet=True)

    return {"duration_seconds": end - start}


# ── DB update helper ───────────────────────────────────────────────────────────

async def _update(media_id: str, updates: dict):
    import uuid as _uuid
    async with AsyncSessionLocal() as session:
        await session.execute(update(Media).where(Media.id == _uuid.UUID(media_id)).values(**{k: v for k, v in updates.items() if v is not None}))
        await session.commit()
