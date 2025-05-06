# app/rag/__init__.py

from app.rag.pinecone import index_pdf, query_index

RAG = [
    index_pdf,
    query_index,
]
