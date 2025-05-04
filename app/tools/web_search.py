from typing import List, Dict
from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults


@tool
def tavily_search(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Search the web using TavilySearchResults and return up to max_results
    documents, each with 'url' and 'content'.
    """
    results = TavilySearchResults(max_results=max_results).invoke(query)
    return results
