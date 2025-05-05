# app/rag/pinecone_tools.py

import logging
from typing import Optional

from pinecone import Pinecone
from langchain_core.tools import tool
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import ChatPromptTemplate
from langchain.text_splitter import CharacterTextSplitter
from langchain_pinecone import Pinecone as PineconeVectorStore

from app.config import PINECONE_API_KEY, PINECONE_ENV, get_llm
from app.tools.docs_tools import handle_pdf

logger = logging.getLogger(__name__)

# ─── 1) Initialize the Pinecone client ────────────────────────────────
_client = Pinecone(
    api_key=PINECONE_API_KEY,
    environment=PINECONE_ENV,
)

# ─── 2) Shared embedder & LLM ────────────────────────────────────────
_EMBEDDER = OpenAIEmbeddings(model="text-embedding-3-small")
_LLM = get_llm()

# ─── 3) Build your RAG combine‐chain ─────────────────────────────────
_SYSTEM_PROMPT = (
    "Use the following context to answer the question concisely. "
    "If you don’t know the answer, say so.\n\n"
    "Context:\n{context}"
)
_PROMPT = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", "{input}"),
    ]
)
_COMBINE_CHAIN = create_stuff_documents_chain(llm=_LLM, prompt=_PROMPT)


def _get_store(name: str) -> PineconeVectorStore:
    """
    Wrap a Pinecone index in LangChain’s PineconeVectorStore.
    """
    idx = _client.Index(name)
    return PineconeVectorStore(
        index=idx,
        embedding_function=_EMBEDDER.embed_query,
        text_key="text",
    )


@tool
def index_pdf(name: Optional[str], path_or_url: str) -> str:
    """
    Ingest a PDF (by URL or local path) into Pinecone index `name`,
    splitting it into smaller chunks first.
    """
    if not name:
        return "❓ What Pinecone index name should I use to store these embeddings?"

    # 1) Download & parse the PDF into page-level dicts
    pages = handle_pdf(path_or_url=path_or_url, mode="page")
    if isinstance(pages, str) and pages.startswith("❓"):
        return pages
    if not pages:
        return "⚠️ No pages extracted from the PDF."

    # 2) Wrap each page in a Document
    docs = [Document(page_content=p["content"], metadata=p["metadata"]) for p in pages]

    # 3) Chunk documents into smaller pieces
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    # 4) Upsert into Pinecone
    try:
        store = _get_store(name)
        store.add_documents(chunks)
        return f"✅ Indexed {len(chunks)} chunks into Pinecone index '{name}'."
    except Exception as e:
        logger.exception("index_pdf failed")
        return f"index_pdf error: {e}"


@tool
def query_index(name: str, question: str, k: int = 5) -> str:
    """
    Run a RAG-powered query against the Pinecone index `name`.
    """
    try:
        store = _get_store(name)
        retriever = store.as_retriever(search_kwargs={"k": k})
        rag = create_retrieval_chain(
            retriever=retriever,
            combine_documents_chain=_COMBINE_CHAIN,
        )
        out = rag.invoke({"input": question})
        return out.get("output", "")
    except Exception as e:
        logger.exception("query_index failed")
        return f"query_index error: {e}"
