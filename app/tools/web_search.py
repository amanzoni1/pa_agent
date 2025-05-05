# app/tools/web_search.py

import os
import logging
from typing import List, Dict, Any

from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults

logger = logging.getLogger(__name__)

# instantiate once at module load
_TAVILY = TavilySearchResults(
    api_key=os.environ["TAVILY_API_KEY"],
    max_results=5,
    search_depth="advanced",
    include_content=True,
    include_answer=True,
    include_images=False,
    include_raw_content=False,
)


@tool
def tavily_search(query: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search the web in real‑time via Tavily.

    Args:
        query: Your search query.
        max_results: How many hits to return (up to 5).

    Returns:
        A list of dicts, each with:
          - url     (str)
          - title   (str)
          - content (str, up to ~20 000 chars)
          - answer  (str, Tavily’s concise extracted answer)
    """
    try:
        _TAVILY.max_results = max_results
        # TavilySearchResults.invoke returns a raw List[Dict]
        hits: List[Dict[str, Any]] = _TAVILY.invoke({"query": query})
        out = []
        for h in hits:
            out.append(
                {
                    "url": h.get("url", ""),
                    "title": h.get("title", ""),
                    "content": h.get("content", "")[:20000],
                    "answer": h.get("answer", "") or "",
                }
            )
        return out
    except Exception:
        logger.exception("tavily_search failed for query=%r", query)
        return []
