# app/rag/utils.py

import logging, os, time, ssl, tempfile, requests
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import PINECONE_API_KEY, PINECONE_ENV

# globals
logger = logging.getLogger(__name__)

_pc = Pinecone(api_key=PINECONE_API_KEY)
_EMBED = OpenAIEmbeddings(model="text-embedding-3-small")
_DIM = 1536


# helpers
def parse_env(env: str) -> tuple[str, str]:
    """Split PINECONE_ENV like 'us-east-1-aws' → ('aws', 'us-east-1')."""
    parts = env.strip().split("-")
    if parts[-1] in ("aws", "gcp", "azure"):
        return parts[-1], "-".join(parts[:-1])
    if parts[0] in ("aws", "gcp", "azure"):
        return parts[0], "-".join(parts[1:])
    raise ValueError(f"Invalid PINECONE_ENV: {env!r}")


def ensure_index(name: str) -> None:
    """Create `name` index if it doesn’t exist yet (serverless)."""
    if name in (idx["name"] for idx in _pc.list_indexes()):
        return

    cloud, region = parse_env(PINECONE_ENV)
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


def get_store(name: str) -> PineconeVectorStore:
    name = name.lower()
    ensure_index(name)
    return PineconeVectorStore(
        index=_pc.Index(name),
        embedding=_EMBED,
        text_key="page_content",
    )


def download_pdf(url: str) -> Path:
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


def split_docs(docs: list[Document]) -> list[Document]:
    """
    Semantic chunking with heading + page metadata.
    Uses RecursiveCharacterTextSplitter (natural language, 512/150).
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=512,
        chunk_overlap=150,
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
