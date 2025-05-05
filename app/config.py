import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-west1-gcp")

def get_llm():
    """Single shared ChatOpenAI client for both chat and extraction."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=MODEL_NAME, temperature=TEMPERATURE)
