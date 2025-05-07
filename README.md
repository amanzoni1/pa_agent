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

check bootstrap in deployment
index multi format in rag
adj actuals tools, remove or improve superflous data, add calendar and mail
struttura nodi consequenziali e prompt inside per logic
memories e project si sovrascrivono, quando data controversi sovrascive nome invece di chiedere.
non tutti i data vengono riconosciuti, instructor puo anche chiedere conferma
truncate or summarize current thread
new system prompt completo per react etc, guarda anche logiche

####

    1.	How many major components does the transformer architecture have?
    2.	What is the role of self‑attention (multi‑head attention) in a transformer?
    3.	In left‑to‑right language modelling, what do we condition each token prediction on?
    4.	Which two mechanisms precede and follow the column of transformer blocks?(Name both the “input encoding component” and the “language modelling head.”)
    5. Roughly how many stacked transformer blocks might a single column contain?
    6. What two types of language models are introduced in later chapters besides causal models? 7. Why can’t a static embedding fully capture the meaning of the word “it” in example (9.1)?
    8. In example (9.3), what uncertainty does the model face when predicting after the word “it”?
    9. Which two nouns receive high attention weights when computing the representation of “it” in Fig. 9.2?
    10. What do we call the richer word representations built by integrating information from surrounding tokens?
    11. What grammatical constraint links the words “keys” and “are” in example (9.4)?
    12. According to the text, what is the purpose of the unembedding matrix U in the language‑model head?

# Remote Markdown

index_docs("kb", "https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md")

# Remote CSV

index_docs("kb", "https://people.sc.fsu.edu/~jburkardt/data/csv/hw_200.csv")

# Verify retrieval

query_index("kb", "What does LangChain help with?")
query_index("kb", "What is the first height value in the CSV?")

inspect_file("https://raw.githubusercontent.com/langchain-ai/langchain/master/README.md")
summarise_file("local.pdf")
extract_tables("https://people.sc.fsu.edu/~jburkardt/data/csv/airtravel.csv")
ocr_image("https://i.sstatic.net/IvV2y.png")
