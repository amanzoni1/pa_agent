import asyncio
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage


async def main():
    client = get_client(url="http://localhost:8123")

    # Create a fresh thread
    thread = await client.threads.create()
    print("Thread ID:", thread["thread_id"])

    cfg = {
        "configurable": {
            "user_id": thread["thread_id"],
            "thread_id": thread["thread_id"],
        }
    }

    # Dispatch "Hello!" to your assistant
    run = await client.runs.create(
        thread["thread_id"],
        "my-assistant",
        input={"messages": [HumanMessage(content="Hello!")]},
        config=cfg,
    )
    print("Run dispatched:", run["run_id"], "-", run["status"])

    # Block until it finishes
    final_state = await client.runs.join(thread["thread_id"], run["run_id"])

    # Pick out the last AI message (safer if your graph ever emits tools too)
    ai_messages = [
        msg for msg in final_state.get("messages", []) if msg.get("type") == "ai"
    ]
    if not ai_messages:
        print("⚠️  No AI message found in:\n", final_state)
        return

    print("AI replied:", ai_messages[-1]["content"])


if __name__ == "__main__":
    asyncio.run(main())
