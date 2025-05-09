# app/graph/projects_node.py

import json
import uuid
import logging
from datetime import datetime

from langchain_core.messages import SystemMessage, ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState

from app.config import get_llm
from app.schemas.project_schema import Project

logger = logging.getLogger(__name__)

# Initialize the LLM once at import time
model = get_llm()


def update_projects(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
) -> dict[str, list]:
    """
    Extract and persist a new project plan to the 'projects' namespace.

    Steps:
    1. Extract the triggering user message (two messages back).
    2. Prompt the LLM to generate a concise title and description
       conforming to the Project schema.
    3. Parse the LLM's JSON reply into a project dict.
    4. Persist it under namespace ("projects", user_id) with an auto-generated key.
    5. Return a ToolMessage acknowledging the original UpdateMemory call.
    """
    # 1) Identify user and namespace
    user_id = config["configurable"]["user_id"]
    namespace = ("projects", user_id)
    user_message = state["messages"][-2].content.strip()

    logger.debug("Generating new project from message: %r", user_message)

    # 2) Build the system prompt using the Project schema
    system_prompt = (
        f"System time (UTC): {datetime.utcnow().isoformat()}\n\n"
        "You are an assistant that extracts project plans from a user message.\n"
        "Here is the JSON schema for a Project:\n\n"
        f"{Project.schema_json(indent=2)}\n\n"
        "User just said:\n"
        f'"{user_message}"\n\n'
        "Generate a JSON object that conforms exactly to the schema,\n"
        "with a concise `title` and a clear `description`.  \n"
        'Set `due_date` to null and `status` to "planned".\n'
        "Return *only* the JSON object."
    )
    system_msg = SystemMessage(content=system_prompt)

    # 3) Invoke the LLM and parse its JSON output
    reply = model.invoke([system_msg])
    try:
        project_data = json.loads(reply.content)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse project JSON: %s\nLLM reply was:\n%s",
            e,
            reply.content,
        )
        # Fallback: build a minimal project
        title = user_message.split(".")[0][:50] or user_message[:50]
        project_data = {
            "title": title,
            "description": user_message,
            "due_date": None,
            "status": "planned",
        }

    # 4) Persist the project
    new_key = uuid.uuid4().hex
    store.put(namespace, new_key, project_data)
    logger.debug("Stored project %r for %s", new_key, user_id)

    # 5) Acknowledge the original UpdateMemory call
    tool_call = state["messages"][-1].tool_calls[0]
    ack = ToolMessage(
        content="project saved",
        name=tool_call["name"],
        tool_call_id=tool_call["id"],
    )

    return {"messages": [ack]}
