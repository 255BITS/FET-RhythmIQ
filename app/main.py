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
    """
    Endpoint to generate songs by interacting with the /write_song and /sing endpoints.
    This process involves:
    1. Calling /write_song to generate lyrics.
    2. Passing the lyrics to /sing to generate media URLs for two songs.
    3. Creating two Song instances with the same lyrics but different media URLs.
    """
    logging.info("generate_song_with_agent endpoint called.")

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Call /write_song to generate lyrics
            logging.debug("Calling /write_song endpoint to generate lyrics.")
            response_write_song = await client.post("http://localhost:8000/write_song", json={})

            if response_write_song.status_code == 200:
                lyrics_result = response_write_song.json()
                lyrics = lyrics_result.get('lyrics', '')
                logging.info(f"Lyrics generated: {lyrics}")
            else:
                error_msg = f"Error in /write_song: {response_write_song.status_code}"
                logging.error(error_msg)
                return jsonify({"error": error_msg}), response_write_song.status_code

            # Step 2: Pass lyrics to /sing to generate media URLs for two songs
            logging.debug("Calling /sing endpoint with generated lyrics.")
            response_sing = await client.post("http://localhost:8000/sing", json={"lyrics": lyrics})

            if response_sing.status_code == 200:
                sing_results = response_sing.json()
                # Expecting sing_results to be a list of two dictionaries
                if not isinstance(sing_results, list) or len(sing_results) != 2:
                    error_msg = "Invalid response format from /sing. Expected a list of two song media data."
                    logging.error(error_msg)
                    return jsonify({"error": error_msg}), 500

                logging.info("Media URLs received from /sing endpoint.")
            else:
                error_msg = f"Error in /sing: {response_sing.status_code}"
                logging.error(error_msg)
                return jsonify({"error": error_msg}), response_sing.status_code

            # Step 3: Create two Song instances with the same lyrics but different media URLs
            songs_created = []
            for idx, sing_result in enumerate(sing_results, start=1):
                song = await Song.create(
                    name=f"Generated Song {idx}",
                    status="complete",
                    details={"lyrics": lyrics},
                    image_url=sing_result.get('image_url'),
                    image_large_url=sing_result.get('image_large_url'),
                    video_url=sing_result.get('video_url'),
                    audio_url=sing_result.get('audio_url')
                )
                songs_created.append(song)
                logging.info(f"Created Song ID: {song.id} with media URLs from /sing.")

            # Optionally, you can aggregate these songs or perform additional actions here

            return jsonify({
                "status": "success",
                "songs": [
                    {"id": song.id, "name": song.name, "status": song.status} for song in songs_created
                ]
            }), 200

    except Exception as e:
        logging.exception("Exception occurred during generate_song_with_agent processing.")
        return jsonify({"error": f"Exception: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8257)
