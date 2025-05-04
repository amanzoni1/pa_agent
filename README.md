app/
├── **init**.py
├── run.py # “python -m app.run” entry-point
├── config.py # environment loading & get_llm()
│
├── schemas/ # all your Pydantic/TypedDict schemas
│ ├── **init**.py
│ ├── profile.py # Profile, UserProfile, UpdateMemory, etc.
│ ├── memory.py # Memory, MemoryCollection, ToDo, etc.
│ └── common.py # any shared types
│
├── tools/ # wrappers around external services or “pure” tools
│ ├── **init**.py
│ ├── search.py
│ └── …
│
├── store/ # your persistence layer(s)
│ ├── **init**.py
│ └── memory_store.py # InMemoryStore (swap‐in Redis later)
│
└── graph/ # your LangGraph nodes & router
├── **init**.py
├── router.py # StateGraph wiring + main “assistant” node
├── profile_node.py # update_user_profile()
└── episodic_node.py # update_memory(), etc.
