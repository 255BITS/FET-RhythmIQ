import asyncpg
from datetime import datetime
import json

class Song:
    def __init__(self, id, name, created_at, status, details, tags):
        self.id = id
        self.name = name
        self.created_at = created_at
        self.status = status
        self.details = details
        self.tags = tags

    @classmethod
    async def create(cls, pool, name, status, details, tags):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO songs (name, created_at, status, details, tags)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, name, created_at, status, details, tags
                """,
                name, datetime.now(), status, json.dumps(details), json.dumps(tags)
            )
        return cls(*row)

    @classmethod
    async def get(cls, pool, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM songs WHERE id = $1",
                song_id
            )
        if row:
            return cls(*row)
        return None

    @classmethod
    async def get_all(cls, pool):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM songs ORDER BY created_at DESC")
        return [cls(*row) for row in rows]

    async def update_status(self, pool, new_status):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET status = $1 WHERE id = $2",
                new_status, self.id
            )
        self.status = new_status

    async def update_details(self, pool, new_details):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET details = $1 WHERE id = $2",
                json.dumps(new_details), self.id
            )
        self.details = new_details

    async def update_tags(self, pool, new_tags):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET tags = $1 WHERE id = $2",
                json.dumps(new_tags), self.id
            )
        self.tags = new_tags

async def init_db(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                status TEXT NOT NULL,
                details JSONB,
                tags JSONB
            )
        """)

async def get_db_pool(db_url):
    return await asyncpg.create_pool(db_url)