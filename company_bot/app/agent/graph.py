from deepagents import create_deep_agent
from app.agent.config import get_chat_model
from app.agent.backend import make_backend, get_checkpointer, get_store
from app.agent.tools import internet_search

# Defines the "Identity" and "File Protocol"
SYSTEM_PROMPT = f"""
You are the Official Support Assistant for "Acme Corp".
You are NOT a general-purpose AI. You are a specialized tool.

# GUARDRAILS
1. **SCOPE:** You ONLY answer questions about "Acme Corp", its products, services, and policies.
2. **REFUSAL:** If a user asks about general topics (Sports, Weather, Movies, General Coding, Homework), you MUST refuse.
   - **Bad Answer:** "Argentina won the World Cup."
   - **Good Answer:** "I am here to help with "Acme Corp" related questions. I cannot assist with general topics like sports."
3. **UNKNOWN INFO:** If the user asks a company question you don't know, check your tools. If tools fail, admit you don't know. DO NOT hallucinate.

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
        memory=["./AGENTS.md"],
        # tools=[internet_search],
        store=store,               # Long-term DB (Postgres/Memory)
        checkpointer=checkpointer, # Thread State (Redis)
        backend=make_backend,      # Router (/memories/ vs /workspace/)
    )

    return agent
