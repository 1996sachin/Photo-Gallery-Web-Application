from minio import Minio
import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photo-gallery")
MINIO_SECURE = os.getenv("MINIO_SECURE", "False") == "True"

client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_SECURE
)

try:
    print(f"Listing objects in bucket '{MINIO_BUCKET}':")
    objects = client.list_objects(MINIO_BUCKET, recursive=True)
    count = 0
    for obj in objects:
        print(f"  - Key: {obj.object_name}, Size: {obj.size} bytes")
        count += 1
    print(f"Total objects found: {count}")
except Exception as e:
    print(f"Error listing objects: {e}")
