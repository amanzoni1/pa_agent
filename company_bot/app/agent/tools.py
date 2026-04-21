import os
from typing import List, Tuple
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "app", "vector_db")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
# Lower distance = more similar. Tune per embedding model / dataset.
SIMILARITY_SCORE_THRESHOLD = 1.5

# Lazy singletons to avoid reloading on every tool call
_EMBEDDINGS = None
_DB = None


def _get_db() -> Chroma:
    global _EMBEDDINGS, _DB
    if _EMBEDDINGS is None:
        _EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    if _DB is None:
        _DB = Chroma(
            persist_directory=DB_DIR,
            embedding_function=_EMBEDDINGS,
            collection_name="acme_knowledge",
        )
    return _DB

@tool
def lookup_company_policy(query: str) -> str:
    """
    Search the Knowledge Base.
    Use this to find info about: HR policies, IT setup, Engineering standards,
    Project Chimera, Security protocols, or Pricing.

    Args:
        query: The specific question or topic to search for.
    """
    if not os.path.exists(DB_DIR):
        return "Error: Knowledge Base not found. Please run ingest.py."

    # 1. Load the DB (cached)
    db = _get_db()

    # 2. Search with scores if available
    try:
        results_with_scores: List[Tuple[object, float]] = db.similarity_search_with_score(query, k=3)
        # Filter by threshold (lower distance = more similar)
        filtered = [doc for doc, score in results_with_scores if score <= SIMILARITY_SCORE_THRESHOLD]
        results = filtered
    except Exception:
        # Fallback to similarity search without scores
        results = db.similarity_search(query, k=3)

    # 3. Format Output
    if not results:
        return "No relevant documents found."

    formatted_docs = []
    for doc in results:
        # Extract the header metadata we saved earlier
        source = doc.metadata.get("source", "Unknown")
        h1 = doc.metadata.get("Header 1", "")
        h2 = doc.metadata.get("Header 2", "")

        context = f"SOURCE: {source} > {h1} > {h2}\nCONTENT:\n{doc.page_content}"
        formatted_docs.append(context)

    return "\n\n---\n\n".join(formatted_docs)
