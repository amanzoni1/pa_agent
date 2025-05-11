# app/graph/assistant.py

import json
from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.redis import RedisSaver
from langgraph.store.postgres import PostgresStore
from langgraph.store.base import BaseStore
from langgraph.prebuilt import ToolNode

from app.config import REDIS_URI, POSTGRES_URI
from app.config import get_llm
from app.graph.state import ChatState
from app.graph.memory.short_term_memory import summarize_node
from app.schemas.profile_schema import UpdateProfileMemory
from app.schemas.instructions_schema import UpdateInstructionMemory
from app.schemas.project_schema import UpdateProjectMemory
from app.graph.prompts import SYSTEM_PROMPT
from app.graph.memory import MEMORY
from app.tools import TOOLS
from app.rag import RAG


model = get_llm()

# Main Agent node
def assistant_node(
    state: ChatState,
    config: RunnableConfig,
    store: BaseStore,
):
    """
    1) Gather long-term profile from store
    2) Issue the SYSTEM_PROMPT + history to the LLM
    3) Bind the three memory tools, disallow parallel calls
    4) Return the AI’s reply (which may include exactly one tool_call)
    """
    uid = config["configurable"]["user_id"]

    # Load Long-term memories
    prof_entry = store.get(("profile", uid), "user_profile")
    profile = prof_entry.value if prof_entry and prof_entry.value else {}

    inst_entries = store.search(("instructions", uid))
    instructions = [i.value for i in inst_entries]

    proj_entries = store.search(("projects", uid))
    projects = [p.value for p in proj_entries]

    # Format prompt
    prompt = SYSTEM_PROMPT.format(
        profile=json.dumps(profile, indent=2),
        instructions=json.dumps(instructions, indent=2),
        projects=json.dumps(projects, indent=2),
    )

    # Build the system message with prompt ans summarized history
    system_messages = [SystemMessage(content=prompt)]

    if state.get("summary"):
        system_messages.append(
            SystemMessage(
                content=f"Previous conversation (summarized):\n{state.get('summary')}"
            )
        )

    # Give the tools to the Agent
    assistant = model.bind_tools(
        [
            *RAG,
            *TOOLS,
            UpdateProfileMemory,
            UpdateProjectMemory,
            UpdateInstructionMemory,
        ],
        parallel_tool_calls=False,
    )

    # Invoke the Agent with the system message and recent messages
    ai_msg = assistant.invoke(system_messages + state["messages"])

    # print("TOOL CALLS :", ai_msg.tool_calls)
    msg = ai_msg.model_dump(mode="json")

    return {"messages": [msg]}


# Routing
def route_summarize(state, *_):
    return "summarize_conversation" if len(state["messages"]) > 10 else "assistant"

def route_tools(state, *_):
    last = state["messages"][-1]
    calls = getattr(last, "tool_calls", []) or []
    if not calls:
        return END

    name = calls[0]["name"]
    if name in [t.name for t in RAG + TOOLS]:
        return name
    if name == "UpdateProfileMemory":
        return "update_user_profile"
    if name == "UpdateInstructionMemory":
        return "update_instructions"
    if name == "UpdateProjectMemory":
        return "update_projects"
    return END


# Build the StateGraph
builder = StateGraph(ChatState)

# Core chatbot
builder.add_node("assistant", assistant_node)
builder.add_node("summarize_conversation", summarize_node)

# ToolNodes for every tool in TOOLS and RAG
for tool_fn in RAG:
    node_name = tool_fn.name
    builder.add_node(node_name, ToolNode([tool_fn]))
for tool_fn in TOOLS:
    node_name = tool_fn.name
    builder.add_node(node_name, ToolNode([tool_fn]))

# Memory update nodes
for tool_fn in MEMORY:
    node_name = tool_fn.__name__
    builder.add_node(node_name, tool_fn)

# Edges
builder.add_conditional_edges(START, route_summarize)
builder.add_edge("summarize_conversation", "assistant")

builder.add_conditional_edges("assistant", route_tools)
for node_name in [
    *[t.name for t in RAG],
    *[t.name for t in TOOLS],
    "update_user_profile",
    "update_instructions",
    "update_projects",
]:
    builder.add_edge(node_name, "assistant")

# Redis checkpointer
_raw_redis = RedisSaver.from_conn_string(REDIS_URI)
redis_cp = _raw_redis.__enter__()
redis_cp.setup()

# Postgres store
_raw_pg = PostgresStore.from_conn_string(POSTGRES_URI)
pg_store = _raw_pg.__enter__()
pg_store.setup()


GRAPH = builder.compile(
    checkpointer=redis_cp,
    store=pg_store,
)


# Visualize your graph
# with open("chatbot_graph.png", "wb") as f:
#     f.write(GRAPH.get_graph().draw_mermaid_png())
# print("Wrote graph to chatbot_graph.png")
