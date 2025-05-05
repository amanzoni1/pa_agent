# app/tools/web_loader.py

import logging
from typing import Dict, Any

from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader

logger = logging.getLogger(__name__)


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
