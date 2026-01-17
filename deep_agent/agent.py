# agents/deep_agent/agent.py
from deepagents import create_deep_agent
from config import get_chat_model
from memory import make_backend, get_checkpointer, get_store
from tools import internet_search

# 1. System Prompt that enforces the Memory Strategy
SYSTEM_PROMPT = """
You are a Company Assistant.

MEMORY PROTOCOL:
1. You have a long-term memory folder at `/memories/`.
2. ALWAYS check `/memories/user_profile.md` at the start of a chat to know who you are talking to.
3. If the user tells you important facts (name, role, project), SAVE them to `/memories/user_profile.md` using 'write_file' or 'edit_file'.
4. Use `/workspace/` for temporary notes (these will be deleted later).
"""

def build_agent(provider="openai"):
    # Initialize components
    model = get_chat_model(provider)
    store = get_store()
    checkpointer = get_checkpointer()

    # Create the Deep Agent
    agent = create_deep_agent(
        model=model,
        tools=[internet_search], # We add our custom search tool
        store=store,             # The long-term DB
        checkpointer=checkpointer, # The thread state
        backend=make_backend,    # The Router logic
        system_prompt=SYSTEM_PROMPT
    )

    return agent
