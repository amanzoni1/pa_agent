import os
import datetime
from deepagents import create_deep_agent
from app.agent.config import get_chat_model
from app.agent.backend import make_backend, get_checkpointer, get_store
from app.agent.tools import lookup_company_policy


# DYNAMIC SYSTEM PROMPT
SYSTEM_PROMPT = f"""
### RUNTIME CONTEXT
- **Current Date:** {datetime.datetime.now().strftime("%Y-%m-%d")}
- **System Status:** ONLINE

### TOOL USAGE PROTOCOL (TECHNICAL)
You have access to `lookup_company_policy`. You MUST follow these rules:

1.  **"SEARCH FIRST" RULE:**
    You have NO internal knowledge of Acme Corp. You ONLY know what is in the database.
    - If a user asks for a policy, password, or setting: **YOU MUST CALL THE TOOL.**
    - Do not answer from your own training data.

2.  **QUERY EXPANSION STRATEGY:**
    Users write lazy queries. You must translate them into "Handbook Language" before calling the tool.
    - User: "wifi sucks" -> Tool Call: "corporate wireless network troubleshooting"
    - User: "sick leave" -> Tool Call: "HR employee sick leave policy 2026"
    - User: "vpn key"    -> Tool Call: "AcmeGuard VPN shared secret key"

3.  **CITATION:**
    Always mention the source document found by the tool (e.g., "According to 'IT_05.md'...").
"""

def build_agent(provider="fast-20b"):
    # Initialize components
    model = get_chat_model(provider)
    store = get_store()
    checkpointer = get_checkpointer()

    # Create the Deep Agent
    agent = create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        memory=["/system/AGENTS.md"],
        skills=["/system/skills/"],
        tools=[lookup_company_policy],
        store=store,
        checkpointer=checkpointer,
        backend=make_backend,
    )

    return agent
