# app/graph/profile_node.py

import uuid
from datetime import datetime
from trustcall import create_extractor
from langchain_core.messages import SystemMessage
from langgraph.store.base import BaseStore
from langgraph.graph import MessagesState
from app.config import get_llm
from app.schemas import UserProfile

# ─── Initialize LLM & Trustcall extractor ─────────────────────────────────────

model = get_llm()

user_profile_extractor = create_extractor(
    model,
    tools=[UserProfile],
    tool_choice="UserProfile",
    enable_inserts=True,  # allow appending to list fields
)


# ─── Node: update_user_profile ────────────────────────────────────────────────


def update_user_profile(
    state: MessagesState,
    config,
    store: BaseStore,
):
    """
    Use Trustcall to patch or insert into the UserProfile JSON.
    - Reads the current UserProfile from the store (if any).
    - Prompts the model to update only changed fields based on the latest conversation.
    - Persists each patch or new document back to the same namespace.
    """

    # 1. Build namespace/key
    uid = config["configurable"]["user_id"]
    namespace = ("profile", uid)
    key = "user_profile"

    # 2. Retrieve existing profile (if any)
    existing_entry = store.get(namespace, key)
    existing_json = existing_entry.value if existing_entry else {}

    # 3. Construct a detailed system prompt
    system_content = (
        f"System time (UTC): {datetime.utcnow().isoformat()}\n\n"
        "You are the memory manager for a single user profile.  "
        "Maintain a JSON document capturing everything we know about this user.  "
        "The JSON schema is:\n\n"
        f"{UserProfile.schema_json(indent=2)}\n\n"
        "Here is the current profile JSON (may be empty):\n"
        f"{existing_json}\n\n"
        "Below is the most recent conversation.  "
        "Update the JSON with any _new_ facts or corrections you see.  "
        "Return only the JSON document (either full or as patches), conforming EXACTLY to the schema."
    )
    messages = [SystemMessage(content=system_content)] + state["messages"]

    # 4. Invoke Trustcall extractor
    result = user_profile_extractor.invoke(
        {
            "messages": messages,
            "existing": {"UserProfile": existing_json} if existing_json else None,
        }
    )

    # 5. Persist each response (full doc or patch)
    for resp, meta in zip(result["responses"], result["response_metadata"]):
        doc_id = meta.get("json_doc_id", str(uuid.uuid4()))
        store.put(namespace, doc_id, resp.model_dump())

    # 6. Signal the router that we’ve updated memory
    last_tool_call = state["messages"][-1].tool_calls[0]
    return {
        "messages": [
            {
                "role": "tool",
                "content": "user profile updated",
                "tool_call_id": last_tool_call["id"],
            }
        ]
    }
