import typer
from app.graph.router import GRAPH

cli = typer.Typer()


@cli.command()
def chat(user: str = "default"):
    cfg = {"configurable": {"thread_id": "cli", "user_id": user}}
    while True:
        try:
            text = input("You: ")
            chunk = {"messages": [{"type": "human", "content": text}]}
            stream = GRAPH.stream(chunk, cfg, stream_mode="values")
            for step in stream:
                ai_msg = step["messages"][-1]
            print("AI :", ai_msg.content)
        except (EOFError, KeyboardInterrupt):
            break


if __name__ == "__main__":
    cli()
