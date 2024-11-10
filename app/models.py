import asyncpg
from datetime import datetime
import json
from typing import Optional
import uuid

# Define a global pool variable
pool = None

class Song:
    def __init__(self, id, name, created_at, status, details, image_url: Optional[str] = None, image_large_url: Optional[str] = None, video_url: Optional[str] = None, audio_url: Optional[str] = None, generation_uuid = None, listens = None):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.status = status
        self.listens = listens
        try:
            self.details = json.loads(details) if isinstance(details, str) else details
        except json.JSONDecodeError:
            self.details = {}

        self.image_url = image_url
        self.image_large_url = image_large_url
        self.video_url = video_url
        self.audio_url = audio_url
        self.generation_uuid = generation_uuid

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
        generation_uuid = kwargs.get("generation_uuid", str(uuid.uuid4()))

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO songs (name, created_at, status, details, image_url, image_large_url, video_url, audio_url, generation_uuid)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, name, created_at, status, details, image_url, image_large_url, video_url, audio_url, generation_uuid
                """,
                name, datetime.now(), status, json.dumps(details), image_url, image_large_url, video_url, audio_url, generation_uuid
            )
        return cls(*row)

    @classmethod
    async def get(cls, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM songs WHERE id = $1",
                int(song_id)
            )
        if row:
            return cls(*row)
        return None

    @classmethod
    async def get_songs_after(cls, song, limit=5):
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM (
                    SELECT DISTINCT ON (generation_uuid) *
                    FROM songs
                    WHERE created_at >= $1::timestamp
                    AND (
                        status = 'complete'
                        OR (created_at >= NOW() - INTERVAL '5 minutes' AND status != 'complete')
                    )
                    AND generation_uuid != $2
                    ORDER BY generation_uuid, created_at DESC
                ) AS subquery
                ORDER BY created_at ASC
                LIMIT $3
            """, song.created_at, song.generation_uuid, limit)
        return [cls(*row) for row in rows]
    @classmethod
    async def get_all(cls):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM songs ORDER BY created_at DESC")
        return [cls(*row) for row in rows]

    @classmethod
    async def last_complete(cls, offset):
        offset *= 2 #hack
        async with pool.acquire() as conn:
            # Fetch the Nth last completed song
            rows = await conn.fetch(
                """
                SELECT * FROM songs
                WHERE status = 'complete'
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                1, offset
            )
            
            if rows:
                # If we found a song at the offset, return it
                return cls(*rows[0])
            
            # If no completed songs are found at that offset, return the last one if any exist
            if offset > 0:
                rows = await conn.fetch(
                    """
                    SELECT * FROM songs
                    WHERE status = 'complete'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                if rows:
                    return cls(*rows[0])

        # No completed songs in the database; return a mock object
        return cls(
            id=None,
            name="No Completed Song",
            created_at=None,
            status="completed",
            details={"message": "Mock song - no completed songs available"},
            image_url=None,
            image_large_url=None,
            video_url=None,
            audio_url=None
        )

    async def update_name(self, name):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET name = $1 WHERE id = $2",
                name, self.id
            )
        self.status = name

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

    async def update_media_urls(self, image_url=None, image_large_url=None, video_url=None, audio_url=None):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET image_url = $1, image_large_url = $2, video_url = $3, audio_url = $4 WHERE id = $5",
                image_url, image_large_url, video_url, audio_url, self.id
            )
        self.image_url, self.image_large_url, self.video_url, self.audio_url = image_url, image_large_url, video_url, audio_url

    async def increment_listen_count(self):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET listens = listens + 1 WHERE id = $1",
                self.id
            )
        self.listens += 1

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
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS generation_uuid UUID;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS listens INTEGER DEFAULT 0;
            ALTER TABLE songs DROP COLUMN IF EXISTS tags;
        """)

async def get_db_pool(db_url):
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(db_url)
    return pool
