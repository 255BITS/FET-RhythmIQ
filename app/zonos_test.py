import os
API_KEY=os.getenv("ZONOS_API_KEY", "zsk-d0f94527697f2e5edaaf7f12b127f41ac5879da89fa7364b18e10255b1903d10")

from zyphra import ZyphraClient

client = ZyphraClient(api_key=API_KEY)

with ZyphraClient(api_key=API_KEY) as client:
    # Save to file
    output_path = client.audio.speech.create(
        text="You're listening to 97.3 the GOAT. A.I. Rap God 24 hours a day!",
        speaking_rate=15,
        output_path="output.webm"
    )
    
    # Get bytes
    #audio_data = client.audio.speech.create(
    #    text="Hello, world!",
    #    speaking_rate=15
    #)
