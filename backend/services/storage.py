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

# CDN Configuration
CDN_DOMAIN = os.getenv("CDN_DOMAIN") # e.g., memories.sachinsinghchaudhary.com.np
USE_CDN = os.getenv("USE_CDN", "False") == "True"

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

def ensure_bucket():
    try:
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)
            logger.info(f"Created bucket: {MINIO_BUCKET}")
        else:
            logger.info(f"Bucket {MINIO_BUCKET} already exists.")
    except Exception as e:
        # If bucket exists but we don't have permission to check, just warn and continue.
        # Uploads will still work if the bucket actually exists and our keys have write access.
        logger.warning(f"Could not verify/create bucket {MINIO_BUCKET}: {e}")

def upload_file(local_path: str, object_name: str, content_type: str = None):
    try:
        client.fput_object(MINIO_BUCKET, object_name, local_path, content_type=content_type)
        return object_name
    except Exception as e:
        logger.error(f"Error uploading file {local_path} to {object_name}: {e}")
        raise

def upload_fileobj(file_obj, object_name: str, length: int, content_type: str = None):
    try:
        client.put_object(MINIO_BUCKET, object_name, file_obj, length, content_type=content_type)
        return object_name
    except Exception as e:
        logger.error(f"Error uploading file object to {object_name}: {e}")
        raise

def download_file(object_name: str, local_path: str):
    try:
        client.fget_object(MINIO_BUCKET, object_name, local_path)
    except Exception as e:
        logger.error(f"Error downloading {object_name} to {local_path}: {e}")
        raise

def get_file_data(object_name: str):
    try:
        response = client.get_object(MINIO_BUCKET, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()
    except Exception as e:
        logger.error(f"Error getting object {object_name} data: {e}")
        raise

def get_presigned_url(object_name: str, expires_minutes: int = 60) -> str:
    try:
        url = client.presigned_get_object(MINIO_BUCKET, object_name, expires=timedelta(minutes=expires_minutes))
        if CDN_DOMAIN:
            from urllib.parse import urlparse, urlunparse
            p = urlparse(url)
            # Reconstruct URL with CDN domain
            return urlunparse(p._replace(netloc=CDN_DOMAIN))
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {object_name}: {e}")
        return ""

def delete_file(object_name: str):
    try:
        client.remove_object(MINIO_BUCKET, object_name)
    except Exception as e:
        logger.error(f"Error deleting object {object_name}: {e}")

def generate_object_key(user_id: str, filename: str, prefix: str = "originals") -> str:
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique = uuid.uuid4().hex
    if ext:
        return f"{user_id}/{prefix}/{unique}.{ext}"
    return f"{user_id}/{prefix}/{unique}"
