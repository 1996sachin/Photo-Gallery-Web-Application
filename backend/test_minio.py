from minio import Minio
import os
from dotenv import load_dotenv

load_dotenv()

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "photo-gallery")

client = Minio(MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY, secret_key=MINIO_SECRET_KEY, secure=False)

try:
    if client.bucket_exists(MINIO_BUCKET):
        print(f"Bucket {MINIO_BUCKET} exists")
        objects = client.list_objects(MINIO_BUCKET, recursive=True)
        print("Objects:")
        for obj in objects:
            print(f"- {obj.object_name}")
    else:
        print(f"Bucket {MINIO_BUCKET} does not exist")
except Exception as e:
    print(f"Error: {e}")
