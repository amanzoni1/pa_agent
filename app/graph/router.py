from langchain_core.messages import SystemMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langchain_core.runnables.config import RunnableConfig
from langgraph.store.base import BaseStore
from app.config import get_llm
from app.schemas.schemas import UpdateMemory
from app.tools import TOOLS
from app.graph.user_profile_node import update_user_profile

model = get_llm()

SYSTEM_PROMPT = """\
You are a friendly assistant.  Use whatever you already know about the user to personalize your reply:

{profile}

Now answer the user below.  If you learn any *new factual* info about them
(e.g. name, location, interests, ongoing projects), *call* the UpdateMemory
tool exactly once with `update_type="profile"`.  Otherwise do NOT call any tool.
"""


def assistant_node(
    state: MessagesState,
    config: RunnableConfig,
    store: BaseStore,
):
    # 1) load existing profile
    uid = config["configurable"]["user_id"]
    existing = store.get(("profile", uid), "user_profile")
    profile = existing.value if existing and existing.value else {}

    # 2) assemble system prompt
    prompt = SYSTEM_PROMPT.format(profile=profile)

    # 3) bind ALL your tools (memory + TOOLS) and let the model pick
    assistant = model.bind_tools(
        [UpdateMemory] + TOOLS, tool_choice="auto"
    )

    # 4) invoke with system + chat history
    ai_msg = assistant.invoke([SystemMessage(content=prompt)] + state["messages"])

    return {"messages": [ai_msg]}


def route_memory(state, *_):
    # if the assistant called our UpdateMemory tool → patch the profile
    last = state["messages"][-1]
    return "update_user_profile" if getattr(last, "tool_calls", None) else END


# ─── build the graph ─────────────────────────────────────────────

builder = StateGraph(MessagesState)

builder.add_node("assistant", assistant_node)
builder.add_node("update_user_profile", update_user_profile)

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", route_memory)
builder.add_edge("update_user_profile", "assistant")

GRAPH = builder.compile(
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
)
