import asyncpg
from datetime import datetime
import json
from typing import Optional

# Define a global pool variable
pool = None

class Song:
    def __init__(self, id, name, created_at, status, details, image_url: Optional[str] = None, image_large_url: Optional[str] = None, video_url: Optional[str] = None, audio_url: Optional[str] = None):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.status = status
        self.details = details
        self.image_url = image_url
        self.image_large_url = image_large_url
        self.video_url = video_url
        self.audio_url = audio_url

    @classmethod
    async def create(cls, **kwargs):
        # Set default values for optional fields
        name = kwargs.get("name", "Unknown Title")
        status = kwargs.get("status", "new")
        details = kwargs.get("details", {})
        tags = kwargs.get("tags", [])

        image_url = kwargs.get("image_url")
        image_large_url = kwargs.get("image_large_url")
        video_url = kwargs.get("video_url")
        audio_url = kwargs.get("audio_url")

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO songs (name, created_at, status, details, image_url, image_large_url, video_url, audio_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, name, created_at, status, details, image_url, image_large_url, video_url, audio_url
                """,
                name, datetime.now(), status, json.dumps(details), image_url, image_large_url, video_url, audio_url
            )
        return cls(*row, image_url=row.get('image_url'), image_large_url=row.get('image_large_url'), video_url=row.get('video_url'), audio_url=row.get('audio_url'))

    @classmethod
    async def get(cls, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM songs WHERE id = $1",
                song_id
            )
        if row:
            return cls(*row)
        return None

    @classmethod
    async def get_all(cls):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM songs ORDER BY created_at DESC")
        return [cls(*row) for row in rows]

    async def update_status(self, new_status):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET status = $1 WHERE id = $2",
                new_status, self.id
            )
        self.status = new_status

    async def update_details(self, new_details):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET details = $1 WHERE id = $2",
                json.dumps(new_details), self.id
            )
        self.details = new_details

async def init_db(pool_instance):
    global pool
    pool = pool_instance
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                details JSONB
            );
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS image_url TEXT;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS image_large_url TEXT;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS video_url TEXT;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS audio_url TEXT;
        """)

async def get_db_pool(db_url):
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(db_url)
    return pool
