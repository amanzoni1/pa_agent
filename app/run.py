# app/run.py

import uuid
import typer
from langchain_core.messages import HumanMessage
from langgraph.store.memory import InMemoryStore
from app.graph.assistant import GRAPH

app = typer.Typer(help="🗣️  Chat CLI for your personal assistant with long-term memory")


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

        # ─── Grab and display the assistant’s reply ─────────────────────────
        ai = result["messages"][-1]
        typer.secho(f"AI: {ai.content}\n", fg=typer.colors.CYAN)

        # ─── Append for next turn ───────────────────────────────────────────
        history.append(ai)


if __name__ == "__main__":
    app()
