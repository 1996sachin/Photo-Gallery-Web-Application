import sqlite3
import os
import shutil
import uuid
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from models.database import Media, User

# We'll use a sync session for this script
DATABASE_URL = "postgresql://sachin:password@localhost:5432/memoriesdb"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

media_items = session.query(Media).all()
print(f"Found {len(media_items)} media items")

for m in media_items:
    # Try to map existing files to database entries if they are missing
    # The logs showed object_name: f20a6150-5fc3-4913-8908-71a6d081d69e/originals/f63ce04af0e945d5807f0f4f5cc2e7ec.jpeg
    # but we have 1a4d8620-d9ab-4d7c-a88e-e89f816b18f9.jpg in backend/uploads/originals/
    
    local_path = os.path.join("backend", "uploads", m.file_path)
    if not os.path.exists(local_path):
        print(f"File missing: {m.file_path}")
        # Let's see if we can find any file in originals that might match
        originals = os.listdir("backend/uploads/originals")
        if originals:
            # If there's only one or two, maybe it's one of them?
            # This is risky, but for a fix we can try to point it to SOMETHING if it's broken.
            # However, better to just let the user re-upload or fix the paths.
            pass

session.close()
