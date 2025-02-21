import random

MODEL_NICKNAMES = {
    "o3-mini": "Ozone 3",
    "chatgpt-4o-latest": "GPT-4O Maestro",
    "deepseek-reasoner": "Deep Seeker",
    "grok-3": "Grok Rhymes",
    "r1-1776": "Perplexity Renegade",
    "claude-3-5-sonnet-20241022": "Sonnet 3.5",
    "gemini-2.0-pro-exp-02-05": "G-Mini Pro",
    "gemini-2.0-flash-thinking-exp-01-21": "G-Mini Flash"
}

def get_model_nickname(model_name):
    """
    Returns a tuple of (model_name, nickname).
    If a nickname is not predefined, it defaults to the model name.
    """
    return (model_name, MODEL_NICKNAMES.get(model_name, model_name))

def get_random_model_name():
    """
    Returns a random model name from a predefined list of models.
    """
    models = list(MODEL_NICKNAMES.keys())
    return random.choice(models)

# Example usage:
if __name__ == "__main__":
    model_name = get_random_model_name()
    print(get_model_nickname(model_name))
