# app/graph/assistant.py

from langchain_core.messages import SystemMessage
from langchain_core.runnables.config import RunnableConfig
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.store.base import BaseStore
from langgraph.prebuilt import ToolNode

from app.config import get_llm
from app.schemas.profile_schema import UpdateProfileMemory
from app.schemas.memory_schema import UpdateExperienceMemory
from app.schemas.project_schema import UpdateProjectMemory
from app.graph.profile_node import update_user_profile
from app.graph.memories_node import update_memories
from app.graph.projects_node import update_projects
from app.tools import TOOLS
from app.rag import RAG


model = get_llm()

SYSTEM_PROMPT = """\
You are a deeply thoughtful, friendly assistant.  Always think step-by-step before acting, and if you ever need more information, ask a clear follow-up question.

Use what you know about the user to personalize replies:

{profile}

**Memory tools** (use at most one per turn):
  1. Core profile → `UpdateProfileMemory(update_type="profile")`
  2. Past experience → `UpdateExperienceMemory(update_type="memories")`
  3. Projects       → `UpdateProjectMemory(update_type="projects")`

**General tools**:
  • Web:
    - `tavily_search(query, max_results=3)`
    - `wiki_search(query, max_pages=2, summarize=True|False)`
    - `web_fetch(url, max_pages=1)`
  • Documents:
    - `handle_pdf(path_or_url, mode='single'|'page')`
    - `handle_csv(path_or_url, mode='inspect'|'docs'|'html', max_rows=…)`
    - `excel_inspect(excel_path, sheet_name=None, max_rows=5)`
  • File I/O:
    - `decode_and_save_file(filename, content_b64)`
    - `file_download(url, dest_path=None)`
    - `read_file(path)`
  • Directory:
    - `list_dir(path, pattern="**/*")`
    - `handle_directory(path, mode='list'|'text')`
  • Images:
    - `extract_text_from_image(image_path)`
  • RAG / Pinecone:
    - `index_pdf(name, url)`
    - `query_index(name, question, k=5)`

**Clarifications**
- If given a PDF but no `mode`, ask:
  “Would you like `mode='single'` (all text) or `mode='page'` (page splits)?”
- If asked to index but no `name`, **never** guess the `name` argument, ask:
  “What Pinecone index name should I use?”

**When you reply**
- If you call a tool, think through *why* and *what* tool will achieve.
- If a required argument is missing, ask the user for it rather than guessing.
- Otherwise, do **not** call any tool.

Now the conversation begins:
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
        [
            UpdateProfileMemory,
            UpdateExperienceMemory,
            UpdateProjectMemory,
            *RAG,
            *TOOLS,
        ],
        parallel_tool_calls=False,
    )

    ai_msg = assistant.invoke([SystemMessage(content=prompt)] + state["messages"])
    ###
    print("TOOL CALLS:", ai_msg.tool_calls)
    ###
    return {"messages": [ai_msg]}
    # return {"messages": state["messages"] + [ai_msg]}


def route_tools(state, *_):
    last = state["messages"][-1]
    calls = getattr(last, "tool_calls", []) or []
    if not calls:
        return END

    name = calls[0]["name"]
    if name == "UpdateProfileMemory":
        return "update_user_profile"
    if name == "UpdateExperienceMemory":
        return "update_memories"
    if name == "UpdateProjectMemory":
        return "update_projects"
    if name in [t.name for t in TOOLS + RAG]:
        return name
    return END


# ─── Build the StateGraph ─────────────────────────────────────────
builder = StateGraph(MessagesState)

# Core chatbot
builder.add_node("assistant", assistant_node)

# Memory update nodes
builder.add_node("update_user_profile", update_user_profile)
builder.add_node("update_memories", update_memories)
builder.add_node("update_projects", update_projects)

# ToolNodes for every tool in TOOLS and RAG
for tool_fn in TOOLS:
    node_name = tool_fn.name
    builder.add_node(node_name, ToolNode([tool_fn]))
for tool_fn in RAG:
    node_name = tool_fn.name
    builder.add_node(node_name, ToolNode([tool_fn]))

builder.add_edge(START, "assistant")
builder.add_conditional_edges("assistant", route_tools)
for node_name in [
    "update_user_profile",
    "update_memories",
    "update_projects",
    *[t.name for t in TOOLS],
    *[t.name for t in RAG],
]:
    builder.add_edge(node_name, "assistant")

GRAPH = builder.compile(
    checkpointer=MemorySaver(),
    store=InMemoryStore(),
)

# # (optional) visualize your graph
# with open("chatbot_graph.png", "wb") as f:
#     f.write(GRAPH.get_graph().draw_mermaid_png())
# print("Wrote graph to chatbot_graph.png")
