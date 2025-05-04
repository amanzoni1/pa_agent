# app/graph/profile_node.py

import json
import logging
from datetime import datetime

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState

from app.config import get_llm
from app.schemas.profile_schema import Profile

logger = logging.getLogger(__name__)

# Initialize the LLM once at import time
model = get_llm()


def update_user_profile(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> dict[str, list]:
    """
    Merge the user's latest message into our persistent Profile JSON.

    Steps:
    1. Load existing profile JSON (if any) from the store under key "user_profile".
    2. Prompt the LLM with the JSON schema + current data + latest user message.
    3. Parse the LLM's reply as a full, updated JSON document.
    4. Write it back into the store.
    5. Return a ToolMessage acknowledging the original UpdateMemory call.
    """
    # 1) Load existing profile
    user_id = config["configurable"]["user_id"]
    namespace = ("profile", user_id)
    key = "user_profile"

    existing_entry = store.get(namespace, key)
    existing_profile = existing_entry.value if existing_entry else {}

    logger.debug("Loaded existing profile for %r: %r", user_id, existing_profile)

    # 2) Grab the last user message (two messages back: human → assistant(tool_call))
    user_message = state["messages"][-2]

    # 3) Build the system prompt
    system_prompt = (
        f"System time: {datetime.utcnow().isoformat()}\n\n"
        "Maintain exactly these fields:\n"
        f"{Profile.schema_json(indent=2)}\n\n"
        "Here is the current JSON:\n"
        f"{json.dumps(existing_profile, indent=2)}\n\n"
        f"User just said: “{user_message.content}”\n\n"
        "Update only `name`, `location`, `job`, `passions` or `goals` if new facts.\n"
        "Return *only* the complete JSON document."
    )
    system_msg = SystemMessage(content=system_prompt)

    # 4) Invoke the LLM
    reply = model.invoke([system_msg, user_message])
    try:
        updated_profile = json.loads(reply.content)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse updated profile JSON: %s\nLLM reply was:\n%s",
            e,
            reply.content,
        )
        updated_profile = existing_profile

    # 5) Persist the updated profile
    store.put(namespace, key, updated_profile)
    logger.debug("Stored updated profile for %r: %r", user_id, updated_profile)

    # 6) Acknowledge the original UpdateMemory call
    original_call = state["messages"][-1].tool_calls[0]
    ack = ToolMessage(
        content="user profile updated",
        name=original_call["name"],
        tool_call_id=original_call["id"],
    )

    return {"messages": [ack]}
