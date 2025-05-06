# app/config.py

import logging
import os
import time
from functools import wraps
from typing import Any, Callable, Type

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import openai
from openai import APIConnectionError, Timeout, RateLimitError


# ──────────────────────────────────────────────────────────────────────────────
# Environment
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()

OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-3.5-turbo")
TEMPERATURE: float = float(os.getenv("TEMPERATURE", 0.0))

# Pinecone
PINECONE_API_KEY: str | None = os.getenv("PINECONE_API_KEY")
PINECONE_ENV: str = os.getenv("PINECONE_ENV", "us-west1-gcp")

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ──────────────────────────────────────────────────────────────────────────────
# Retry decorator for transient OpenAI errors
# ──────────────────────────────────────────────────────────────────────────────
ServiceUnavailableError = getattr(openai, "ServiceUnavailableError", openai.APIError)
TRANSIENT_EXC: tuple[Type[Exception], ...] = (
    APIConnectionError,
    Timeout,
    RateLimitError,
    ServiceUnavailableError,
)


def retry(
    tries: int = 4,
    delay: float = 1.0,
    backoff: float = 2.0,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Simple exponential‑back‑off retry decorator."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args, **kwargs):
            _tries, _delay = tries, delay
            while _tries > 0:
                try:
                    return func(*args, **kwargs)
                except TRANSIENT_EXC as exc:
                    _tries -= 1
                    if _tries == 0:
                        raise  # bubble up after final attempt
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


# ──────────────────────────────────────────────────────────────────────────────
# LLM factory
# ──────────────────────────────────────────────────────────────────────────────
class RetriableChat(ChatOpenAI):
    @retry(tries=4, delay=1, backoff=2)
    def invoke(self, *args, **kwargs):
        return super().invoke(*args, **kwargs)


_llm = RetriableChat(
    api_key=OPENAI_API_KEY,
    model=MODEL_NAME,
    temperature=TEMPERATURE,
    request_timeout=60,
    max_retries=0,
)


def get_llm() -> ChatOpenAI:
    """Return the shared ChatOpenAI instance with built‑in retries."""
    return _llm
