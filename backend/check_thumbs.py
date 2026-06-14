import asyncio, os
from sqlalchemy import select
from models.database import AsyncSessionLocal, Media

async def check():
    async with AsyncSessionLocal() as s:
        r = await s.execute(select(Media.thumbnail_path, Media.file_path).limit(5))
        for t, f in r.all():
            print(f"Thumb: {t} | File: {f}")

if __name__ == '__main__':
    asyncio.run(check())
