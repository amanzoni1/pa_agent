# app/tools/docs_loader.py

import requests, io
import logging
import tempfile
import pandas as pd
from typing import List, Dict, Any, Optional

from langchain_core.tools import tool
from langchain_community.document_loaders import CSVLoader, UnstructuredCSVLoader, PyPDFLoader, DirectoryLoader

logger = logging.getLogger(__name__)


def _download_to_tempfile(url: str, suffix: str) -> str:
    """Fetch a URL and write to a NamedTemporaryFile, return its path."""
    resp = requests.get(url, verify=False, timeout=10)
    resp.raise_for_status()
    tf = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tf.write(resp.content)
    tf.close()
    return tf.name


@tool
def csv_to_docs(
    path: str,
    source_column: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Turn each row of a CSV (local path or URL) into a mini‑document via CSVLoader.

    Args:
      path:           Local file path or URL to your .csv
      source_column:  (optional) column name to use as the 'source' metadata

    Returns:
      [
        {
          "content": "ColA: …\nColB: …",
          "metadata": {"row": 0, "source": "Nationals", …}
        },
        …
      ]
    """
    try:
        # download remote to a temp file if needed
        local = (
            _download_to_tempfile(path, suffix=".csv")
            if path.lower().startswith(("http://", "https://"))
            else path
        )
        loader = CSVLoader(
            file_path=local,
            source_column=source_column,
        )
        docs = loader.load()
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception:
        logger.exception("csv_to_docs failed for %r", path)
        return []


@tool
def unstructured_csv_to_docs(path: str) -> List[Dict[str, Any]]:
    """
    Load a CSV as an HTML table (elements mode) via UnstructuredCSVLoader.

    Returns the raw documents (with `text_as_html` in metadata).
    """
    try:
        local = (
            _download_to_tempfile(path, suffix=".csv")
            if path.lower().startswith(("http://", "https://"))
            else path
        )
        loader = UnstructuredCSVLoader(
            file_path=local,
            mode="elements",
        )
        docs = loader.load()
        return [{"content": d.page_content, "metadata": d.metadata} for d in docs]
    except Exception:
        logger.exception("unstructured_csv_to_docs failed for %r", path)
        return []


@tool
def pdf_to_docs(path: str) -> List[Dict[str, Any]]:
    """
    Split a PDF into page‑level Documents via PyPDFLoader.

    Args:
      path: Local file path or HTTP(S) URL to a PDF.

    Returns:
      A list of {"content": str, "metadata": dict}, one per page.
      Returns [] on failure.
    """
    try:
        if path.lower().startswith(("http://", "https://")):
            path = _download_to_tempfile(path, ".pdf")

        loader = PyPDFLoader(path, mode="page")
        docs = loader.load()
        return [
            {
                "content": d.page_content,
                "metadata": d.metadata,
            }
            for d in docs
        ]

    except Exception as e:
        logger.exception("pdf_to_docs failed for %r", path)
        return []


@tool
def dir_to_docs(directory: str, pattern: str = "**/*") -> List[Dict[str, Any]]:
    """
    Recursively load all files under a directory into Documents.

    Args:
        directory: Root directory to search.
        pattern:   Glob pattern (e.g. "**/*.md" or "**/*").

    Returns:
        A list of dicts, each with:
          - content  (str): Full text of the document.
          - metadata (dict): {'source': <filepath>, ...}
    """
    try:
        loader = DirectoryLoader(directory, glob=pattern)
        docs = loader.load()
        out: List[Dict[str, Any]] = []
        for d in docs:
            meta = d.metadata.copy()
            meta["source"] = d.metadata.get("source", "")
            out.append({"content": d.page_content, "metadata": meta})
        return out
    except Exception:
        logger.exception("dir_to_docs failed for %r", directory)
        return []
