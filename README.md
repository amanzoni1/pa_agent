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

###

-sub graph where to make reduction inside a node etc
https://github.com/langchain-ai/langchain-academy/blob/main/module-4/sub-graph.ipynb

####

memories e project si sovrascrivono, quando data controversi sovrascive nome invece di chiedere.
non tutti i data vengono riconosciuti, instructor puo anche chiedere conferma
truncate or summarize current thread
new system prompt completo per react etc, guarda anche logiche
