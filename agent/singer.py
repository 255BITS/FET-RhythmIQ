import os
import requests
import json
from dotenv import load_dotenv
import random
import sys
import re  # Added for regex parsing
from xml_tools import toolbox, parser, formatter
sys.path.insert(0, os.path.abspath("../common"))
from stations import get_station_instructions, get_station_by_id

# Load environment variables from a .env file if present
load_dotenv()

# Configuration
GPT_PROVIDER = os.getenv("GPT_PROVIDER", "nanogpt").lower()  # Default to 'nanogpt' if not set

N_SHOT = int(os.getenv("N_SHOT", "2"))  # Number of example songs to include

# Configuration for NanoGPT API
NANOGPT_API_KEY = os.getenv("NANOGPT_API_KEY")
NANOGPT_DEFAULT_MODEL = os.getenv("NANOGPT_MODEL", "o3-mini")
NANOGPT_BASE_URL = "https://nano-gpt.com/api/v1"

# Configuration for Local Server
LOCAL_SERVER_ADDRESS = os.getenv("LOCAL_SERVER_ADDRESS", "127.0.0.1")
LOCAL_SERVER_PORT = os.getenv("LOCAL_SERVER_PORT", "5000")  # Ensure it's a string


print(f"Using GPT Provider: {GPT_PROVIDER.capitalize()}")

def load_random_instruction():
    """
    Loads a random instruction from the instructions directory.

    Returns:
        str: The content of a randomly selected instruction file.
    """
    instructions_dir = "instructions"
    try:
        instruction_files = [f for f in os.listdir(instructions_dir) if f.endswith('.txt')]
        if not instruction_files:
            raise FileNotFoundError("No instruction files found in the instructions directory.")
        selected_file = random.choice(instruction_files)
        with open(os.path.join(instructions_dir, selected_file), "r") as file:
            instruction_content = file.read().strip()
        return instruction_content
    except Exception as e:
        print(f"Error loading random instruction: {e}")
        return None

def validate_environment():
    """
    Validates that necessary environment variables are set based on the selected GPT provider.
    """
    if GPT_PROVIDER == "nanogpt":
        if not NANOGPT_API_KEY:
            raise ValueError("NANOGPT_API_KEY is not set. Please set it in the environment variables.")
    elif GPT_PROVIDER == "local":
        # Optionally, you can add validation for local server settings
        pass
    else:
        raise ValueError(f"Unsupported GPT_PROVIDER '{GPT_PROVIDER}'. Supported providers are 'nanogpt' and 'local'.")

def talk_to_gpt(prompt, model=None, messages=None):
    """
    Sends a prompt to the NanoGPT API using the OpenAI-compatible chat completions endpoint
    and returns the response in the same format as before.

    Args:
        prompt (str): The input prompt to send to the model.
        model (str): The model to use for generation.
        messages (list): Optional list of message dictionaries for context.
                         If provided, the prompt is appended as a user message.

    Returns:
        dict: A dictionary with two keys:
              - "text_response": The generated text from the assistant.
              - "nano_info": Additional info (e.g. usage statistics) from the API.
    """
    if model is None:
        model = NANOGPT_DEFAULT_MODEL
    headers = {
        "Authorization": f"Bearer {NANOGPT_API_KEY}",
        "Content-Type": "application/json"
    }

    # If no messages are provided, create one using the prompt;
    # otherwise, append the prompt as a user message.
    if messages is None:
        messages = [{"role": "user", "content": prompt}]
    else:
        if prompt and prompt.strip():
            messages.append({"role": "user", "content": prompt})

    # Build the payload using OpenAI-compatible parameters.
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0.8,
        "top_p": 0.99,
        "stream": False  # Non-streaming mode so that we get one complete response.
    }

    endpoint = f"{NANOGPT_BASE_URL}/chat/completions"

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request to NanoGPT failed: {e}")
        return None

    try:
        result = response.json()
        # Expected response format (non-streaming) is similar to OpenAI's:
        # {
        #    "id": "...", "object": "chat.completion", "created": ...,
        #    "model": "...",
        #    "choices": [{
        #         "index": 0,
        #         "message": {"role": "assistant", "content": "generated text"},
        #         "finish_reason": "stop"
        #    }],
        #    "usage": { ... }
        # }
        text_response = result["choices"][0]["message"]["content"]
        nano_info = result.get("usage", {})
        return {
            "text_response": text_response,
            "nano_info": nano_info
        }
    except (KeyError, json.JSONDecodeError) as e:
        print(f"Error parsing NanoGPT response: {e}")
        return None

def send_payload(prompt, server=LOCAL_SERVER_ADDRESS, port=LOCAL_SERVER_PORT):
    """
    Sends a formatted prompt to a local server for text generation.

    Args:
        prompt (str): The input prompt to send to the local server.
        server (str): The server address. Defaults to LOCAL_SERVER_ADDRESS.
        port (str): The server port. Defaults to LOCAL_SERVER_PORT.

    Returns:
        str: The generated text from the local server.
    """
    # Define the generation parameters
    params = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 8192
    }

    # Prepare the payload
    payload = params

    try:
        response = requests.post(
            f"http://{server}:{port}/v1/chat/completions",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request to local server failed: {e}")
        return None

    return response.json()["choices"][0]["message"]["content"]

def generate_song(instruction=None, model_name=None, artist=None, station=None):
    """
    Generates a song based on the provided instruction.

    Args:
        instruction (str): The instruction or description for the song.

    Returns:
        dict: A dictionary containing song data (description, title, lyrics, style, negative_style).
    """
    # Validate environment variables
    try:
        validate_environment()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        return None
    if instruction is None or instruction.strip() == "":
        instruction = load_random_instruction()
        if not instruction:
            print("Failed to load a random instruction.")
            return None

    # If a station is provided, lookup the station instructions and append to the prompt.
    if station:
        try:
            station_instructions = get_station_instructions(station)
            if station_instructions:
                instruction += "\n\n" + station_instructions
        except Exception as e:
            print(f"Error loading station instruction: {e}")

    # Get random song files for examples
    try:
        song_files = [f for f in os.listdir("songs") if f.endswith('.xml')]
        if not song_files:
            raise FileNotFoundError("No song files found in songs directory")

        # Read base prompt and system prompt
        with open("base.txt", "r") as file:
            base_prompt = file.read().strip()
        with open("system.txt", "r") as file:
            system_prompt = file.read().strip()

        #system_prompt += "\n"+formatter.usage_prompt(toolbox)
        messages = [{"role": "system", "content": system_prompt}]

        # Select random examples
        examples = []
        num_examples = min(N_SHOT, len(song_files))
        selected_songs = random.sample(song_files, num_examples)

        #for idx, song_file in enumerate(selected_songs):
        #    with open(f"songs/{song_file}", "r") as song_f:
        #        song_content = song_f.read().strip()
        #        song_content = f"<use_tool>\n<name>song</name>\n{song_content}</use_tool>"
        #    examples.append(f"\nExample {idx + 1}:\nSong:\n{song_content}")

        # Build the user prompt
        user_prompt = formatter.usage_prompt(toolbox)+"\n\n"+base_prompt+f"\n\nAdditional Instructions:\n{instruction}"#f"{base_prompt}\n{''.join(examples)}\n\nInstructions:\n{instruction}"
        if artist:
            user_prompt += f"\n\nYou are the artist: {artist}"

        print("SYSTEM", system_prompt, "USER", user_prompt)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None
    except IOError as e:
        print(f"Error reading files: {e}")
        return None

    # Call the appropriate GPT provider
    if GPT_PROVIDER == "nanogpt":
        print("\n--- Using NanoGPT API ---")
        nano_response = talk_to_gpt(user_prompt, messages=messages, model=model_name)
        if nano_response:
            print("NanoGPT Response:", nano_response['text_response'])
            song_data = parse_song_response(nano_response['text_response'])
            return song_data
        else:
            print("Failed to get response from NanoGPT API.")
            return None
    elif GPT_PROVIDER == "local":
        print("\n--- Using Local Server API ---")
        local_response = send_payload(user_prompt)
        if local_response:
            print("Local Server Response:", local_response)
            song_data = parse_song_response(local_response)
            return song_data
        else:
            print("Failed to get response from the local server.")
            return None
    else:
        print(f"Unsupported GPT_PROVIDER '{GPT_PROVIDER}'. Please set it to 'nanogpt' or 'local'.")
        return None

def parse_song_response(response_text):
    events = parser.parse(response_text)
    print("Parsing", response_text)
    for event in events:
        if event.is_tool_call:
            if event.tool.name == "song":
                result = toolbox.use(event).result
                return apply_length_constraints(result)
    print("No write_song event found in the response.")
    return {}

def apply_length_constraints(song_data):
    song_data['description'] = song_data.get('description', "No description found").strip()
    song_data['title'] = song_data.get('title', "No title found").strip()[:80]
    if not song_data.get('lyrics'):
        assert False, "No lyrics found"
    song_data['lyrics'] = song_data['lyrics'].strip()[:3000]
    song_data['style'] = song_data.get('style', "No style found").strip()[:120]
    song_data['negative_style'] = song_data.get('negative_style', "").strip()[:120]
    return song_data

def main():
    """
    Main function to demonstrate the generate_song function.
    """
    # Example usage of generate_song
    song_data = generate_song("Create a motivational song about overcoming challenges.")

    if song_data:
        print("\nGenerated Song Data:")
        print(f"Title: {song_data.get('title', 'No title found')}")
        print(f"Lyrics:\n{song_data.get('lyrics', 'No lyrics found')}")
        print(f"Style: {song_data.get('style', 'No style found')}")
        print(f"Negative Style: {song_data.get('negative_style', '')}")
    else:
        print("Song generation failed.")

if __name__ == "__main__":
    main()
