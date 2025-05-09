# app/graph/instructions_node.py

import json
import logging
import uuid
from datetime import datetime

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState

from app.config import get_llm
from app.schemas.instructions_schema import Instruction

logger = logging.getLogger(__name__)
model = get_llm()


def update_instructions(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> dict[str, list]:
    """
    Extract and persist user instructions, preferences, or complaints.

    This node will:
      1. Load the most recent user message.
      2. Prompt the LLM to summarise that message into a single directive
         (paraphrased, not verbatim) conforming to the Instruction schema.
      3. Parse and validate the LLM’s JSON reply into an Instruction.
      4. Persist the Instruction under namespace ("instructions", user_id) with a unique key.
      5. Return a ToolMessage acknowledging the tool call.
    """
    # 1) Identify user and namespace
    user_id = config["configurable"]["user_id"]
    namespace = ("instructions", user_id)
    user_msg = state["messages"][-2]  # HumanMessage

    # 2) Build the system prompt using the Instruction schema
    schema_str = json.dumps(Instruction.model_json_schema(), indent=2)
    prompt = (
        f"System time (UTC): {datetime.utcnow().isoformat()}\n\n"
        "Extract one concise, paraphrased instruction or preference from the user message. "
        "Summarise it as a single actionable sentence; do not quote the user verbatim.\n"
        "Here is the JSON schema for an Instruction object:\n" + schema_str + "\n\n"
        f'User said: "{user_msg.content}"\n\n'
        "Return ONLY the raw JSON document — absolutely no code fences, no markdown, no commentary."
    )
    system_msg = SystemMessage(content=prompt)

    # 3) Invoke the LLM and parse its JSON response
    reply = model.invoke([system_msg])
    try:
        data = json.loads(reply.content)
    except json.JSONDecodeError:
        logger.error("Instruction JSON parse failed. Raw: %s", reply.content)
        data = {"content": user_msg.content, "tags": []}

    # 4) Validate and persist
    try:
        inst = Instruction(**data)
    except Exception as e:
        logger.warning("Instruction validation failed(%s). Using raw message.", e)
        inst = Instruction(content=user_msg.content)

    key = uuid.uuid4().hex
    store.put(namespace, key, inst.model_dump())
    logger.debug("Saved instruction %s for user %s", key, user_id)

    # 5) Acknowledge the tool call
    tool_call = state["messages"][-1].tool_calls[0]
    ack = ToolMessage(
        content="instruction saved",
        name=tool_call["name"],
        tool_call_id=tool_call["id"],
    )
    return {"messages": [ack]}
