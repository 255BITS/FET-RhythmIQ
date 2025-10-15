import random

MODEL_NICKNAMES = {
    # Latest additions:
    "inclusionai/ling-1t": "Ling 1T",
    "moonshotai/Kimi-K2-Instruct-0905": "Kimi K2 Instruct",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    "claude-sonnet-4-5-20250929": "Claude Sonnet 4.5",
    "claude-sonnet-4-20250514": "Claude Sonnet 4",
    "claude-opus-4-1-20250805": "Claude Opus 4.1",
    "gpt-5-chat-latest": "GPT-5 Chat",
    "Qwen/Qwen3-235B-A22B-Instruct-2507": "Qwen3 235B A22B",
    "z-ai/glm-4.6": "GLM 4.6",
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
