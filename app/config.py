# app/config.py

import logging, os, time
from typing import Any, Callable, Type
from functools import wraps

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import openai
from openai import APIConnectionError, APITimeoutError, RateLimitError

load_dotenv()

REDIS_URI = os.getenv("REDIS_URI", "redis://localhost:6379")
POSTGRES_URI = os.getenv(
    "POSTGRES_URI",
    "postgresql://postgres:postgres@localhost:5432/postgres?sslmode=disable",
)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
RAG_MODEL = os.getenv("RAG_MODEL", "gpt-4o")
TEMPERATURE = float(os.getenv("TEMPERATURE", 0.0))

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east1-aws")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
COINMARKETCAP_API_KEY = os.getenv("COINMARKETCAP_API_KEY")

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# retry decorator
ServiceUnavailableError = getattr(openai, "ServiceUnavailableError", openai.APIError)
TRANSIENT_EXC: tuple[Type[Exception], ...] = (
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    ServiceUnavailableError,
)

def retry(tries: int = 4, delay: float = 1.0, backoff: float = 2.0):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries:
                try:
                    return func(*args, **kwargs)
                except TRANSIENT_EXC as exc:
                    _tries -= 1
                    if not _tries:
                        raise
                    logger.warning(
                        "%s failed (%s). Retrying in %.1fs …",
                        func.__name__,
                        exc,
                        _delay,
                    )
                    time.sleep(_delay)
                    _delay *= backoff

        return wrapper

    return decorator


# LLM subclasses with built‑in retry
class RetriableChat(ChatOpenAI):
    @retry()
    def invoke(self, *args, **kwargs):
        return super().invoke(*args, **kwargs)


# Chat/orchestration model
_chat_llm = RetriableChat(
    api_key=OPENAI_API_KEY,
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    request_timeout=60,
    max_retries=0,
)

# RAG combine‑chain model
_rag_llm = RetriableChat(
    api_key=OPENAI_API_KEY,
    model=RAG_MODEL,
    temperature=0,
    request_timeout=60,
    max_retries=0,
)


# LLM getters
def get_llm() -> ChatOpenAI:
    """Chat / orchestration LLM (MODEL_NAME)."""
    return _chat_llm


def get_rag_llm() -> ChatOpenAI:
    """High‑quality RAG LLM (RAG_MODEL)."""
    return _rag_llm
