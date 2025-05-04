# app/run.py

import uuid, typer
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
    Type /memory to see your saved profile, memories, projects, and instructions.
    Type /exit or Ctrl-D to quit.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    typer.secho(
        f"\n[Memory namespace] user_id={user_id!r}  thread_id={thread_id!r}\n",
        fg=typer.colors.GREEN,
    )

    # your chat history
    history: list[HumanMessage] = []

    # config for Graph
    cfg = {"configurable": {"user_id": user_id, "thread_id": thread_id}}

    # reuse the same store the graph was compiled with, if any
    store = getattr(GRAPH, "store", InMemoryStore())

    while True:
        try:
            text = typer.prompt("You")
        except (EOFError, KeyboardInterrupt):
            typer.secho("\nGoodbye!", fg=typer.colors.RED)
            raise typer.Exit()

        cmd = text.strip().lower()
        if cmd in ("/exit", "/quit"):
            raise typer.Exit()

        if cmd == "/memory":
            # profile
            prof = store.get(("profile", user_id), "user_profile")
            typer.secho("=== PROFILE ===", fg=typer.colors.BLUE)
            typer.echo(prof.value or "{}")

            # experiences
            exps = store.search(("memories", user_id))
            typer.secho("=== MEMORIES ===", fg=typer.colors.BLUE)
            for m in exps:
                typer.echo(f"- {m.value['content']}")

            # projects
            projs = store.search(("projects", user_id))
            typer.secho("=== PROJECTS ===", fg=typer.colors.BLUE)
            for p in projs:
                typer.echo(f"- {p.value['title']}: {p.value['description']}")

            typer.secho("=====================\n", fg=typer.colors.BLUE)
            continue

        # 1) add user message
        history.append(HumanMessage(content=text))

        # 2) run through the graph
        result = GRAPH.invoke({"messages": history}, cfg)
        ai = result["messages"][-1]

        # 3) print AI reply
        typer.secho(f"AI: {ai.content}\n", fg=typer.colors.CYAN)

        # 4) append for next turn
        history.append(ai)


if __name__ == "__main__":
    app()
