import os
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
# In production, swap InMemoryStore with PostgresStore
# from langgraph.store.postgres import PostgresStore

from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

def get_checkpointer():
    """Short-term thread state (Pause/Resume)"""
    # For now using MemorySaver, later you swap this for RedisSaver
    return MemorySaver()

def get_store():
    """Long-term database storage"""
    # This stores the actual files that live in /memories/
    return InMemoryStore()

def make_backend(runtime):
    """
    The Router:
    - /memories/ -> Goes to Long-term Store
    - Everything else -> Goes to Ephemeral State
    """
    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime)
        }
    )
