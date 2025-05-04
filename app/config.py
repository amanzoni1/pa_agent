import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))


def get_llm():
    """Single shared ChatOpenAI client for both chat and extraction."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
