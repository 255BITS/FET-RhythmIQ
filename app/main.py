from quart import Quart, render_template, jsonify, request
from models import Song, init_db, get_db_pool
import asyncio
import httpx
import os
import json
import uuid
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


app = Quart(__name__)

DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://rhythmiq:rhythmiq@localhost:5432/rhythmiq")
AGENT_HOST = os.getenv("AGENT_HOST", "http://localhost:8258")

@app.before_serving
async def setup():
    await init_db(await get_db_pool(DATABASE_URL))

@app.route('/')
async def home():
    current_song = await Song.last_complete(3)
    return await render_template('home.html', current_song=current_song)

# New route to get the current song details
@app.route('/current_song')
async def current_song_route():
    current_song = await Song.last_complete(3)
    return jsonify({
        'name': current_song.name,
        'status': current_song.status,
        'audio_url': current_song.audio_url
    })

@app.route('/create_song')
async def create_song():
    return await render_template('create_song.html')

@app.route('/generate_song', methods=['POST'])
async def generate_song():
    generation_uuid = str(uuid.uuid4())
    song1 = await Song.create(name="New Song 1", status="generating", generation_uuid=generation_uuid)
    song2 = await Song.create(name="New Song 2", status="generating", generation_uuid=generation_uuid)
    asyncio.create_task(generate_song_with_agent([song1, song2]))
    return jsonify([{"id": song1.id, "name": song1.name, "status": song1.status}, {"id": song2.id, "name": song2.name, "status": song2.status}])

@app.route('/queue')
async def update_queue():
    current_song_id = request.args.get("currentSongId")
    current_song = await Song.get(current_song_id)
    songs = await Song.get_songs_after(current_song)
    return await render_template('partials/queue.html', songs=songs, song=current_song)

@app.route('/stream_music')
async def stream_music():
    async def generate():
        while True:
            song = await Song.get_next_complete()
            if song:
                yield f"data: {json.dumps({'id': song.id, 'name': song.name})}\n\n"
            await asyncio.sleep(1)
    
    return app.response_class(generate(), mimetype='text/event-stream')

@app.route('/song/<id>/listen', methods=['POST'])
async def listen(id):
    song = await Song.get(id)
    if song:
        await song.increment_listen_count()
        songs_after = await Song.get_songs_after(song)
        print("Listen!", len(songs_after))
        if len(songs_after) < 3:
            generation_uuid = str(uuid.uuid4())
            song1 = await Song.create(name="New Song 1", status="generating", generation_uuid=generation_uuid)
            song2 = await Song.create(name="New Song 2", status="generating", generation_uuid=generation_uuid)
            asyncio.create_task(generate_song_with_agent([song1, song2]))
 
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Song not found"}), 404

# New route to generate song using the agent
async def generate_song_with_agent(songs):
    """
    Endpoint to generate songs by interacting with the /write_song and /sing endpoints.
    This process involves:
    1. Calling /write_song to generate lyrics.
    2. Passing the lyrics to /sing to generate media URLs for two songs.
    3. Creating two Song instances with the same lyrics but different media URLs.
    """

    try:
        async with httpx.AsyncClient() as client:
            # Step 1: Call /write_song to generate lyrics
            logging.debug("Calling /write_song endpoint to generate lyrics.")
            for song in songs:
                await song.update_status("writing lyrics")

            response_write_song = await client.post(f"{AGENT_HOST}/write_song", json={"instruction":""}, timeout=600)

            if response_write_song.status_code == 200:
                lyrics_result = response_write_song.json()
                logging.info(f"Lyrics generated: {lyrics_result}")
            else:
                for song in songs:
                    await song.update_status("error")
                error_msg = f"Error in /write_song: {response_write_song.status_code}"
                logging.error(error_msg)
                return jsonify({"error": error_msg}), response_write_song.status_code

            for song in songs:
                await song.update_status("singing")
                await song.update_details(lyrics_result)
                await song.update_name(lyrics_result["title"])
            # Step 2: Pass lyrics to /sing to generate media URLs for two songs
            logging.debug("Calling /sing endpoint with generated lyrics.")
            response_sing = await client.post("http://localhost:8000/sing", json=lyrics_result, timeout=600)

            if response_sing.status_code == 200:
                sing_results = response_sing.json()
                print(sing_results)
                # Expecting sing_results to be a list of two dictionaries
                logging.info("Media URLs received from /sing endpoint.")
            else:
                for song in songs:
                    await song.update_status("error singing")
                error_msg = f"Error in /sing: {response_sing.status_code} {response_sing.text}"
                logging.error(error_msg)
                return jsonify({"error": error_msg}), response_sing.status_code

            if not isinstance(sing_results, dict):
                error_msg = f"Invalid response format from /sing. Expected a dictionary with media URLs. got {sing_results}"
                logging.error(error_msg)
                for song in songs:
                    await song.update_status("error")
                return jsonify({"error": error_msg}), 500

            logging.info("Media URLs received from /sing endpoint.")

            # Extract media URLs for each song
            songs_created = []
            for idx, song in enumerate(songs, start=1):
                image_url = sing_results.get(f'image_url_{idx}')
                image_large_url = sing_results.get(f'image_large_url_{idx}')
                video_url = sing_results.get(f'video_url_{idx}')
                audio_url = sing_results.get(f'audio_url_{idx}')

                if not all([image_url, image_large_url, video_url, audio_url]):
                    error_msg = f"Missing media URLs for song {idx} in sing_results."
                    logging.error(error_msg)
                    await song.update_status("error")
                    continue

                await song.update_media_urls(
                    image_url=image_url,
                    image_large_url=image_large_url,
                    video_url=video_url,
                    audio_url=audio_url
                )
                # Final update status
                await song.update_status("complete")
                logging.info(f"Created Song ID: {song.id} with media URLs from /sing.")
                songs_created.append(song)

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
