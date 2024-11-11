import os
import requests
import json
from dotenv import load_dotenv
import random
import re  # Added for regex parsing

# Load environment variables from a .env file if present
load_dotenv()

# Configuration
GPT_PROVIDER = os.getenv("GPT_PROVIDER", "nanogpt").lower()  # Default to 'nanogpt' if not set

N_SHOT = int(os.getenv("N_SHOT", "2"))  # Number of example songs to include

# Configuration for NanoGPT API
NANOGPT_BASE_URL = "https://nano-gpt.com/api"
NANOGPT_API_KEY = os.getenv("NANOGPT_API_KEY")
NANOGPT_DEFAULT_MODEL = os.getenv("NANOGPT_MODEL", "o1-mini")

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

def talk_to_gpt(prompt, model=NANOGPT_DEFAULT_MODEL, messages=None):
    """
    Sends a prompt to the NanoGPT API and returns the response.

    Args:
        prompt (str): The input prompt to send to the model.
        model (str): The model to use for generation.
        messages (list): Optional list of messages for context.

    Returns:
        dict: Parsed JSON response from NanoGPT API containing the generated text and additional info.
    """
    headers = {
        "x-api-key": NANOGPT_API_KEY,
        "Content-Type": "application/json"
    }

    if messages is None:
        messages = []

    data = {
        "prompt": prompt,
        "model": model,
        "messages": messages
    }

    endpoint = f"{NANOGPT_BASE_URL}/talk-to-gpt"

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"HTTP Request to NanoGPT failed: {e}")
        return None

    # Assuming the response text contains JSON separated by <NanoGPT> tags
    try:
        parts = response.text.split('<NanoGPT>')
        if len(parts) < 2:
            print("Unexpected response format from NanoGPT API.")
            return None

        # Extract the text response (everything before <NanoGPT>)
        text_response = parts[0].strip()

        # Extract the NanoGPT info
        nano_info_str = parts[1].split('</NanoGPT>')[0]
        nano_info = json.loads(nano_info_str)

        return {
            "text_response": text_response,
            "nano_info": nano_info
        }
    except (IndexError, json.JSONDecodeError) as e:
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
        "max_tokens": 4096
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

def generate_song(instruction=None):
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

    # Get random song files for examples
    try:
        song_files = [f for f in os.listdir("songs") if f.endswith('.txt')]
        if not song_files:
            raise FileNotFoundError("No song files found in songs directory")

        # Read base prompt and system prompt
        with open("base.txt", "r") as file:
            base_prompt = file.read().strip()
        with open("system.txt", "r") as file:
            system_prompt = file.read().strip()
        messages = [{"role": "system", "content": system_prompt}]

        # Select random examples
        examples = []
        num_examples = min(N_SHOT, len(song_files))
        selected_songs = random.sample(song_files, num_examples)

        for idx, song_file in enumerate(selected_songs):
            with open(f"songs/{song_file}", "r") as song_f:
                song_content = song_f.read().strip()
            examples.append(f"\nExample {idx + 1}:\nSong:\n{song_content}")

        # Build the user prompt
        user_prompt = f"{base_prompt}\n{''.join(examples)}\n\nInstructions:\n{instruction}"

    except FileNotFoundError as e:
        print(f"Error: {e}")
        return None
    except IOError as e:
        print(f"Error reading files: {e}")
        return None

    # Call the appropriate GPT provider
    if GPT_PROVIDER == "nanogpt":
        print("\n--- Using NanoGPT API ---")
        nano_response = talk_to_gpt(user_prompt, messages=messages)
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
    """
    Parses the response text from the GPT model and extracts song data.

    Args:
        response_text (str): The raw text response from the GPT model.

    Returns:
        dict: A dictionary containing song data.
    """
    song_data = {}
    try:
        # Use regex to extract different parts of the song.txt content
        title_match = re.search(r'Title:\s*(.*)', response_text, re.DOTALL)
        lyrics_match = re.search(r'Lyrics:\s*(.*?)Style', response_text, re.DOTALL)
        style_match = re.search(r'Style:\s*(.*?)\n\n', response_text, re.DOTALL)
        negative_style_match = re.search(r'Negative Style:\s*(.*?)\n\n', response_text, re.DOTALL)

        # Extracted data
        title = title_match.group(1).strip()[:80] if title_match else "No title found"
        if not lyrics_match:
            assert False, "No lyrics found"
        lyrics = lyrics_match.group(1).strip()[:3000]
        style = style_match.group(1).strip()[:120] if style_match else "No style found"
        negative_style = negative_style_match.group(1).strip()[:120] if negative_style_match else ""


        song_data['title'] = title
        song_data['lyrics'] = lyrics
        song_data['style'] = style
        song_data['negative_style'] = negative_style

    except Exception as e:
        print(f"Error parsing song response: {e}")

    return song_data

def main():
    """
    Main function to demonstrate the generate_song function.
    """
    # Example usage of generate_song
    song_data = generate_song("Create a motivational song about overcoming challenges.")

    if song_data:
        print("\nGenerated Song Data:")
        print(f"Title: {song_data['title']}")
        print(f"Lyrics:\n{song_data['lyrics']}")
        print(f"Style: {song_data['style']}")
        print(f"Negative Style: {song_data['negative_style']}")
    else:
        print("Song generation failed.")

if __name__ == "__main__":
    main()

