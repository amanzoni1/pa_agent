# app/run.py

import uuid
import typer
import asyncio
import signal
import sys
from langchain_core.messages import HumanMessage
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
    Type `/memory` to view stored profile, projects, and instructions.
    Type `/mcp` to list MCP tools.
    Type `/exit` or Ctrl-D to quit.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    typer.secho(
        f"\n[Memory namespace] user_id={user_id!r}  thread_id={thread_id!r}\n",
        fg=typer.colors.GREEN,
    )

    cfg = {"configurable": {"user_id": user_id, "thread_id": thread_id}}
    store = GRAPH.store

    try:
        while True:
            try:
                text = typer.prompt("You")
            except (EOFError, KeyboardInterrupt):
                _shutdown("Ctrl+D or Ctrl+C")
                return

            cmd = text.strip().lower()
            if cmd in ("/exit", "/quit"):
                _shutdown("exit command")
                return

            # View memory status
            if cmd == "/memory":
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

            # View MCP available
            if cmd == "/mcp":
                from app.mcp import MCP

                typer.secho("=== MCP TOOLS ===", fg=typer.colors.BLUE)
                for tool in MCP:
                    typer.echo(f"- {tool.name}: {tool.description}")
                typer.secho("=====================\n", fg=typer.colors.BLUE)
                continue

            # Invoke the graph
            payload = {
                "messages": [HumanMessage(content=text)],
                "summary": "",
            }
            result = GRAPH.invoke(payload, cfg)

            ai = result["messages"][-1]
            typer.secho(f"AI: {ai.content}\n", fg=typer.colors.CYAN)

    except (EOFError, KeyboardInterrupt):
        _shutdown("Ctrl+D or Ctrl+C")


if __name__ == "__main__":
    app()
