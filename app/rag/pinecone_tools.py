# app/rag/pinecone_tools.py

import logging
import os , requests
import tempfile
import time
import ssl
from urllib.error import URLError
from urllib.request import urlretrieve
from pathlib import Path
from typing import Optional
from urllib.request import urlretrieve

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import Pinecone as PineconeVectorStore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from pinecone import Pinecone, ServerlessSpec

from app.config import PINECONE_API_KEY, PINECONE_ENV, get_llm

# ──────────────────────────────────────────────────────────────────────────────
# Globals
# ──────────────────────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 1) Pinecone control‑plane client
_pc = Pinecone(api_key=PINECONE_API_KEY)

# 2) Embeddings & LLM
_EMBED = OpenAIEmbeddings(model="text-embedding-3-small")
_DIM = 1536  # text‑embedding‑3‑small output size
_LLM = get_llm()

# 3) LLM combine chain used for RAG
_SYS = (
    "Answer the question concisely. If the context isn’t sufficient, say you don’t know.\n\n"
    "Context:\n{context}"
)
_PROMPT = ChatPromptTemplate.from_messages([("system", _SYS), ("human", "{input}")])
_COMBINE = create_stuff_documents_chain(llm=_LLM, prompt=_PROMPT)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _parse_env(env: str) -> tuple[str, str]:
    """Split PINECONE_ENV like 'us-east-1-aws' → ('aws', 'us-east-1')."""
    parts = env.strip().split("-")
    if parts[-1] in ("aws", "gcp", "azure"):
        return parts[-1], "-".join(parts[:-1])
    if parts[0] in ("aws", "gcp", "azure"):
        return parts[0], "-".join(parts[1:])
    raise ValueError(f"Invalid PINECONE_ENV: {env!r}")


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
    while not _pc.describe_index(name).status["ready"]:
        time.sleep(1)
    logger.info("Index %s ready", name)


def _get_store(name: str) -> PineconeVectorStore:
    _ensure_index(name)
    return PineconeVectorStore(
        index=_pc.Index(name),
        embedding=_EMBED,
        text_key="page_content",
    )


def _download(url: str) -> Path:
    """
    Download remote PDF to a temp file and return its path.
    Falls back to verify=False if the first try hits an SSL error.
    """
    if not url.startswith(("http://", "https://")):
        return Path(url)  # local file

    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)

    try:
        # normal secure path
        urlretrieve(url, tmp)
        return Path(tmp)
    except URLError as err:
        # only retry for SSL issues
        if isinstance(err.reason, ssl.SSLCertVerificationError):
            logger.warning(
                "SSL verification failed for %s – retrying with verify=False", url
            )
            resp = requests.get(url, timeout=20, verify=False, stream=True)
            resp.raise_for_status()
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=8192):
                    fh.write(chunk)
            return Path(tmp)
        raise


def _split(docs: list[Document]) -> list[Document]:
    """
    Semantic chunking with heading + page metadata.
    Uses RecursiveCharacterTextSplitter (natural language, 512/100).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=100,
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


# ──────────────────────────────────────────────────────────────────────────────
# Public tools
# ──────────────────────────────────────────────────────────────────────────────
@tool
def index_pdf(name: Optional[str], path_or_url: str) -> str:
    """
    ➜ Ingest a PDF into Pinecone.

    Args:
      name: target Pinecone index (auto‑created if needed).
      path_or_url: local path *or* HTTP(S) URL to a PDF.

    Returns:
      Success / error message.
    """
    if not name:
        return "❓ Please provide a Pinecone index name."

    try:
        pdf_path = _download(path_or_url)
        pages = PyPDFLoader(str(pdf_path)).load()
        chunks = _split(pages)

        store = _get_store(name)
        store.add_documents(chunks)
        return f"✅ Indexed {len(chunks)} chunks into '{name}'."
    except Exception as exc:
        logger.exception("index_pdf failed")
        return f"index_pdf error: {exc}"


@tool
def query_index(name: str, question: str, k: int = 10) -> str:
    """
    ➜ Ask `question` against Pinecone index `name` using MMR retrieval.

    Args:
      name: Pinecone index name.
      question: natural‑language question.
      k: number of diverse chunks to retrieve (default 10).

    Returns:
      Answer string (may cite context implicitly).
    """
    try:
        store = _get_store(name)
        retriever = store.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "lambda_mult": 0.5},
        )
        rag = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=_COMBINE,
        )
        result  = rag.invoke({"input": question})
        answer  = result.get("answer") or result.get("output") or ""
        return answer or "I couldn’t find that in the context."
    except Exception as exc:
        logger.exception("query_index failed")
        return f"query_index error: {exc}"
