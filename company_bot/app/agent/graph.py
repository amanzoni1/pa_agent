from deepagents import create_deep_agent
from app.agent.config import get_chat_model
from app.agent.backend import make_backend, get_checkpointer, get_store
from app.agent.tools import internet_search

# 1. The Constitution (System Prompt)
# Defines the "Identity" and "File Protocol"
SYSTEM_PROMPT = """
You are a helpful Company Assistant.

MEMORY PROTOCOL:
1. You have a long-term memory folder at `/memories/`.
2. ALWAYS check `/memories/user_profile.md` at the start of a chat to know who you are talking to.
3. If the user tells you important facts (name, role, project), SAVE them to `/memories/user_profile.md` using 'write_file' or 'edit_file'.
4. Use `/workspace/` for temporary notes.

BEHAVIOR:
- Be concise.
- Use the provided skills if you get stuck.
"""

def build_agent(provider="openai"):
    # Initialize components
    model = get_chat_model(provider)
    store = get_store()
    checkpointer = get_checkpointer()

    # Create the Deep Agent
    agent = create_deep_agent(
        model=model,
        tools=[internet_search],   # Custom Search Tool
        store=store,               # Long-term DB (Postgres/Memory)
        checkpointer=checkpointer, # Thread State (Redis)
        backend=make_backend,      # Router (/memories/ vs /workspace/)
        system_prompt=SYSTEM_PROMPT,
        memory=["/data/memory/policy.md"],
    )

    return agent
