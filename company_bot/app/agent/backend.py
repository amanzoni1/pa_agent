import os
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from deepagents.backends.filesystem import FilesystemBackend
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
    - /memories/ -> Read/Write access for the agent's long-term memory
    - /system/ ->  Read/Write access for the AGENTS and skills files
    - Everything else -> Goes to Ephemeral State
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_path = os.path.join(base_dir, "assets")

    return CompositeBackend(
        default=StateBackend(runtime),
        routes={
            "/memories/": StoreBackend(runtime),
            "/system/": FilesystemBackend(root_dir=assets_path, virtual_mode=True),
        }
    )
