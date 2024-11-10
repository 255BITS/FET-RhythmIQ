from quart import Quart, render_template, jsonify, request
from models import Song, init_db, get_db_pool
import asyncio
import httpx
import os
import json

app = Quart(__name__)

DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://rhythmiq:rhythmiq@localhost:5432/rhythmiq")

@app.before_serving
async def setup():
    await init_db(await get_db_pool(DATABASE_URL))

@app.route('/')
async def home():
    return await render_template('home.html')

@app.route('/create_song')
async def create_song():
    return await render_template('create_song.html')

@app.route('/generate_song', methods=['POST'])
async def generate_song():
    song = await Song.create(name="New Song", status="generating")
    asyncio.create_task(generate_song_task(song))
    return jsonify({"id": song.id, "name": song.name, "status": song.status})

async def generate_song_task(song):
    # Simulate AI song generation
    await asyncio.sleep(10)
    song.status = "complete"
    song.details = json.dumps({"duration": "3:30", "genre": "Pop"})
    song.tags = json.dumps(["upbeat", "electronic"])
    await song.save()

@app.route('/update_queue')
async def update_queue():
    songs = await Song.get_recent(limit=5)
    return await render_template('partials/queue.html', songs=songs)

@app.route('/stream_music')
async def stream_music():
    async def generate():
        while True:
            song = await Song.get_next_complete()
            if song:
                yield f"data: {json.dumps({'id': song.id, 'name': song.name})}\n\n"
            await asyncio.sleep(1)
    
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/api/skip_song', methods=['POST'])
async def skip_song():
    # Logic to skip to the next song
    return jsonify({"status": "success"})

# New route to generate song using the agent
@app.route('/generate_song_with_agent', methods=['POST'])
async def generate_song_with_agent():
    # Create a new song entry with status 'generating'
    song1 = await Song.create(name="New Song in progress", status="generating")
    song2 = await Song.create(name="New Song in progress", status="generating")
    # Start the song generation task
    asyncio.create_task(generate_song_with_agent_task([song1,song2]))
    # Return the song details
    return jsonify({"ids": [song1.id, song2.id]})

async def generate_song_with_agent_task([songs]):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post("http://localhost:8000/orchestrate", json={})
            if response.status_code == 200:
                result = response.json()
                for idx, song in enumerate(songs):
                    # Update song details with the result from the agent
                    song.status = "complete"
                    song.details = json.dumps(result[idx])
                    await song.save()
            else:
                for idx, song in enumerate(songs):
                    # Handle error
                    song.status = "error"
                    song.details = {"error": f"Error: {response.status_code}"}
                    await song.save()
        except Exception as e:
            for idx, song in enumerate(songs):
                song.status = "error"
                song.details = {"error": f"Exception: {str(e)}"}
                await song.save()

if __name__ == '__main__':
    app.run(debug=True, port=8257)
