import asyncio, os
from sqlalchemy import select, func
from models.database import AsyncSessionLocal, Media

async def check():
    async with AsyncSessionLocal() as s:
        total = await s.execute(select(func.count(Media.id)))
        total_count = total.scalar()
        
        null_thumbs = await s.execute(select(func.count(Media.id)).where(Media.thumbnail_path == None))
        null_count = null_thumbs.scalar()
        
        print(f"Total Media: {total_count}")
        print(f"Media without thumbnails: {null_count}")
        
        if null_count > 0:
            sample = await s.execute(select(Media.id, Media.media_type, Media.original_filename).where(Media.thumbnail_path == None).limit(5))
            print("Samples without thumbnails:")
            for mid, mtype, fname in sample.all():
                print(f"ID: {mid} | Type: {mtype} | Name: {fname}")

if __name__ == '__main__':
    asyncio.run(check())
