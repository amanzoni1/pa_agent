# app/graph/nodes/short_term_memory.py

import logging
from datetime import datetime
from typing import Any, Dict

from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore

from app.graph.state import ChatState
from app.config import get_llm

logger = logging.getLogger(__name__)
llm = get_llm()


def summarize_node(
    state: ChatState, config: RunnableConfig, store: BaseStore
) -> Dict[str, Any]:
    """
    Summarize older chat turns into a rolling summary and prune them.
    """
    # Load old summary
    old_summary = state["summary"] or ""

    # Create the prompt
    if old_summary:
        summary_message = f"""
            System time (UTC): {datetime.utcnow().isoformat()}

            You already have this one-paragraph summary of the conversation so far:
            {old_summary}

            Now extend and refine that summary into a single, concise paragraph by incorporating the new messages above.
            • Preserve every point from the existing summary.
            • Seamlessly fold in any new details.
            • Return only the updated summary paragraph—no extra labels or commentary.
            """
    else:
        summary_message = f"""
            System time (UTC): {datetime.utcnow().isoformat()}

            Create a one-paragraph summary of the conversation above that captures all key points, intentions, and actions.
            Return only the summary paragraph—no extra text.
            """

    messages = state["messages"] + [HumanMessage(content=summary_message)]

    # Invoke the LLM with a SystemMessage
    response = llm.invoke(messages)
    new_summary = response.content.strip()

    # Delete all but the 2 most recent messages
    deletes = [RemoveMessage(id=m.id) for m in state["messages"][:-2]]

    # print("summary", new_summary)

    return {"summary": new_summary, "messages": deletes}
