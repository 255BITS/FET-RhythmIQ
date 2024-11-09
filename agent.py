from uagents import Agent, Bureau, Context, Model, Protocol
from singer import generate_song
from dotenv import load_dotenv
import os
import time

load_dotenv()

lyricist_seed = os.getenv("FET_LYRICIST_SEED", "RhythmIQ Lyricist seed phrase")
mailbox_key = os.getenv("FET_LYRICIST_MAILBOX", "RhythmIQ Lyricist mail")
# Create a single agent - RhythmIQ Lyricist
lyricist = Agent(name="RhythmIQ Lyricist", seed=lyricist_seed)#, mailbox=f"{mailbox_key}@https://agentverse.ai")

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
    description: str
    title: str
    lyrics: str
    style: str
    negative_style: str


# Define protocol
proto = Protocol(name="SongProtocol", version="1.0")

@proto.on_message(model=BroadcastSongRequest, replies=BroadcastSongResponse)
async def handle_song_request(ctx: Context, sender: str, msg: BroadcastSongRequest):
    # Use prompt.py's generate_song function
    instruction = msg.instruction
    song_data = generate_song(instruction)

    if song_data:
        response = BroadcastSongResponse(
            description=song_data.get('description', ''),
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


@lyricist.on_rest_post("/rest/post", Request, Response)
async def handle_post(ctx: Context, req: Request) -> Response:
    ctx.logger.info("Received POST request")
    return Response(
        text=f"Received: {req.text}",
        agent_address=ctx.agent.address,
        timestamp=int(time.time()),
    )

# Initialize the bureau and add the lyricist agent
bureau = Bureau(port=8000, endpoint="http://localhost:8000/submit")
bureau.add(lyricist)

if __name__ == "__main__":
    bureau.run()
