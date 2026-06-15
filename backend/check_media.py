import asyncio
from sqlalchemy import select
from models.database import AsyncSessionLocal, Media

async def main():
    async with AsyncSessionLocal() as session:
        # Check media items
        media_result = await session.execute(select(Media))
        media_items = media_result.scalars().all()
        print("--- MEDIA ITEMS ---")
        for m in media_items:
            print(f"ID: {m.id}")
            print(f"  Title: {m.title}")
            print(f"  Original Name: {m.original_filename}")
            print(f"  File Path: {m.file_path}")
            print(f"  Thumbnail Path: {m.thumbnail_path}")
            print(f"  Album ID: {m.album_id}")
            print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
