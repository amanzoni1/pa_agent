import asyncio
import argparse
import logging
import warnings
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

from langchain_core.messages import AIMessage, ToolMessage
from app.agent.graph import build_agent

# Suppress noisy logs
warnings.simplefilter("ignore", ResourceWarning)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# 1. Setup
load_dotenv(".env")
console = Console()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Run the Company Bot CLI")
    parser.add_argument(
        "--model", "-m",
        type=str,
        default="openai",
        help="Model Config: Use a shortcut ('openai', 'fast') OR a prefix ('fw-..., 'oa-..., 'ant-...')"
    )
    return parser.parse_args()

def extract_thinking(msg: AIMessage):
    """
    Extracts reasoning/thinking content from various model formats.
    Returns a tuple of (thought, content).
    """
    content = msg.content or ""
    # Standard reasoning field (Fireworks/DeepSeek)
    thought = msg.additional_kwargs.get("reasoning_content", "")

    # Tag-based reasoning (Qwen/DeepSeek-R1 Distill style)
    if not thought and "<think>" in str(content):
        try:
            parts = str(content).split("</think>")
            thought = parts[0].replace("<think>", "").strip()
            content = parts[1].strip()
        except:
            pass
    return thought, content

async def main():
    args = parse_arguments()
    agent = build_agent(provider=args.model)

    # Dashboard Session
    thread_id = "dashboard_session_final_v3"
    config = {"configurable": {"thread_id": thread_id}}

    # Header
    console.print(Panel.fit(
        f"[bold white]Company Bot CLI[/]\n[dim]Model: {args.model}[/dim]",
        style="blue"
    ))

    while True:
        try:
            # --- INPUT ---
            user_input = console.input("\n[bold green]User > [/]")
            if user_input.lower() in ['q', 'quit']: break

            # --- PRE-CALCULATE OFFSET ---
            initial_state = await agent.aget_state(config)
            start_len = len(initial_state.values.get("messages", []))

            # --- STREAMING EXECUTION ---
            current_len = start_len
            spinner = Spinner("dots", text="[dim]Agent is thinking...[/dim]", style="yellow")

            with Live(spinner, console=console, refresh_per_second=10, transient=True) as live:

                async for chunk in agent.astream(
                    {"messages": [("user", user_input)]},
                    config=config,
                    stream_mode="values"
                ):
                    if "messages" in chunk:
                        messages = chunk["messages"]

                        if len(messages) > current_len:
                            live.stop()

                            for msg in messages[current_len:]:

                                # 1. Visualize Tool Calls (Reasoning + Action)
                                if isinstance(msg, AIMessage) and msg.tool_calls:
                                    thought, _ = extract_thinking(msg)
                                    if thought:
                                        console.print(Panel(Markdown(thought), title="[italic dim]Thinking...[/italic dim]", border_style="dim cyan", style="dim"))
                                    elif msg.content:
                                        console.print(f"[dim italic]{msg.content}[/dim italic]")

                                    for tc in msg.tool_calls:
                                        name = tc['name']
                                        t_args = tc['args']

                                        if name in ["read_file", "write_file", "edit_file"]:
                                            action = "Reading Memory" if name == "read_file" else "Updating Memory"
                                            path = t_args.get('file_path', '...')
                                            console.print(f"[bold magenta]🧠 {action}:[/bold magenta] [dim]{path}[/dim]")
                                        else:
                                            details = t_args.get('query') or str(t_args)[:60]
                                            console.print(f"[bold yellow]🛠️  Tool Call ({name}):[/bold yellow] [dim]{details}[/dim]")

                                # 2. Visualize Tool Outputs
                                elif isinstance(msg, ToolMessage):
                                    status = "Error" if "error" in msg.content.lower() else "Success"
                                    color = "magenta" if "file" in msg.name else "bold yellow"
                                    console.print(f"   [dim {color}]↳ {status}: {msg.name}[/dim {color}]")

                                # 3. Visualize Final Answer
                                elif isinstance(msg, AIMessage) and not msg.tool_calls:
                                    thought, answer = extract_thinking(msg)

                                    if thought:
                                        console.print(Panel(Markdown(thought), title="[italic dim]Brain[/italic dim]", border_style="dim white", style="dim"))

                                    if answer:
                                        console.print(Panel(Markdown(answer), title="Bot", border_style="green"))

                                    usage = msg.response_metadata.get("token_usage")
                                    if usage:
                                        total = usage.get('total_tokens')
                                        prompt = usage.get('prompt_tokens')
                                        completion = usage.get('completion_tokens')
                                        console.print(f"[dim right]Tokens: {total} (In: {prompt}, Out: {completion})[/dim right]")

                            current_len = len(messages)
                            live.start()

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
