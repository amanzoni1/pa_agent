# app/tools/web_tools.py

import logging
from typing import List, Dict, Any

from langchain_core.tools import tool
from langchain_community.tools import TavilySearchResults
from langchain_community.document_loaders import WebBaseLoader

from app.config import TAVILY_API_KEY


logger = logging.getLogger(__name__)

# instantiate once at module load
_TAVILY = TavilySearchResults(
    api_key=TAVILY_API_KEY,
    max_results=5,
    search_depth="advanced",
    include_content=True,
    include_answer=True,
    include_images=False,
    include_raw_content=False,
)


@tool
def web_fetch(url: str, max_pages: int = 1) -> Dict[str, Any]:
    """
    Fetch and clean one or more web pages.

    Args:
      url: single URL or comma‑separated list of URLs (e.g. "gazzetta.it, example.com")
      max_pages: how many URLs to actually fetch (default 1)

    Returns:
      {
        "pages": [
          { "source": <url>,
            "title":  <page title if any>,
            "content":<cleaned text body>
          },
          …
        ]
      }
    """
    try:
        # split & limit
        urls = [u.strip() for u in url.split(",")][:max_pages]

        # auto‑prepend scheme if missing
        def normalize(u: str) -> str:
            return u if u.startswith(("http://", "https://")) else "https://" + u

        urls = [normalize(u) for u in urls]

        loader = WebBaseLoader(urls)
        docs = loader.load()
        pages = []
        for d in docs:
            pages.append(
                {
                    "source": d.metadata.get("source", ""),
                    "title": d.metadata.get("title", ""),
                    "content": d.page_content.strip(),
                }
            )
        return {"pages": pages}

    except Exception:
        logger.exception("web_fetch failed for url=%r", url)
        return {"pages": []}


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
