from uagents import Agent, Bureau, Context, Model, Protocol
from singer import generate_song
from dotenv import load_dotenv
import os
import json
import time
import requests

load_dotenv()

lyricist_seed = os.getenv("FET_LYRICIST_SEED", "RhythmIQ Lyricist seed phrase")
mailbox_key = os.getenv("FET_LYRICIST_MAILBOX", "RhythmIQ Lyricist mail")
# Create a single agent - RhythmIQ Lyricist
lyricist = Agent(name="RhythmIQ Lyricist", seed=lyricist_seed)#, mailbox=f"{mailbox_key}@https://agentverse.ai")

fox_api_key = os.getenv("FOX_API_KEY")
singer_seed = os.getenv("FET_SINGER_SEED", "RhythmIQ Singer seed phrase")
singer = Agent(name="RhythmIQ Singer", seed=singer_seed)


class Request(Model):
    text: str

class Response(Model):
    timestamp: int
    text: str
    agent_address: str

# Define the models
class BroadcastSongRequest(Model):
    instruction: str

class BroadcastSongResponse(Model):
    title: str
    lyrics: str
    style: str
    negative_style: str

GenerateAudioRequest = BroadcastSongResponse

class GenerateAudioResponse(Model):
    audio_url: str
    image_url: str

# Define protocol
proto = Protocol(name="SongwriterProtocol", version="1.0")

@proto.on_message(model=BroadcastSongRequest, replies=BroadcastSongResponse)
async def handle_song_request(ctx: Context, sender: str, msg: BroadcastSongRequest):
    # Use prompt.py's generate_song function
    instruction = msg.instruction
    song_data = generate_song(instruction)

    if song_data:
        response = BroadcastSongResponse(
            title=song_data.get('title', ''),
            lyrics=song_data.get('lyrics', ''),
            style=song_data.get('style', ''),
            negative_style=song_data.get('negative_style', '')
        )
        await ctx.send(sender, response)
    else:
        ctx.logger.error("Failed to generate song.")


@singer.on_rest_post("/sing", GenerateAudioRequest, Response)
async def handle_sing_post(ctx: Context, req: GenerateAudioRequest) -> Response:
    ctx.logger.info(f"Received /sing POST request with data: {req}")

    song_ids = generate_audio(
        title=req.title,  # Title can be empty or extracted from 'req' if available
        lyrics=req.lyrics,  # Lyrics can be empty or extracted from 'req' if available
        style=req.style,  # Style can be empty or extracted from 'req' if available
        negative_style=req.negative_style  # Negative style can be empty or extracted from 'req' if available
    )
    if song_ids:
        ctx.logger.info(f"Song IDs received: {song_ids}")
        try:
            audio_url, image_url = poll_for_audio(song_ids)
            return Response(
                text=f"audio_url: {audio_url} image url: {image_url}",
                agent_address=ctx.agent.address,
                timestamp=int(time.time()),
            )
        except Exception as e:
            ctx.logger.error(f"Error during polling: {e}")
    else:
        ctx.logger.error("Failed to initiate audio generation.")

# Include protocol in the lyricist agent
lyricist.include(proto)


@lyricist.on_rest_post("/rest/post", Request, Response)
async def handle_post(ctx: Context, req: Request) -> Response:
    ctx.logger.info("Received POST request")
    return Response(
        text=f"Received: {req.text}",
        agent_address=ctx.agent.address,
        timestamp=int(time.time()),
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
        'mv': 'chirp-v3-5'
    }
    response = requests.post('https://api.sunoaiapi.com/api/v1/gateway/generate/music', json=data, headers=headers)
    print("response", response.status_code, response.text)
    if response.status_code == 200:
        resp_data = response.json()
        if resp_data['code'] == 0:
            song_ids = [item['song_id'] for item in resp_data['data']]
            return song_ids
    return None

# Function to poll for the generated audio
def poll_for_audio(song_ids):
    headers = {
        'Content-Type': 'application/json',
        'api-key': fox_api_key
    }
    params = {
        'ids': ','.join(song_ids)
    }
    while True:
        print("polling")
        time.sleep(5)  # Wait before polling again
        response = requests.get('https://api.sunoaiapi.com/api/v1/gateway/query', params=params, headers=headers)
        print("---",response.status_code)
        print(json.dumps(response.json(), indent=2))
        if response.status_code == 200:
            resp_data = response.json()
            if isinstance(resp_data, list):
                for item in resp_data:
                    if item['status'] == 'complete':
                        audio_url = item.get('audio_url')
                        image_url = item.get('image_url')
                        return audio_url, image_url
                    elif item['status'] == 'error':
                        raise Exception(f"Generation error: {item['meta_data'].get('error_message')}")

@audio_proto.on_message(model=GenerateAudioRequest, replies=GenerateAudioResponse)
async def handle_generate_audio(ctx: Context, sender: str, msg: GenerateAudioRequest):
    ctx.logger.info(f"Received audio generation request with data: {msg}")
    song_ids = generate_audio(
        title=msg.title,
        lyrics=msg.lyrics,
        style=msg.style,
        negative_style=msg.negative_style
    )
    if song_ids:
        ctx.logger.info(f"Song IDs received: {song_ids}")
        try:
            audio_url, image_url = poll_for_audio(song_ids)
            response = GenerateAudioResponse(
                audio_url=audio_url,
                image_url=image_url
            )
            await ctx.send(sender, response)
        except Exception as e:
            ctx.logger.error(f"Error during polling: {e}")
    else:
        ctx.logger.error("Failed to initiate audio generation.")

# Include protocol in the singer agent
singer.include(audio_proto)


# Initialize the bureau and add the lyricist agent
bureau = Bureau(port=8000, endpoint="http://localhost:8000/submit")
bureau.add(lyricist)
bureau.add(singer)

if __name__ == "__main__":
    bureau.run()
