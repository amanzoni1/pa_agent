# app/rag/pinecone.py

import logging
from typing import Optional

from langchain_core.tools import tool
from langchain.prompts import ChatPromptTemplate
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.document_loaders import PyPDFLoader

from .utils import get_store, download_pdf, split_docs
from app.config import get_rag_llm

logger = logging.getLogger(__name__)

# LLM & prompt
_LLM = get_rag_llm()
_SYS = (
    "Answer **only** using the context below. "
    "If the context does not answer the question, reply 'I dont know.'\n\nContext:\n{context}"
)
_PROMPT = ChatPromptTemplate.from_messages([("system", _SYS), ("human", "{input}")])
_COMBINE = create_stuff_documents_chain(llm=_LLM, prompt=_PROMPT)


# LangGraph tools
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
        pdf_path = download_pdf(path_or_url)
        pages = PyPDFLoader(str(pdf_path)).load()
        chunks = split_docs(pages)

        store = get_store(name)
        store.add_documents(chunks)
        return f"Indexed {len(chunks)} chunks into '{name}'."
    except Exception as exc:
        logger.exception("index_pdf failed")
        return f"index_pdf error: {exc}"


@tool
def query_index(name: str, question: str, k: int = 20) -> str:
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
        store = get_store(name)
        retriever = store.as_retriever(
            # search_type="mmr",
            search_type="similarity_score_threshold",
            search_kwargs={"k": 20, "score_threshold": 0.15},
            # search_kwargs={"k": k, "lambda_mult": 0.5},
        )
        rag = create_retrieval_chain(
            retriever=retriever,
            combine_docs_chain=_COMBINE,
        )
        result = rag.invoke({"input": question}, return_source_documents=True)

        answer = result.get("answer") or result.get("output") or ""

        docs_raw = (
            result.get("source_documents")
            or result.get("documents")
            or result.get("context")
            or []
        )

        docs = docs_raw if isinstance(docs_raw, list) else docs_raw.get("documents", [])

        cites = " ".join(f"(page {d.metadata.get('page', '?')})" for d in docs[:2])

        return (
            answer + (" " + cites if cites else "")
            if answer
            else "I couldn’t find that in the context."
        )
    except Exception as exc:
        logger.exception("query_index failed")
        return f"query_index error: {exc}"
