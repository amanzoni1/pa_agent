import os
from langchain.chat_models import init_chat_model

# Easy switch for your experiments
MODELS = {
    "openai": "openai:gpt-4o",
    "anthropic": "anthropic:claude-3-5-sonnet-latest",
    "fireworks": "fireworks:accounts/fireworks/models/llama-v3p3-70b-instruct",
    "deepseek": "fireworks:accounts/fireworks/models/deepseek-r1"
}

def get_chat_model(provider="openai"):
    """
    Returns the configured model based on the provider string.
    """
    model_string = MODELS.get(provider, MODELS["openai"])
    print(f"--- Loading Model: {model_string} ---")

    # This automatically handles the API key if env vars are set
    return init_chat_model(model=model_string)
