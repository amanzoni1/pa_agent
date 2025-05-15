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
from app.mcp import cleanup_mcp


app = typer.Typer(help="🗣️  Chat CLI for your personal assistant with long-term memory")


def _shutdown(signal_name: str = None):
    """Gracefully clean up MCP connections and exit."""
    typer.secho(
        f"\nReceived {signal_name or 'exit'}, cleaning up MCP…", fg=typer.colors.YELLOW
    )
    try:
        # Check if we're already in an event loop
        try:
            loop = asyncio.get_event_loop()
            is_running = loop.is_running()
        except RuntimeError:
            # No event loop in this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            is_running = False

        # Different handling based on whether a loop is already running
        if is_running:
            # If we're in a running event loop, we need to use a different approach
            typer.secho("Using existing event loop for cleanup", fg=typer.colors.YELLOW)
            # Create a Future that we'll use to know when cleanup is done
            cleanup_done = loop.create_future()

            # Schedule the cleanup task
            async def do_cleanup():
                try:
                    await cleanup_mcp()
                    cleanup_done.set_result(None)
                except Exception as e:
                    cleanup_done.set_exception(e)

            asyncio.create_task(do_cleanup())

            # We can't wait for it in this thread, so we'll just continue
            # This is not ideal but better than blocking forever
            typer.secho("Cleanup scheduled, exiting now", fg=typer.colors.YELLOW)
        else:
            # If no loop is running, we can run it to completion
            typer.secho("Running cleanup in new event loop", fg=typer.colors.YELLOW)
            loop.run_until_complete(cleanup_mcp())
            loop.close()
            typer.secho("Cleanup completed", fg=typer.colors.GREEN)
    except Exception as e:
        typer.secho(f"Error during MCP cleanup: {e}", fg=typer.colors.RED)
    finally:
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
                _shutdown("Ctrl+D or Ctrl+C")
                return

            lower = text.strip().lower()
            if lower in ("/exit", "/quit"):
                _shutdown("exit command")
                return

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
        _shutdown("Ctrl+D or Ctrl+C")
    finally:
        # Make sure we call _shutdown only once by removing it from here
        # (it will be called via the exception handlers above)
        pass


if __name__ == "__main__":
    app()
