from typing import List
from langchain_core.tools import tool
from app.config import get_llm

llm = get_llm()

@tool
def web_search(query: str, k: int = 5) -> List[str]:
    """Return top‑k web search snippets for the query."""
    # replace with real API later
    fake_results = [f"Snippet {i} about {query}" for i in range(1, k + 1)]
    return fake_results
