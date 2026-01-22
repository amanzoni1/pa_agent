import os
import sys
from langchain.chat_models import init_chat_model

SHORTCUTS = {
    "openai": ("openai", "gpt-4o"),
    "claude": ("anthropic", "claude-3-5-sonnet-latest"),
    "fast":   ("fireworks", "accounts/fireworks/models/gpt-oss-20b"),
}

def validate_key(provider):
    """Ensures the correct API key is present."""
    key_map = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "fireworks": "FIREWORKS_API_KEY",
    }

    env_var = key_map.get(provider)
    if env_var and not os.getenv(env_var):
        print(f"\n❌ CONFIG ERROR: Missing Environment Variable: {env_var}")
        print(f"   To use provider '{provider}', add this key to your .env file.\n")
        sys.exit(1)

def parse_model_string(model_arg):
    """
    Parses the CLI argument into (provider, model_name).
    Supports:
      1. Shortcuts: 'openai', 'fast'
      2. Prefixes:  'fw-accounts/...', 'oa-gpt-4o', 'ant-claude-3'
    """
    # Check Shortcuts
    if model_arg in SHORTCUTS:
        return SHORTCUTS[model_arg]

    # Check Prefixes (The Flexible Way)
    if model_arg.startswith("oa-"):
        # OpenAI: oa-gpt-3.5-turbo
        return "openai", model_arg[3:]

    if model_arg.startswith("ant-"):
        # Anthropic: ant-claude-3-opus...
        return "anthropic", model_arg[4:]

    if model_arg.startswith("fw-"):
        # Fireworks: fw-accounts/fireworks/models/qwen...
        return "fireworks", model_arg[3:]

    # 3. Fallback / Error
    print(f"\n❌ MODEL ERROR: Could not parse '{model_arg}'")
    print("   Usage examples:")
    print("   • Shortcut:  --model openai")
    print("   • Fireworks: --model fw-accounts/fireworks/models/llama-v3-70b")
    print("   • OpenAI:    --model oa-gpt-4-turbo")
    print("   • Anthropic: --model ant-claude-3-opus-20240229")
    sys.exit(1)

def get_chat_model(model_id, **kwargs):
    """
    Main entry point.
    """
    provider, model_name = parse_model_string(model_id)

    validate_key(provider)

    print(f"--- 🧠 Loading Brain: {model_name} ({provider}) ---")

    try:
        return init_chat_model(model=model_name, model_provider=provider, **kwargs)
    except Exception as e:
        print(f"❌ INIT ERROR: {e}")
        sys.exit(1)
