# app/rag/utils.py

import logging, time, tempfile, requests, re
from pathlib import Path
from urllib.parse import urlparse
from typing import List

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    WebBaseLoader,
    PyPDFLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)

from app.config import PINECONE_API_KEY, PINECONE_ENV

# globals
logger = logging.getLogger(__name__)

_pc = Pinecone(api_key=PINECONE_API_KEY)
_EMBED = OpenAIEmbeddings(model="text-embedding-3-small")
_DIM = 1536

_REGION_MAP = {
    "us-east1": "us-east-1",
    "uswest1": "us-west-1",
}

# helpers
def _download_and_load(
    url: str,
    suffix: str,
    loader_cls,
    verify_ssl: bool = True,
    **loader_kwargs,
) -> List[Document]:
    """
    Stream `url` to a NamedTemporaryFile (auto‑deleted), then parse it with
    `loader_cls`.  `suffix` must match the file‑type expected by the loader.
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        r = requests.get(url, timeout=30, stream=True, verify=verify_ssl)
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp.flush()  # ensure bytes on disk
        return loader_cls(tmp.name, **loader_kwargs).load()


def _load_remote_file(
    url: str,
    suffix: str,
    loader_cls,
    **loader_kwargs,
) -> List[Document]:
    """
    Wrapper around `_download_and_load` that retries without SSL verification
    when a certificate error is raised (common on internal sites with
    self‑signed certs).
    """
    try:
        return _download_and_load(url, suffix, loader_cls, True, **loader_kwargs)
    except requests.exceptions.SSLError:
        logger.warning(
            "SSL verification failed for %s – retrying with verify=False", url
        )
        return _download_and_load(url, suffix, loader_cls, False, **loader_kwargs)


def load_docs(path_or_url: str) -> list[Document]:
    """
    Auto‑detect and load docs from:
      • PDF (.pdf)                   → PyPDFLoader
      • Markdown (.md / .markdown)   → UnstructuredMarkdownLoader
      • CSV (.csv)                   → CSVLoader   (each row = Document)
      • HTTP/HTTPS URL or .html      → WebBaseLoader
      • DOCX (.docx)                 → UnstructuredWordDocumentLoader
    Handles both *remote* and *local* paths. Raises ValueError if unsupported.
    """
    parsed = urlparse(path_or_url)

    # Remote URL
    if parsed.scheme in ("http", "https"):
        lower = parsed.path.lower()
        if lower.endswith(".pdf"):
            return _load_remote_file(path_or_url, ".pdf", PyPDFLoader)
        if lower.endswith((".md", ".markdown")):
            return _load_remote_file(path_or_url, ".md", UnstructuredMarkdownLoader)
        if lower.endswith(".csv"):
            return _load_remote_file(path_or_url, ".csv", CSVLoader)
        if lower.endswith(".docx"):
            return _load_remote_file(path_or_url, ".docx", UnstructuredWordDocumentLoader)
        return WebBaseLoader(path_or_url).load()

    # Local file path
    ext = Path(path_or_url).suffix.lower()
    if ext == ".pdf":
        return PyPDFLoader(path_or_url).load()
    if ext in (".md", ".markdown"):
        return UnstructuredMarkdownLoader(path_or_url).load()
    if ext == ".csv":
        return CSVLoader(path_or_url).load()
    if ext == ".html":
        return WebBaseLoader(Path(path_or_url).as_uri()).load()
    if ext == ".docx":
        return UnstructuredWordDocumentLoader(path_or_url).load()

    raise ValueError(f"Unsupported file type: {path_or_url}")


def split_docs(docs: list[Document]) -> list[Document]:
    """
    Semantic chunking with heading + page metadata.
    Uses RecursiveCharacterTextSplitter (natural language, 1000/200).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""],  # default NL separators
    )
    chunks: list[Document] = []
    for doc in docs:
        for chunk in splitter.split_documents([doc]):
            heading = chunk.page_content.split("\n", 1)[0].strip()
            chunk.metadata.update(
                {"page": doc.metadata.get("page", 0), "heading": heading}
            )
            chunks.append(chunk)
    return chunks


def _parse_env(env: str) -> tuple[str, str]:
    """
    Accept forms like 'aws-us-east-1', 'us-east-1-aws', 'us-east1-gcp'…
    Returns (cloud, region) with Pinecone's exact region spelling.
    """
    parts = env.lower().strip().split("-")
    if parts[-1] in ("aws", "gcp", "azure"):
        cloud, region = parts[-1], "-".join(parts[:-1])
    elif parts[0] in ("aws", "gcp", "azure"):
        cloud, region = parts[0], "-".join(parts[1:])
    else:
        raise ValueError(f"Invalid PINECONE_ENV={env!r}")

    # normalise implicit region spellings
    region = _REGION_MAP.get(region, region)
    return cloud, region


def _sanitize(name: str) -> str:
    cleaned = re.sub(r"[^a-z0-9-]+", "-", name.lower())
    return re.sub(r"-{2,}", "-", cleaned).strip("-")


def _ensure_index(name: str) -> None:
    """Create `name` index if it doesn’t exist yet (serverless)."""
    if name in (idx["name"] for idx in _pc.list_indexes()):
        return

    cloud, region = _parse_env(PINECONE_ENV)
    logger.info("Creating Pinecone index %s on %s/%s …", name, cloud, region)
    _pc.create_index(
        name=name,
        dimension=_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud=cloud, region=region),
    )

    try:
        while not _pc.describe_index(name).status["ready"]:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.warning(
            "Interrupted while waiting for index %s; it may finish in the background.",
            name,
        )
        raise

    logger.info("Index %s ready", name)


def get_store(name: str) -> PineconeVectorStore:
    name = _sanitize(name)
    _ensure_index(name)
    return PineconeVectorStore(
        index=_pc.Index(name),
        embedding=_EMBED,
        text_key="page_content",
    )
