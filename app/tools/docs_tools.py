# app/tools/docs_tools.py

import base64
import logging
import mimetypes
import os
import pathlib
import shutil
import tempfile
from typing import Any, Dict, List, Union
from urllib.parse import urlparse

import requests
from langchain_core.tools import tool
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_llm

LOGGER = logging.getLogger(__name__)

_LLM = get_llm()
_CHUNKER = RecursiveCharacterTextSplitter(chunk_size=1_000, chunk_overlap=200)


# helpers
def _download(url: str, suffix: str | None = None) -> str:
    """Stream *url* to a NamedTemporaryFile and return its local path."""
    resp = requests.get(url, timeout=30, stream=True)
    resp.raise_for_status()
    suffix = (
        suffix
        or pathlib.Path(urlparse(url).path).suffix
        or mimetypes.guess_extension(resp.headers.get("content-type", ""))
        or ".bin"
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    for chunk in resp.iter_content(8192):
        tmp.write(chunk)
    tmp.flush()
    return tmp.name


def _as_local(path_or_url: str) -> str:
    """Return a local file path for *path_or_url* (downloading if it is remote)."""
    if path_or_url.lower().startswith(("http://", "https://")):
        return _download(path_or_url)
    return path_or_url


# LangGraph tools
@tool
def inspect_file(path_or_url: str, head_chars: int = 500) -> Dict[str, Any]:
    """
    Quick health‑check for *any* file.

    Returns path (local), byte‑size, guessed MIME type, and the first *head_chars*
    characters (or a <binary …> placeholder for non‑text blobs).
    """
    try:
        path = _as_local(path_or_url)
        sample_bytes: bytes
        with open(path, "rb") as fh:
            sample_bytes = fh.read(head_chars)
        mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
        try:
            sample = sample_bytes.decode("utf-8", errors="replace")
        except Exception:
            sample = f"<binary {len(sample_bytes)} bytes>"
        return {
            "path": path,
            "size_bytes": os.path.getsize(path),
            "mime": mime,
            "sample": sample,
        }
    except Exception as exc:
        LOGGER.exception("inspect_file failed")
        return {"error": str(exc)}


@tool
def summarise_file(path_or_url: str, max_tokens: int = 512) -> str:
    """
    LLM synopsis for small *textual* files (≤ ~15 kB recommended).

    Supported extensions
    --------------------
    • .pdf – via ``PyPDFLoader`` (lazy import)
    • everything else is loaded as plain UTF‑8

    Notes
    -----
    1. The document is **not** chunked into Pinecone – this is a one‑off call.
    2. Large files are truncated after the first ≈3×1000‑char segments.
    """
    path = _as_local(path_or_url)
    ext = pathlib.Path(path).suffix.lower()

    # Lazy imports to keep cold‑start fast
    if ext == ".pdf":
        try:
            from langchain_community.document_loaders import PyPDFLoader  # type: ignore
        except ImportError:
            return "PyPDFLoader missing – run `pip install langchain-community[pdf]`."
        text = "\n".join(d.page_content for d in PyPDFLoader(path).load())
    else:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as exc:
            return f"Cannot read file: {exc}"

    chunks = _CHUNKER.split_text(text)[:3]
    prompt = (
        "You are an assistant. Provide a concise summary of the following document for a busy user:\n\n"
        + "\n\n".join(chunks)
    )
    return _LLM.invoke(prompt, max_tokens=max_tokens).content


@tool
def extract_tables(path_or_url: str, head_rows: int = 5) -> Union[str, List[Dict]]:
    """
    Preview tabular data.

    • **CSV** – returns the first *head_rows* as JSON records.
    • **PDF** – extracts every table via *tabula‑py* (Java required).

    Any other extension → explanatory error message.
    """
    path = _as_local(path_or_url)
    ext = pathlib.Path(path).suffix.lower()

    # CSV
    if ext == ".csv":
        try:
            import pandas as pd  # heavy – import only when needed
        except ImportError:
            return "pandas not installed – run `pip install pandas`."
        df = pd.read_csv(path)
        return df.head(head_rows).to_dict(orient="records")

    # PDF
    if ext == ".pdf":
        if shutil.which("java") is None:
            return "Java runtime not found – required by tabula‑py to parse PDF tables."
        try:
            import tabula  # type: ignore
        except ImportError:
            return "tabula‑py not installed – run `pip install tabula-py`."
        try:
            dfs = tabula.read_pdf(path, pages="all")
        except Exception as exc:
            return f"tabula error: {exc}"
        return [df.head(head_rows).to_dict(orient="records") for df in dfs]

    return "Unsupported file type for table extraction (only CSV and PDF supported)."


@tool
def ocr_image(image_path_or_url: str) -> str:
    """
    Run Tesseract OCR on an image (PNG/JPEG/WEBP) and return the extracted text.
    """
    path = _as_local(image_path_or_url)
    if not path.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
        return "Unsupported image format – please provide PNG/JPEG/WEBP."
    try:
        from PIL import Image  # type: ignore – optional heavy dep
        import pytesseract  # type: ignore – optional heavy dep
    except ImportError:
        return "pytesseract and Pillow required – run `pip install pytesseract pillow`."

    try:
        text = pytesseract.image_to_string(Image.open(path).convert("RGB"))
        return text.strip() or "(no text recognised)"
    except Exception as exc:
        LOGGER.exception("ocr_image failed")
        return f"OCR error: {exc}"


@tool
def save_uploaded_file(
    filename: str, content_b64: str, overwrite: bool = False
) -> Dict[str, Any]:
    """
    Persist a client‑uploaded file *exactly as received*.

    Parameters
    ----------
    filename   Destination path (absolute or relative). \
               Intermediate directories are created automatically.

    content_b64  Raw base‑64 payload from the front‑end.
    overwrite    If ``False`` and *filename* already exists → return an error.

    Returns
    -------
    { "path": str, "size_bytes": int } on success, or { "error": str }.
    """
    try:
        dest = pathlib.Path(filename).expanduser().resolve()
        if dest.exists() and not overwrite:
            return {"error": f"{dest} already exists – pass overwrite=True to replace."}

        data = base64.b64decode(content_b64)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return {"path": str(dest), "size_bytes": len(data)}
    except Exception as exc:
        LOGGER.exception("save_uploaded_file failed")
        return {"error": str(exc)}
