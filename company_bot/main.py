import os
import sys
from dotenv import load_dotenv
from app.agent.graph import build_agent

# 1. Load Environment Variables
# Since main.py is in root, we just load .env directly
load_dotenv(".env")

# 2. Build the Agent
# We default to 'openai', but you can change to 'fireworks' in config.py
agent = build_agent(provider="openai")

# 3. Setup Session
thread_id = "user_123"
config = {"configurable": {"thread_id": thread_id}}

def chat_loop():
    print(f"--- Chatting as Thread: {thread_id} ---")
    print("Commands: 'q' to quit, 'model <name>' to switch model")

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ['q', 'quit']: break

            # Invoke Agent
            response = agent.invoke(
                {"messages": [("user", user_input)]},
                config=config
            )

            # Get last message
            print(f"Bot: {response['messages'][-1].content}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Pre-seed memory to test persistence
    # This creates the file in the virtual store (/memories/)
    print("--- Seeding Memory ---")
    agent.invoke({
        "messages": [("user", "My name is Andrea. Save this to /memories/user_profile.md")]
    }, config=config)

    chat_loop()
