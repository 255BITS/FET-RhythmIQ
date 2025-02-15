from quart import Quart, render_template, jsonify, request, session
from models import Song, UserFavorite, init_db, get_db_pool
import asyncio
import httpx
import os
import json
import uuid
import logging
from datetime import timedelta
import pg_simple_auth

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.getLogger("httpcore.http11").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


app = Quart(__name__)

DATABASE_URL=os.getenv("DATABASE_URL", "postgresql://rhythmiq:rhythmiq@localhost:5432/rhythmiq")
AGENT_HOST = os.getenv("AGENT_HOST", "http://localhost:8258")
APP_SECRET = os.getenv("APP_SECRET", "tempsecret123")

@app.before_serving
async def setup():
    pool = await get_db_pool(DATABASE_URL)
    await init_db(pool)

    auth_config = pg_simple_auth.AuthConfig(
        jwt_expiration=3600 * 24 * 30,  # 1 month
        max_login_attempts=10,
        lockout_duration=300,
        password_min_length=6,
        password_require_uppercase=False,
        password_require_lowercase=False,
        password_require_digit=False,
        password_require_special=False,
    )
    await pg_simple_auth.initialize(
        pool=pool,
        key=APP_SECRET,
        table="public.user",
        auth_config=auth_config
    )

@app.before_request
async def before_request():
    if 'temp_user_id' not in session:
        session['temp_user_id'] = str(uuid.uuid4())

@app.route('/')
async def home():
    user_id = session['temp_user_id']
    current_song = await Song.last_complete(5)
    is_favorite = await UserFavorite.exists(user_id=user_id, song_id=current_song.id)
    return await render_template('home.html', current_song=current_song, is_favorite=is_favorite)

@app.route('/favorites')
async def favorites():
    """
    List all songs favorited by users.
    """
    filter_param = request.args.get("filter", "all_time")
    if filter_param == "last_week":
        delta = timedelta(days=7)
        favorites = await Song.get_all_favorites_filtered(delta)
    elif filter_param == "last_month":
        delta = timedelta(days=30)
        favorites = await Song.get_all_favorites_filtered(delta)
    elif filter_param == "last_3_months":
        delta = timedelta(days=90)
        favorites = await Song.get_all_favorites_filtered(delta)
    elif filter_param == "last_year":
        delta = timedelta(days=365)
        favorites = await Song.get_all_favorites_filtered(delta)
    else:
        favorites = await Song.get_all_favorites()

    print("favorites", favorites)

    current_song = favorites[0] if favorites else None
    return await render_template('favorites.html', favorites=favorites, current_song=current_song, filter=filter_param)

@app.route('/create_song')
async def create_song():
    return await render_template('create_song.html')

@app.route('/queue')
async def update_queue():
    current_song_id = request.args.get("currentSongId")
    current_song = await Song.get(current_song_id)
    songs = await Song.get_songs_after(current_song, limit=10)
    generating_songs = [s for s in songs if s.status not in ('complete', 'error', 'error singing')]

    if len(songs) < 6 and len(generating_songs) == 0:
        # Prevent duplicate generation if already processing
        generation_uuid = str(uuid.uuid4())
        song1 = await Song.create(name="New Song 1", status="generating", generation_uuid=generation_uuid)
        song2 = await Song.create(name="New Song 2", status="generating", generation_uuid=generation_uuid)
        asyncio.create_task(generate_song_with_agent([song1, song2]))
    return await render_template('partials/queue.html', songs=songs, song=current_song, number_generating=len(generating_songs))

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
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Song not found"}), 404

@app.route('/song/<int:id>/favorite', methods=['POST'])
async def favorite_song(id):
    if 'token' not in session:
        return jsonify({
            "error": "You must be logged in to favorite a song",
            "modal": true
        }), 401
    user_id = session['token']
    song = await Song.get(id)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    favorite, created = await UserFavorite.get_or_create(user_id=user_id, song_id=id)
    await song.update_favorite_count()

    return jsonify({
        "is_favorite": True,
        "favorite_count": await song.get_favorite_count()
    })

@app.route('/song/<int:id>/unfavorite', methods=['POST'])
async def unfavorite_song(id):
    if 'token' not in session:
        return jsonify({
            "error": "You must be logged in to unfavorite a song",
            "modal": true
        }), 401
    user_id = session['token']
    song = await Song.get(id)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    await UserFavorite.delete(user_id=user_id, song_id=id)
    await song.update_favorite_count()

    return jsonify({
        "is_favorite": False,
        "favorite_count": await song.get_favorite_count()
    })

@app.route('/song/<int:id>/favorite_count', methods=['GET'])
async def get_favorite_count(id):
    user_id = session['temp_user_id']
    song = await Song.get(id)
    if not song:
        return jsonify({"error": "Song not found"}), 404

    is_favorite = await UserFavorite.exists(user_id=user_id, song_id=id)
    favorite_count = await song.get_favorite_count()

    return jsonify({
        "is_favorite": is_favorite,
        "favorite_count": (favorite_count or 0)
    })

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

            response_write_song = await client.post(f"{AGENT_HOST}/write_song", json={"instruction":""}, timeout=1000)

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
            response_sing = await client.post(f"{AGENT_HOST}/sing", json=lyrics_result, timeout=1000)

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

def js_escape(value):
    """Escape characters that would interfere with JavaScript strings."""
    return (
        value.replace('\\', '\\\\')  # Escape backslashes
             .replace("'", "\\'")     # Escape single quotes
             .replace('"', '\\"')     # Escape double quotes
             .replace("\n", ' ')     # Escape double quotes
    )

app.jinja_env.filters['jsescape'] = js_escape
app.secret_key = APP_SECRET

from auth_routes import auth_bp
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    app.run(debug=True, port=8257)