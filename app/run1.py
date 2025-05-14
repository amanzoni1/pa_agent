# app/run.py

import uuid
import typer
import asyncio
import signal
import sys
import time
from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore
from app.graph.assistant import GRAPH
from app.mcp import cleanup_mcp, initialize_app_mcp

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = typer.Typer(help="🗣️  Chat CLI for your personal assistant with long-term memory")


def _shutdown(signal_name: str = None):
    """Gracefully clean up MCP connections and exit."""
    typer.secho(
        f"\nReceived {signal_name or 'exit'}, cleaning up MCP…", fg=typer.colors.YELLOW
    )
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(cleanup_mcp())
        loop.close()
    except Exception as e:
        typer.secho(f"Error during MCP cleanup: {e}", fg=typer.colors.RED)
    sys.exit(0)


# register both Ctrl-C and 'kill' termination
signal.signal(signal.SIGINT, lambda *_: _shutdown("SIGINT"))
signal.signal(signal.SIGTERM, lambda *_: _shutdown("SIGTERM"))


@app.command()
def chat(
    user_id: str = typer.Option(
        "default",
        "--user-id",
        "-u",
        help="Namespace key for your saved memories (e.g. your name).",
    ),
    thread_id: str = typer.Option(
        None,
        "--thread-id",
        "-t",
        help="Conversation ID (UUID). If not provided, a new one is generated.",
    ),
):
    """
    Start an interactive chat loop.
    Type /memory to see your saved profile, projects, and instructions.
    Type /exit or Ctrl-D to quit.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    typer.secho(
        f"\n[Memory namespace] user_id={user_id!r}  thread_id={thread_id!r}\n",
        fg=typer.colors.GREEN,
    )

    # Initialize MCP before starting the chat
    try:
        typer.secho(f"Initializing MCP tools...", fg=typer.colors.YELLOW)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        tools = loop.run_until_complete(initialize_app_mcp())
        loop.close()
        typer.secho(f"Loaded {len(tools)} MCP tools", fg=typer.colors.GREEN)

        # Ensure MCP tools are properly loaded in the graph
        # from app.graph.assistant import GRAPH

        # Wait a moment to ensure tools are properly registered
        time.sleep(1)
    except Exception as e:
        typer.secho(f"Error initializing MCP tools: {e}", fg=typer.colors.RED)

    # 1) Chat history and running summary
    history: list[HumanMessage] = []
    summary: str = ""

    # 2) Graph config
    cfg = {"configurable": {"user_id": user_id, "thread_id": thread_id}}

    # 3) Shared store for long-term memory
    store = getattr(GRAPH, "store", InMemoryStore())

    try:
        while True:
            try:
                text = typer.prompt("You")
            except (EOFError, KeyboardInterrupt):
                typer.secho("\nGoodbye!", fg=typer.colors.RED)
                raise typer.Exit()

            lower = text.strip().lower()
            if lower in ("/exit", "/quit"):
                raise typer.Exit()

            if lower == "/memory":
                # PROFILE
                entry = store.get(("profile", user_id), "user_profile")
                typer.secho("=== PROFILE ===", fg=typer.colors.BLUE)
                typer.echo(entry.value if entry and entry.value else "{}")

                # PROJECTS
                projs = store.search(("projects", user_id))
                typer.secho("=== PROJECTS ===", fg=typer.colors.BLUE)
                for p in projs:
                    v = p.value
                    typer.echo(
                        f"- {v['title']} (status: {v.get('status')}, due: {v.get('due_date')})\n"
                        f"    {v.get('description', '')}"
                    )

                # INSTRUCTIONS
                insts = store.search(("instructions", user_id))
                typer.secho("=== INSTRUCTIONS ===", fg=typer.colors.BLUE)
                for inst in insts:
                    typer.echo(f"- {inst.value['content']}")

                typer.secho("=====================\n", fg=typer.colors.BLUE)
                continue

            # Special case for debugging MCP tools
            if lower == "/mcp":
                from app.mcp import MCP

                typer.secho("=== MCP TOOLS ===", fg=typer.colors.BLUE)
                for tool in MCP:
                    typer.echo(f"- {tool.name}: {tool.description}")
                typer.secho("=====================\n", fg=typer.colors.BLUE)
                continue

            # ─── User said something new ────────────────────────────────────────
            history.append(HumanMessage(content=text))

            # ─── Invoke the graph, passing current history + last summary ───────
            payload = {
                "messages": history,
                "summary": summary,
            }

            result = GRAPH.invoke(payload, cfg)

            # ─── Pull updated summary back out (unchanged if no summarization ran)
            summary = result.get("summary", summary)

            # ─── Grab and display the assistant's reply ─────────────────────────
            ai = result["messages"][-1]
            typer.secho(f"AI: {ai.content}\n", fg=typer.colors.CYAN)

            # ─── Append for next turn ───────────────────────────────────────────
            history.append(ai)

    except (EOFError, KeyboardInterrupt):
        pass
    finally:
        _shutdown()


if __name__ == "__main__":
    app()
