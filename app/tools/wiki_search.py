from typing import List, Dict
from langchain_core.tools import tool
from langchain_community.document_loaders import WikipediaLoader


@tool
def wiki_search(query: str, max_pages: int = 2) -> List[Dict[str, str]]:
    """
    Load pages from Wikipedia for `query` and return up to max_pages docs;
    each dict has 'source', 'page', and 'content'.
    """
    docs = WikipediaLoader(query=query, load_max_docs=max_pages).load()
    return [
        {
            "source": doc.metadata["source"],
            "page": doc.metadata.get("page", ""),
            "content": doc.page_content,
        }
        for doc in docs
    ]
