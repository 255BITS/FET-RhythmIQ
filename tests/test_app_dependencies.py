"""Exercise the real Quart routes with database access replaced by a fixture."""

import asyncio
from pathlib import Path
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import main


async def check():
    client = main.app.test_client()
    for route in ["/login", "/signup"]:
        response = await client.get(route)
        assert response.status_code == 200, (route, response.status_code)
    song = main.Song(id=1, name="Offline song", status="complete",
                     audio_url="https://example.com/audio.mp3")
    with patch.object(main.Song, "last_complete", new=AsyncMock(return_value=song)):
        response = await client.get("/")
        assert response.status_code == 200, response.status_code
        assert b"Offline song" in await response.get_data()


if __name__ == "__main__":
    asyncio.run(check())
