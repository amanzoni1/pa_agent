# app/graph/memories_node.py

import json
import logging
from datetime import datetime

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState

from app.config import get_llm
from app.schemas.memory_schema import Memory

logger = logging.getLogger(__name__)

# Initialize the LLM once at import time
model = get_llm()


def update_memories(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> dict[str, list]:
    """
    Extract and persist a one-off user experience to the 'memories' namespace.

    Steps:
    1. Extract the triggering user message (two messages back).
    2. Prompt the LLM to generate a concise memory object
       conforming to the Memory schema.
    3. Parse the LLM's JSON reply into a memory dict.
    4. Persist it under namespace ("memories", user_id) with an auto-generated key.
    5. Return a ToolMessage acknowledging the original UpdateMemory call.
    """
    # 1) Identify user and namespace
    user_id = config["configurable"]["user_id"]
    namespace = ("memories", user_id)
    user_message = state["messages"][-2].content.strip()

    logger.debug("Generating new memory from message: %r", user_message)

    # 2) Build the system prompt using the Memory schema
    system_prompt = (
        f"System time (UTC): {datetime.utcnow().isoformat()}\n\n"
        "You are an assistant that extracts meaningful experiences from a user message.\n"
        "Here is the JSON schema for a Memory:\n\n"
        f"{Memory.schema_json(indent=2)}\n\n"
        "User just said:\n"
        f'"{user_message}"\n\n'
        "Generate a JSON object that conforms exactly to the schema,\n"
        "with a concise `content` field summarizing the experience and\n"
        "`tags` set to null. Return *only* the JSON object."
    )
    system_msg = SystemMessage(content=system_prompt)

    # 3) Invoke the LLM and parse its JSON output
    reply = model.invoke([system_msg])
    try:
        memory_data = json.loads(reply.content)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse memory JSON: %s\nLLM reply was:\n%s",
            e,
            reply.content,
        )
        # Fallback: store the raw user message
        memory_data = {"content": user_message, "tags": None}

    # 4) Persist the memory
    store.put(namespace, None, memory_data)
    logger.debug("Stored new memory for %r: %r", user_id, memory_data)

    # 5) Acknowledge the original UpdateMemory call
    tool_call = state["messages"][-1].tool_calls[0]
    ack = ToolMessage(
        content="memory saved",
        name=tool_call["name"],
        tool_call_id=tool_call["id"],
    )

    return {"messages": [ack]}
