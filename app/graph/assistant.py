# app/graph/assistant.py

import json
from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.prebuilt import ToolNode

from app.config import get_llm
from app.schemas.profile_schema import UpdateProfileMemory
from app.schemas.instructions_schema import UpdateInstructionMemory
from app.schemas.project_schema import UpdateProjectMemory
from app.graph.prompts import SYSTEM_PROMPT
from app.graph.memory import MEMORY
from app.tools import TOOLS
from app.rag import RAG


model = get_llm()


def assistant_node(
    state: MessagesState,
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

    # Load profile
    prof_entry = store.get(("profile", uid), "user_profile")
    profile = prof_entry.value if prof_entry and prof_entry.value else {}

    # Load memories list
    inst_entries = store.search(("instructions", uid))
    instructions = [i.value for i in inst_entries]

    # Load projects list
    proj_entries = store.search(("projects", uid))
    projects = [p.value for p in proj_entries]

    # Format prompt
    prompt = SYSTEM_PROMPT.format(
        profile=json.dumps(profile, indent=2),
        instructions=json.dumps(instructions, indent=2),
        projects=json.dumps(projects, indent=2),
    )

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

    ai_msg = assistant.invoke([SystemMessage(content=prompt)] + state["messages"])
    ###
    print("TOOL CALLS:", ai_msg.tool_calls)
    ###
    return {"messages": [ai_msg]}


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


# ─── Build the StateGraph ─────────────────────────────────────────
builder = StateGraph(MessagesState)

# Core chatbot
builder.add_node("assistant", assistant_node)

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
builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", route_tools)
for node_name in [
    *[t.name for t in RAG],
    *[t.name for t in TOOLS],
    "update_user_profile",
    "update_instructions",
    "update_projects",
]:
    builder.add_edge(node_name, "assistant")

GRAPH = builder.compile(
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
)

# Visualize your graph
# with open("chatbot_graph.png", "wb") as f:
#     f.write(GRAPH.get_graph().draw_mermaid_png())
# print("Wrote graph to chatbot_graph.png")
