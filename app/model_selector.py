import random

def get_random_model_name():
    """
    Returns a random model name from a predefined list of NANOGPT models.
    """
    models = [
        #"Rocinante-12B-v1.1 Q8",
        #"neversleep/llama-3-lumimaid-70b",
        #"x-ai/grok-2",
        #"Cydonia-22B-v1.1-Q5_K_L",
        #"microsoft/wizardlm-2-8x22b",
        "o3-mini",
        #"o1-preview",
        #"Volta-Merge-70B-1",
        "chatgpt-4o-latest",
        "deepseek-reasoner",
        #"doubao-1.5-pro-32k",
        "claude-3-5-sonnet-20241022",
        #"gpt-4o-mini",
        #"yi-large",
        #"yi-spark",
        #"yi-lightning",
        #"glm-4-plus",
        #"anthracite-org/magnum-v4-72b",
        #"neversleep/llama-3.1-lumimaid-70b",
        #"accounts/fireworks/models/llama-v3p1-405b-instruct",
        #"nousresearch/hermes-3-llama-3.1-405b",
        #"nvidia/llama-3.1-nemotron-70b-instruct",
        #"google/gemini-pro-1.5",
        #"google/gemini-flash-1.5",
        "gemini-2.0-pro-exp-02-05",
        "gemini-2.0-flash-thinking-exp-01-21"
    ]
    return random.choice(models)

# Example usage:
if __name__ == "__main__":
    print(get_random_model_name())
