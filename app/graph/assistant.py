# app/graph/assistant.py

from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore

from app.config import get_llm
from app.schemas.profile_schema import UpdateProfileMemory
from app.schemas.memory_schema import UpdateExperienceMemory
from app.schemas.project_schema import UpdateProjectMemory
from app.graph.profile_node import update_user_profile
from app.graph.memories_node import update_memories
from app.graph.projects_node import update_projects
from app.tools import TOOLS


model = get_llm()

SYSTEM_PROMPT = """\
You are a friendly assistant.  Use whatever you already know about the user to personalize your reply:

{profile}

If you learn *new* information, choose **exactly one** action:

1) Core facts → call UpdateProfileMemory(update_type="profile")
2) One-off experience → call UpdateExperienceMemory(update_type="memories")
3) Plan/project → call UpdateProjectMemory(update_type="projects")
4) Otherwise do **not** call any tool.

Now the conversation follows:
"""


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
    existing = store.get(("profile", uid), "user_profile")
    profile = existing.value if existing and existing.value else {}

    prompt = SYSTEM_PROMPT.format(profile=profile)

    assistant = model.bind_tools(
        [UpdateProfileMemory, UpdateExperienceMemory, UpdateProjectMemory],
        parallel_tool_calls=False,
    )

    ai_msg = assistant.invoke([SystemMessage(content=prompt)] + state["messages"])
    print("TOOL CALLS:", ai_msg.tool_calls)
    return {"messages": [ai_msg]}


def route_memory(state, *_):
    """
    Look at the last AI message’s tool_call.  Route to the matching node.
    """
    last = state["messages"][-1]
    calls = getattr(last, "tool_calls", []) or []
    if not calls:
        return END

    t = calls[0]["args"]["update_type"]
    if t == "profile":
        return "update_user_profile"
    if t == "memories":
        return "update_memories"
    if t == "projects":
        return "update_projects"
    return END


# ─── Build the StateGraph ─────────────────────────────────────────
builder = StateGraph(MessagesState)

builder.add_node("assistant", assistant_node)
builder.add_node("update_user_profile", update_user_profile)
builder.add_node("update_memories", update_memories)
builder.add_node("update_projects", update_projects)

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", route_memory)
builder.add_edge("update_user_profile", "assistant")
builder.add_edge("update_memories", "assistant")
builder.add_edge("update_projects", "assistant")

GRAPH = builder.compile(
    checkpointer=MemorySaver(),  # thread-local chat history
    store=InMemoryStore(),  # cross-thread long-term memory
)

# (optional) visualize your graph
# with open("chatbot_graph.png", "wb") as f:
#     f.write(GRAPH.get_graph().draw_mermaid_png())
# print("Wrote graph to chatbot_graph.png")
