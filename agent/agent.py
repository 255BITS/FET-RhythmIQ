from uagents import Agent, Bureau, Context, Model, Protocol
from singer import generate_song
from dotenv import load_dotenv
import os
import json
import time
import requests
import sentry_sdk
ENV = os.getenv("ENV", "dev")

if ENV == "production":
    sentry_sdk.init("https://d65669d0e41742c1a5a1c2c026732860@errors.255labs.xyz/3")

load_dotenv()

lyricist_seed = os.getenv("FET_LYRICIST_SEED", "RhythmIQ Lyricist seed phrase")
mailbox_key = os.getenv("FET_LYRICIST_MAILBOX", "RhythmIQ Lyricist mail")
# Create a single agent - RhythmIQ Lyricist
lyricist = Agent(name="RhythmIQ Lyricist", seed=lyricist_seed)#, mailbox=f"{mailbox_key}@https://agentverse.ai")

fox_api_key = os.getenv("FOX_API_KEY")
singer_seed = os.getenv("FET_SINGER_SEED", "RhythmIQ Singer seed phrase")
singer = Agent(name="RhythmIQ Singer", seed=singer_seed)

class EmptyRequest(Model):
    pass

class Request(Model):
    text: str

class Response(Model):
    timestamp: int
    text: str
    agent_address: str

# Define the models
class WriteSongRequest(Model):
    instruction: str
    artist_name: str
    model_name: str
    station: str

class WriteSongResponse(Model):
    title: str
    lyrics: str
    style: str
    negative_style: str

GenerateAudioRequest = WriteSongResponse

class GenerateAudioResponse(Model):
    status: str
    error: str
    audio_url_1: str
    image_url_1: str
    video_url_1: str
    image_large_url_1: str
    audio_url_2: str
    image_url_2: str
    video_url_2: str
    image_large_url_2: str

# Define protocol
proto = Protocol(name="SongwriterProtocol", version="1.0")

@proto.on_message(model=WriteSongRequest, replies=WriteSongResponse)
async def handle_song_request(ctx: Context, sender: str, msg: WriteSongRequest):
    # Use prompt.py's generate_song function
    instruction = msg.instruction
    model_name = msg.model_name
    artist = msg.artist_name
    station = msg.station
    song_data = generate_song(instruction, model_name, artist, station)

    if song_data:
        response = WriteSongResponse(
            title=song_data.get('title', ''),
            lyrics=song_data.get('lyrics', ''),
            style=song_data.get('style', ''),
            negative_style=song_data.get('negative_style', '')
        )
        await ctx.send(sender, response)
    else:
        ctx.logger.error("Failed to generate song.")


# Include protocol in the lyricist agent
lyricist.include(proto)


@lyricist.on_rest_post("/write_song", WriteSongRequest, WriteSongResponse)
async def handle_post(ctx: Context, req: WriteSongRequest) -> WriteSongResponse:
    ctx.logger.info("Writing song")
    instruction = req.instruction
    model_name = req.model_name
    artist = req.artist_name
    station = req.station
    song_data = generate_song(instruction, model_name, artist, station)
    return WriteSongResponse(
        title=song_data.get('title', ''),
        lyrics=song_data.get('lyrics', ''),
        style=song_data.get('style', ''),
        negative_style=song_data.get('negative_style', '')
    )

# Define protocol for Singer agent
audio_proto = Protocol(name="AudioGenerationProtocol", version="1.0")

# Function to generate audio using the API
def generate_audio(title, lyrics, style, negative_style):

    headers = {
        'Content-Type': 'application/json',
        'api-key': fox_api_key
    }
    data = {
        'title': title,
        'tags': style,
        'generation_type': 'TEXT',
        'prompt': lyrics,
        'negative_tags': negative_style,
        'mv': 'chirp-v4'
    }
    response = requests.post('https://api.sunoaiapi.com/api/v1/gateway/generate/music', json=data, headers=headers)
    print("response", response.status_code, response.text)
    if response.status_code == 200:
        resp_data = response.json()
        if resp_data['code'] == 0:
            song_ids = [item['song_id'] for item in resp_data['data']]
            return song_ids
    return None

def poll_for_audio(song_ids):
    headers = {
        'Content-Type': 'application/json',
        'api-key': fox_api_key  # Make sure fox_api_key is defined elsewhere
    }
    params = {
        'ids': ','.join(song_ids)
    }
    
    max_attempts = 3   # Number of times to try
    delay_seconds = 1  # Delay in seconds between attempts

    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get('https://api.sunoaiapi.com/api/v1/gateway/query',
                                    params=params, headers=headers)
            #print(f"Polling attempt {attempt}, response: {response.status_code}")
            response_data = response.json()
            #print(json.dumps(response_data, indent=2))
            
            if response.status_code == 200:
                return response_data
            else:
                print(f"Attempt {attempt} failed with status code {response.status_code}.")
        except Exception as e:
            print(f"Attempt {attempt} encountered an exception: {e}")
        
        # Only sleep if there are more attempts to try
        if attempt < max_attempts:
            print(f"Waiting for {delay_seconds} seconds before retrying...")
            time.sleep(delay_seconds)

    print("All attempts failed. Returning None.")
    return None

# Function to wait until all songs are complete
def poll_until_complete(song_ids):
    while True:
        print("Polling for song status...")
        time.sleep(5)  # Wait before polling again
        resp_data = poll_for_audio(song_ids)
        if resp_data:
            statuses = [item['status'] for item in resp_data]
            print(f"Current statuses: {statuses}")
            if all(status == 'complete' for status in statuses):
                print("All songs completed.")
                return resp_data
            elif any(status == 'error' for status in statuses):
                errors = [item for item in resp_data if item['status'] == 'error']
                error_messages = [item['meta_data'].get('error_message', 'Unknown error') for item in errors]
                raise Exception(f"Generation error(s): {error_messages}")
            else:
                continue
        else:
            raise Exception("Failed to poll for audio.")

@singer.on_rest_post("/sing", GenerateAudioRequest, GenerateAudioResponse)
async def handle_sing_post(ctx: Context, req: GenerateAudioRequest) -> GenerateAudioResponse:
    ctx.logger.info(f"Received /sing POST request with data: {req}")
    # Use the song data from the request
    song_data = {
        'title': req.title,
        'lyrics': req.lyrics,
        'style': req.style,
        'negative_style': req.negative_style
    }
    # Generate the audio response
    return await generate_audio_response(ctx, song_data)

@audio_proto.on_message(model=GenerateAudioRequest, replies=GenerateAudioResponse)
async def handle_generate_audio(ctx: Context, sender: str, msg: GenerateAudioRequest):
    ctx.logger.info(f"Received audio generation request with data: {msg}")
    # Use the song data from the message
    song_data = {
        'title': msg.title,
        'lyrics': msg.lyrics,
        'style': msg.style,
        'negative_style': msg.negative_style
    }

    # Generate the audio response
    response = await generate_audio_response(ctx, song_data)

    # Send the response back to the sender
    await ctx.send(sender, response)

async def generate_audio_response(ctx: Context, song_data: dict) -> GenerateAudioResponse:
    song_ids = generate_audio(
        title=song_data.get('title', ''),
        lyrics=song_data.get('lyrics', ''),
        style=song_data.get('style', ''),
        negative_style=song_data.get('negative_style', '')
    )
    if song_ids:
        ctx.logger.info(f"Song IDs received: {song_ids}")
        try:
            song_data_list = poll_until_complete(song_ids)
            # Extract required information
            audio_url_1 = song_data_list[0].get('audio_url')
            image_url_1 = song_data_list[0].get('image_url')
            video_url_1 = song_data_list[0].get('video_url')
            image_large_url_1 = song_data_list[0].get('image_large_url')
            audio_url_2 = song_data_list[1].get('audio_url')
            image_url_2 = song_data_list[1].get('image_url')
            video_url_2 = song_data_list[1].get('video_url')
            image_large_url_2 = song_data_list[1].get('image_large_url')
            return GenerateAudioResponse(
                status="complete",
                error="",
                audio_url_1=audio_url_1,
                image_url_1=image_url_1,
                video_url_1=video_url_1,
                image_large_url_1=image_large_url_1,
                audio_url_2=audio_url_2,
                image_url_2=image_url_2,
                video_url_2=video_url_2,
                image_large_url_2=image_large_url_2
            )
        except Exception as e:
            ctx.logger.error(f"Error during polling: {e}")
            return GenerateAudioResponse(
                status="error",
                error=f"Error during polling: {e}",
                audio_url_1="",
                image_url_1="",
                video_url_1="",
                image_large_url_1="",
                audio_url_2="",
                image_url_2="",
                video_url_2="",
                image_large_url_2=""
            )
    else:
        ctx.logger.error("Failed to initiate audio generation.")
        return GenerateAudioResponse(
            status="error",
            error="Failed to intiate audio generation.",
            audio_url_1="",
            image_url_1="",
            video_url_1="",
            image_large_url_1="",
            audio_url_2="",
            image_url_2="",
            video_url_2="",
            image_large_url_2=""
        )

@singer.on_rest_get("/", Response)
async def handle_heartbeat(ctx: Context) -> Response:
   return Response(
                text="OK",
                agent_address=ctx.agent.address,
                timestamp=int(time.time()),
   )

# Combined endpoint that takes no arguments, runs lyricist and singer in sequence
@singer.on_rest_post("/orchestrate", EmptyRequest, GenerateAudioResponse)
async def handle_orchestrate_post(ctx: Context, req: EmptyRequest) -> GenerateAudioResponse:
    ctx.logger.info("Received orchestrate request")

    # Step 1: Generate lyrics using the lyricist
    # We'll call generate_song without any arguments
    song_data = generate_song()

    if not song_data:
        ctx.logger.error("Failed to generate song data in lyricist.")
        return GenerateAudioResponse(
            status="error",
            error="Failed to generate song data",
            audio_url_1="",
            image_url_1="",
            video_url_1="",
            image_large_url_1="",
            audio_url_2="",
            image_url_2="",
            video_url_2="",
            image_large_url_2=""
        )
    # Step 2: Generate audio response using the shared function
    return await generate_audio_response(ctx, song_data)

# Include protocol in the singer agent
singer.include(audio_proto)


# Initialize the bureau and add the lyricist agent
bureau = Bureau(port=8258, endpoint="https://rhythmiqagent.255labs.xyz/submit")
bureau.add(lyricist)
bureau.add(singer)

if __name__ == "__main__":
    bureau.run()
