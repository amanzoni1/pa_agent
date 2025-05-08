# app/tools/wiki_search.py

import json, logging
from typing import List, Dict, Optional

from langchain_core.tools import tool
from langchain_community.document_loaders import WikipediaLoader
from langchain_core.messages import SystemMessage

from app.config import get_llm

logger = logging.getLogger(__name__)
_model = get_llm()


@tool
def wiki_search(
    query: str,
    max_pages: int = 2,
    trim_content: int = 20000,
    summarize: bool = False,
) -> str:
    """
    Args:
        query: Search term to look up on Wikipedia.
        max_pages: Maximum number of pages to fetch.
        trim_content: Max number of characters to keep from each page's content.
        summarize: If True, generate a brief summary (1–2 sentences) of each page.

    Returns:
        A JSON string representing a list of documents:
        [{
          "source": <URL>,
          "page": <page title>,
          "content": <trimmed text>,
          "summary": <optional summary>
        }, ...]
    """
    try:
        # 1) Fetch raw pages
        loader = WikipediaLoader(query=query, load_max_docs=max_pages)
        docs = loader.load()
    except Exception as e:
        logger.error(
            "wiki_search: failed to load pages for query=%r: %s",
            query,
            e,
            exc_info=True,
        )
        return json.dumps([])

    output: List[Dict[str, Optional[str]]] = []
    for doc in docs:
        source = doc.metadata.get("source")
        title = doc.metadata.get("page") or source
        text = doc.page_content or ""
        # Trim to avoid huge payloads
        if len(text) > trim_content:
            text = text[:trim_content].rsplit(" ", 1)[0] + "..."

        entry: Dict[str, Optional[str]] = {
            "source": source,
            "page": title,
            "content": text,
        }

        # 2) Optional summarization
        if summarize:
            try:
                prompt = SystemMessage(
                    content=(
                        "You are a concise summarizer. "
                        "Summarize the following Wikipedia page in 2 sentences:\n\n"
                        + text
                    )
                )
                summary = _model.invoke([prompt]).content.strip()
                entry["summary"] = summary
            except Exception as e:
                logger.warning("wiki_search: summarization failed for %r: %s", query, e)
                entry["summary"] = None

        output.append(entry)

    return json.dumps(output)
