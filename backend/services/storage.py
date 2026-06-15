from minio import Minio
from datetime import timedelta
import os
import uuid
import logging

logger = logging.getLogger(__name__)

# Minio Configuration
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photo-gallery")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False") == "True"

# Local Storage fallback
UPLOAD_DIR = os.path.join("uploads", "originals")
THUMB_DIR = os.path.join("uploads", "thumbnails")

# CDN Configuration
CDN_DOMAIN = os.getenv("CDN_DOMAIN") # e.g., memories.sachinsinghchaudhary.com.np
USE_CDN = os.getenv("USE_CDN", "False") == "True"

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)


def _storage_key(object_name: str) -> str:
    return object_name[len("uploads/"):] if object_name.startswith("uploads/") else object_name


def _local_path(object_name: str) -> str:
    return object_name if object_name.startswith("uploads/") else os.path.join("uploads", object_name)

def ensure_bucket():
    for d in [UPLOAD_DIR, THUMB_DIR, "uploads/edited", "uploads/avatars"]:
        os.makedirs(d, exist_ok=True)
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created bucket: {MINIO_BUCKET}")
        else:
            logger.info(f"Bucket {MINIO_BUCKET} already exists.")
    except Exception as e:
        logger.warning(f"Could not verify/create bucket {MINIO_BUCKET}: {e}")

def upload_file(local_path: str, object_name: str, content_type: str = None):
    # Always save locally first as a backup/fallback
    local_dest = _local_path(object_name)
    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
    if local_path != local_dest:
        import shutil
        shutil.copy2(local_path, local_dest)

    try:
        client.fput_object(MINIO_BUCKET, _storage_key(object_name), local_path, content_type=content_type)
        return object_name
    except Exception as e:
        logger.error(f"Error uploading file {local_path} to {object_name}: {e}")
        # We don't raise here if we want to allow local-only operation,
        # but the rest of the app might expect it to be in S3.
        # For now, let's keep it raising to be safe, or just return the object_name anyway.
        return object_name

def upload_fileobj(file_obj, object_name: str, length: int, content_type: str = None):
    local_dest = _local_path(object_name)
    os.makedirs(os.path.dirname(local_dest), exist_ok=True)
    with open(local_dest, "wb") as f:
        f.write(file_obj.read())
    file_obj.seek(0)

    try:
        client.put_object(MINIO_BUCKET, _storage_key(object_name), file_obj, length, content_type=content_type)
        return object_name
    except Exception as e:
        logger.error(f"Error uploading file object to {object_name}: {e}")
        return object_name

def download_file(object_name: str, local_path: str):
    local_src = _local_path(object_name)
    if os.path.exists(local_src):
        import shutil
        shutil.copy2(local_src, local_path)
        return

    try:
        client.fget_object(MINIO_BUCKET, _storage_key(object_name), local_path)
    except Exception as e:
        logger.error(f"Error downloading {object_name} to {local_path}: {e}")
        raise

def get_file_data(object_name: str):
    local_src = _local_path(object_name)
    if os.path.exists(local_src):
        with open(local_src, "rb") as f:
            return f.read()

    from minio.error import S3Error
    from fastapi import HTTPException

    try:
        response = client.get_object(MINIO_BUCKET, _storage_key(object_name))
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except S3Error as e:
        if e.code == "NoSuchKey":
            logger.warning(f"File not found in storage: {object_name}")
            raise HTTPException(status_code=404, detail="File not found in storage")
        logger.error(f"S3 error getting object {object_name} data: {e}")
        raise HTTPException(status_code=500, detail=f"Storage error: {e.message}")
    except Exception as e:
        logger.error(f"Error getting object {object_name} data: {e}")
        raise HTTPException(status_code=500, detail="Internal error reading file")

def get_presigned_url(object_name: str, expires_minutes: int = 60) -> str:
    try:
        url = client.presigned_get_object(MINIO_BUCKET, _storage_key(object_name), expires=timedelta(minutes=expires_minutes))
        if CDN_DOMAIN:
            from urllib.parse import urlparse, urlunparse
            p = urlparse(url)
            return urlunparse(p._replace(netloc=CDN_DOMAIN))
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {object_name}: {e}")
        return ""

def delete_file(object_name: str):
    local_src = _local_path(object_name)
    if os.path.exists(local_src):
        os.remove(local_src)
    try:
        client.remove_object(MINIO_BUCKET, _storage_key(object_name))
    except Exception as e:
        logger.error(f"Error deleting object {object_name}: {e}")

def generate_object_key(user_id: str, filename: str, prefix: str = "originals") -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique = uuid.uuid4().hex
    if ext:
        return f"{user_id}/{prefix}/{unique}.{ext}"
    return f"{user_id}/{prefix}/{unique}"
