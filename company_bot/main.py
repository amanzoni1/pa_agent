import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

# Imports for Type Checking
from langchain_core.messages import AIMessage, ToolMessage

# Your Imports
from app.agent.graph import build_agent

# 1. Setup
load_dotenv(".env")
console = Console()

async def main():
    agent = build_agent(provider="openai")

    # Dashboard Session
    thread_id = "dashboard_session_final_v2"
    config = {"configurable": {"thread_id": thread_id}}

    # Header
    console.print(Panel.fit("[bold white]Company Bot CLI[/]", style="blue"))

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

            # Simple spinner
            spinner = Spinner("dots", text="[dim]Agent is thinking...[/dim]", style="yellow")

            with Live(spinner, console=console, refresh_per_second=10, transient=True) as live:

                async for chunk in agent.astream(
                    {"messages": [("user", user_input)]},
                    config=config,
                    stream_mode="values"
                ):
                    if "messages" in chunk:
                        messages = chunk["messages"]

                        # Only process NEW messages
                        if len(messages) > current_len:
                            live.stop() # Pause spinner

                            for msg in messages[current_len:]:

                                # 1. Visualize Tool Calls (Reasoning)
                                if isinstance(msg, AIMessage) and msg.tool_calls:

                                    # Print "Chain of Thought" text if present
                                    if msg.content:
                                        console.print(f"[dim italic]{msg.content}[/dim italic]")

                                    for tc in msg.tool_calls:
                                        name = tc['name']
                                        args = tc['args']

                                        # --- COLOR LOGIC ---

                                        # GROUP A: Memory (Magenta)
                                        if name in ["read_file", "write_file", "edit_file"]:
                                            action = "Reading Memory" if name == "read_file" else "Updating Memory"
                                            path = args.get('file_path', '...')
                                            console.print(f"[bold magenta]🧠 {action}:[/bold magenta] [dim]{path}[/dim]")

                                        # GROUP B: General Tools (Cyan)
                                        else:
                                            # Try to find a readable argument (query, url, etc.)
                                            details = args.get('query') or str(args)[:60]
                                            console.print(f"[bold yellow]🛠️  Tool Call ({name}):[/bold yellow] [dim]{details}[/dim]")

                                # 2. Visualize Tool Outputs (Result)
                                elif isinstance(msg, ToolMessage):
                                    status = "Error" if "error" in msg.content.lower() else "Success"

                                    # Match color to the tool type
                                    # If name implies memory, use magenta, else yellow
                                    if "file" in msg.name:
                                        color = "magenta"
                                    else:
                                        color = "bold yellow"

                                    console.print(f"   [dim {color}]↳ {status}: {msg.name}[/dim {color}]")

                                # 3. Visualize Final Answer
                                elif isinstance(msg, AIMessage) and not msg.tool_calls:
                                    console.print(Panel(Markdown(msg.content), title="Bot", border_style="green"))

                                    # Detailed Token Metrics
                                    usage = msg.response_metadata.get("token_usage")
                                    if usage:
                                        total = usage.get('total_tokens')
                                        prompt = usage.get('prompt_tokens')
                                        completion = usage.get('completion_tokens')
                                        console.print(f"[dim right]Tokens: {total} (In: {prompt}, Out: {completion})[/dim right]")

                            current_len = len(messages)
                            live.start() # Resume spinner

        except KeyboardInterrupt:
            console.print("\n[yellow]Goodbye![/yellow]")
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
