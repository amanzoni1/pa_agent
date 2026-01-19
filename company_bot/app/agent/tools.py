import os
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Configuration
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_DIR = os.path.join(BASE_DIR, "app", "vector_db")
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

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

    # 1. Load the DB
    # We don't need to re-index, just load the existing one
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    db = Chroma(
        persist_directory=DB_DIR,
        embedding_function=embeddings,
        collection_name="acme_knowledge"
    )

    # 2. Search
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
