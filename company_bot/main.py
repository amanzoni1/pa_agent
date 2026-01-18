import sys
import asyncio
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

# Import langchain/deepagents types for type checking
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

# Your existing imports
from app.agent.graph import build_agent

# 1. Load Environment
load_dotenv(".env")
console = Console()

# 2. The Display Manager (Handles the UI logic)
class AgentDisplay:
    def __init__(self):
        self.printed_count = 0
        self.spinner = Spinner("dots", text="Thinking...", style="yellow")

    def update_status(self, text, style="yellow"):
        self.spinner = Spinner("dots", text=text, style=style)

    def print_message(self, msg):
        """Render a message based on its type."""

        # --- CASE A: AI Message (The Bot Speaking or Using Tools) ---
        if isinstance(msg, AIMessage):
            # 1. Print Text Content (The Answer)
            content = msg.content
            if isinstance(content, list): # Handle complex content blocks
                content = "".join([c["text"] for c in content if "text" in c])

            if content and content.strip():
                console.print(Panel(Markdown(content), title="[bold green]Company Bot[/]", border_style="green"))

            # 2. Print Tool Calls (The Thinking)
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    name = tc.get("name")
                    args = tc.get("args", {})

                    # CUSTOM VISUALS FOR YOUR TOOLS
                    if name == "internet_search":
                        query = args.get("query", "...")
                        console.print(f"  [bold cyan]🌍 Searching Web:[/bold cyan] [dim]{query}[/dim]")
                        self.update_status("Searching external sources...", style="cyan")

                    elif name == "read_file":
                        path = args.get("file_path", "...")
                        console.print(f"  [bold magenta]🧠 Accessing Memory:[/bold magenta] [dim]{path}[/dim]")
                        self.update_status("Reading long-term memory...", style="magenta")

                    elif name == "write_file":
                        path = args.get("file_path", "...")
                        console.print(f"  [bold yellow]💾 Saving Memory:[/bold yellow] [dim]{path}[/dim]")
                        self.update_status("Updating user profile...", style="yellow")

                    else:
                        console.print(f"  [bold blue]🔧 Tool Call:[/bold blue] {name}")

        # --- CASE B: Tool Result (The Output) ---
        elif isinstance(msg, ToolMessage):
            name = getattr(msg, "name", "unknown")
            # Keep tool outputs concise to avoid clutter
            if name == "internet_search":
                 console.print(f"  [green]✓ Found search results[/green]")
            elif "file" in name:
                 console.print(f"  [green]✓ Memory updated[/green]")
            else:
                 console.print(f"  [green]✓ Tool finished[/green]")

# 3. The Async Chat Loop
async def main():
    agent = build_agent(provider="openai")

    # Guest Session
    thread_id = "guest_session_rich_ui"
    config = {"configurable": {"thread_id": thread_id}}

    # Welcome Header
    console.print(Panel.fit(
        "[bold white]Company Support Bot[/bold white]",
        style="blue"
    ))
    console.print("[dim]Type 'q' to quit.[/dim]\n")

    while True:
        try:
            # Standard input (rich.console.input allows colors in prompt)
            user_input = console.input("[bold blue]You:[/bold blue] ")
            if user_input.lower() in ['q', 'quit']:
                console.print("[yellow]Goodbye![/yellow]")
                break

            display = AgentDisplay()

            # Live Spinner + Async Streaming
            with Live(display.spinner, console=console, refresh_per_second=10, transient=True) as live:

                # We use stream_mode="values" to get the full list of messages as they grow
                async for chunk in agent.astream(
                    {"messages": [("user", user_input)]},
                    config=config,
                    stream_mode="values"
                ):
                    if "messages" in chunk:
                        messages = chunk["messages"]

                        # Only print the NEW messages we haven't seen yet
                        if len(messages) > display.printed_count:
                            live.stop() # Pause spinner to print clearly

                            for msg in messages[display.printed_count:]:
                                display.print_message(msg)

                            display.printed_count = len(messages)

                            live.start() # Resume spinner
                            live.update(display.spinner)

        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")

if __name__ == "__main__":
    asyncio.run(main())
