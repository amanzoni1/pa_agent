import os
import sys
from langchain.chat_models import init_chat_model

# 1. The Registry of Brains
MODELS = {
    "openai": ("openai", "gpt-4o"),
    "anthropic": ("anthropic", "claude-3-5-sonnet-20240620"),
    "deepseek": ("fireworks", "accounts/fireworks/models/deepseek-v3p2"),
    "qwen-main": ("fireworks", "accounts/fireworks/models/qwen3-235b-a22b-instruct-2507"),
    "qwen-vision": ("fireworks", "accounts/fireworks/models/qwen3-vl-30b-a3b-instruct"),
    "fast-20b": ("fireworks", "accounts/fireworks/models/gpt-oss-20b"),
}

def validate_key(provider):
    """Checks if the necessary API key is set."""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "fireworks": "FIREWORKS_API_KEY",
    }

    env_var = key_map.get(provider)
    if env_var and not os.getenv(env_var):
        print(f"❌ Error: Missing Environment Variable: {env_var}")
        print(f"   Please add it to your .env file to use provider: {provider}")
        sys.exit(1)

def get_chat_model(model_id, **kwargs):
    """
    Returns the configured model based on the CLI string.
    """
    if model_id not in MODELS:
        print(f"⚠️ Warning: Model '{model_id}' not found. Defaulting to OpenAI.")
        provider, model_name = MODELS["openai"]
    else:
        provider, model_name = MODELS[model_id]

    validate_key(provider)

    print(f"--- 🧠 Loading Brain: {model_name} ({provider}) ---")

    try:
        return init_chat_model(model=model_name, model_provider=provider, **kwargs)
    except Exception as e:
        print(f"❌ Error initializing model: {e}")
        sys.exit(1)
