from deepagents import create_deep_agent
from app.agent.config import get_chat_model
from app.agent.backend import make_backend, get_checkpointer, get_store
from app.agent.tools import internet_search

# Defines the "Identity" and "File Protocol"
SYSTEM_PROMPT = f"""
You are the Official Support Assistant for "Acme Corp".

# MEMORY PROTOCOL
1. **Startup:** Read `/memories/user_profile.md` at the start.
2. **Update:** Save user details (name, role, constraints) to `/memories/user_profile.md`.
3. **Drafting:** Use `/workspace/` for notes.
"""

def build_agent(provider="openai"):
    # Initialize components
    model = get_chat_model(provider)
    store = get_store()
    checkpointer = get_checkpointer()

    # Create the Deep Agent
    agent = create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        # memory=["./AGENTS.md"],
        tools=[internet_search],
        store=store,               # Long-term DB (Postgres/Memory)
        checkpointer=checkpointer, # Thread State (Redis)
        backend=make_backend,      # Router (/memories/ vs /workspace/)
    )

    return agent
