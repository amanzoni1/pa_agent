# app/rag/__init__.py

from app.rag.pinecone import index_docs, query_index

RAG = [
    index_docs,
    query_index,
]
