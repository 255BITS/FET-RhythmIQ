import asyncpg
from datetime import datetime
import json
from typing import Optional
import uuid
from model_selector import get_model_nickname

# Define a global pool variable
pool = None

class Song:
    def __init__(
        self,
        id: Optional[int] = None,
        name: Optional[str] = None,
        created_at: Optional[datetime] = None,
        status: Optional[str] = None,
        details: Optional[dict] = None,
        image_url: Optional[str] = None,
        image_large_url: Optional[str] = None,
        video_url: Optional[str] = None,
        audio_url: Optional[str] = None,
        generation_uuid: Optional[str] = None,
        listens: Optional[int] = 0,
        favorite_count: Optional[int] = 0,
        model_name: Optional[str] = None,
        station: Optional[str] = None,

        **kwargs  # Catch-all for any extra fields in the DB
    ):
        # Known fields
        self.id = id
        self.name = name
        self.created_at = created_at
        self.status = status
        self.listens = listens
        self.favorite_count = favorite_count

        # Details can be JSON in the DB. Ensure it's a dict in Python.
        if isinstance(details, str):
            try:
                self.details = json.loads(details)
            except json.JSONDecodeError:
                self.details = {}
        else:
            self.details = details or {}

        self.image_url = image_url
        self.image_large_url = image_large_url
        self.video_url = video_url
        self.audio_url = audio_url
        self.generation_uuid = generation_uuid
        self.model_name = model_name
        self.model_nickname = get_model_nickname(model_name)[1] if model_name else None
        self.station = station

        # If you want to keep track of extra fields not explicitly handled:
        self._extra = kwargs  # Store them so they're not lost or cause an error

    @classmethod
    def from_db_record(cls, record):
        """
        Convert an asyncpg.Record into a dict and pass it to the constructor.
        """
        # Convert the record to a dict so ** unpacking works
        record_dict = dict(record)
        return cls(**record_dict)

    @classmethod
    async def get_all_favorites(cls):
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT s.*
                FROM songs s
                WHERE favorite_count > 0
                ORDER BY favorite_count DESC, created_at DESC
                """
            )
        # Use from_db_record for each row
        return [cls.from_db_record(row) for row in rows]

    @classmethod
    async def get_all_favorites_filtered(cls, delta):
        lower_bound = datetime.utcnow() - delta
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT DISTINCT s.*
                FROM songs s
                JOIN user_favorites uf ON s.id = uf.song_id
                WHERE uf.created_at >= $1
                ORDER BY s.favorite_count DESC, s.created_at DESC
                """,
                lower_bound
            )
        return [cls.from_db_record(row) for row in rows]

    @classmethod
    async def create(cls, **kwargs):
        # Provide default values for optional fields
        name = kwargs.get("name", "Unknown Title")
        status = kwargs.get("status", "new")
        details = kwargs.get("details", {})

        image_url = kwargs.get("image_url")
        image_large_url = kwargs.get("image_large_url")
        video_url = kwargs.get("video_url")
        audio_url = kwargs.get("audio_url")
        model_name = kwargs.get("model_name")
        station = kwargs.get("station")
        generation_uuid = kwargs.get("generation_uuid", str(uuid.uuid4()))

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO songs (
                    name, created_at, status, details, 
                    image_url, image_large_url, 
                    video_url, audio_url, generation_uuid, model_name, station
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                RETURNING *
                """,
                name,
                datetime.utcnow(),
                status,
                json.dumps(details),
                image_url,
                image_large_url,
                video_url,
                audio_url,
                generation_uuid,
                model_name,
                station
            )
        return cls.from_db_record(row)

    @classmethod
    async def get(cls, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM songs WHERE id = $1",
                int(song_id)
            )
        if row:
            return cls.from_db_record(row)
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
                        OR (created_at >= NOW() - INTERVAL '10 minutes' AND status != 'complete')
                    )
                    AND generation_uuid != $2
                ORDER BY generation_uuid, created_at DESC
                ) AS subquery
                ORDER BY created_at ASC
                LIMIT $3
            """, song.created_at, song.generation_uuid, limit)
        return [cls.from_db_record(row) for row in rows]

    @classmethod
    async def get_all(cls):
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM songs ORDER BY created_at DESC")
        return [cls.from_db_record(row) for row in rows]

    @classmethod
    async def last_complete(cls, offset, station=None):
        offset *= 2  # FIXME: Double offset for compatibility with pagination
        async with pool.acquire() as conn:
            # Build main query dynamically based on station parameter
            station_clause = "AND station = $3" if station else ""
            params = [1, offset]
            if station:
                params.append(station)
            query = f"""
                SELECT * FROM songs
                WHERE status = 'complete' {station_clause}
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
            """
            rows = await conn.fetch(query, *params)
            if rows:
                return cls.from_db_record(rows[0])

            if offset > 0:
                # Fallback query: get the last complete song
                station_clause = "AND station = $1" if station else ""
                params = [station] if station else []
                fallback_query = f"""
                    SELECT * FROM songs
                    WHERE status = 'complete' {station_clause}
                    ORDER BY created_at DESC
                    LIMIT 1
                """
                rows = await conn.fetch(fallback_query, *params)
                if rows:
                    return cls.from_db_record(rows[0])

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
        self.name = name

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
        self.image_url, self.image_large_url, self.video_url, self.audio_url = (
            image_url, image_large_url, video_url, audio_url
        )

    async def increment_listen_count(self):
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET listens = listens + 1 WHERE id = $1",
                self.id
            )
        self.listens += 1

    async def get_favorite_count(self):
        return await UserFavorite.get_favorite_count(self.id)

    async def update_favorite_count(self):
        favorite_count = await self.get_favorite_count()
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE songs SET favorite_count = $1 WHERE id = $2",
                favorite_count, self.id
            )
        self.favorite_count = favorite_count

class UserFavorite:
    def __init__(self, id, user_id, song_id, created_at):
        self.id = id
        self.user_id = user_id
        self.song_id = song_id
        self.created_at = created_at

    @classmethod
    async def create(cls, user_id, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_favorites (user_id, song_id, created_at)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, song_id, created_at
                """,
                user_id, song_id, datetime.utcnow()
            )
        return cls(*row)

    @classmethod
    async def get(cls, user_id, song_id):
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM user_favorites WHERE user_id = $1 AND song_id = $2",
                user_id, song_id
            )
        return cls(*row) if row else None

    @classmethod
    async def delete(cls, user_id, song_id):
        async with pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM user_favorites WHERE user_id = $1 AND song_id = $2",
                user_id, song_id
            )

    @classmethod
    async def get_or_create(cls, user_id, song_id):
        favorite = await cls.get(user_id, song_id)
        if favorite is None:
            favorite = await cls.create(user_id, song_id)
            return favorite, True
        return favorite, False

    @classmethod
    async def exists(cls, user_id, song_id):
        async with pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM user_favorites WHERE user_id = $1 AND song_id = $2)",
                user_id, song_id
            )
        return result

    @classmethod
    async def get_favorite_count(cls, song_id):
        async with pool.acquire() as conn:
            count = await conn.fetchval(
                "SELECT COUNT(*) FROM user_favorites WHERE song_id = $1",
                song_id
            )
        return count

async def get_db_pool(db_url):
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(db_url)
    return pool

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
            /* Removed redundant column additions:
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS album_id INTEGER DEFAULT NULL;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS station_id INTEGER DEFAULT NULL;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS playlist_id INTEGER DEFAULT NULL;
            */
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS model_name TEXT DEFAULT NULL;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS station TEXT DEFAULT NULL;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS generation_uuid UUID;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS listens INTEGER DEFAULT 0;
            ALTER TABLE songs DROP COLUMN IF EXISTS tags;
            ALTER TABLE songs DROP COLUMN IF EXISTS station_id;
            ALTER TABLE songs DROP COLUMN IF EXISTS album_id;
            ALTER TABLE songs DROP COLUMN IF EXISTS playlist_id;
            ALTER TABLE songs ADD COLUMN IF NOT EXISTS favorite_count INTEGER DEFAULT 0;

            CREATE TABLE IF NOT EXISTS user_favorites (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                song_id INTEGER NOT NULL,
                created_at TIMESTAMP NOT NULL,
                UNIQUE(user_id, song_id)
            );
        """)