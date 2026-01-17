# agents/deep_agent/main.py
import uuid
from dotenv import load_dotenv
from agent import build_agent

# Load env vars from root
load_dotenv("../../.env")

# Build agent with OpenAI (or change to 'fireworks')
agent = build_agent(provider="openai")

# Simulate a user with a specific ID
thread_id = "user_123"
config = {"configurable": {"thread_id": thread_id}}

def chat_loop():
    print(f"--- Chatting as Thread: {thread_id} ---")
    print("Commands: 'q' to quit, 'model <name>' to switch model")

    while True:
        user_input = input("\nUser: ")
        if user_input.lower() == 'q': break

        # Invoke Agent
        response = agent.invoke(
            {"messages": [("user", user_input)]},
            config=config
        )

        # Get last message
        print(f"Bot: {response['messages'][-1].content}")

if __name__ == "__main__":
    # Pre-seed memory to test the /memories/ feature
    print("--- seeding memory ---")
    agent.invoke({
        "messages": [("user", "My name is Andrea. Save this to /memories/user_profile.md")]
    }, config=config)

    chat_loop()
