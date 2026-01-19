import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# --- CONFIGURATION ---
SOURCE_DIR = "app/docs"
DB_DIR = "app/vector_db"

# open-source embedding model
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"

def ingest():
    print(f"--- 🚀 Starting Ingestion ---")

    # 1. Load Markdown Files
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Error: Source directory '{SOURCE_DIR}' not found.")
        return

    docs = []
    print(f"📂 Scanning {SOURCE_DIR}...")
    for filename in os.listdir(SOURCE_DIR):
        if filename.endswith(".md"):
            path = os.path.join(SOURCE_DIR, filename)
            with open(path, "r", encoding="utf-8") as f:
                docs.append(Document(
                    page_content=f.read(),
                    metadata={"source": filename}
                ))
    print(f"   Found {len(docs)} documents.")

    # 2. Phase 1: Semantic Splitting (By Headers)
    # This keeps "Section 2.1" together with its content
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    header_splits = []
    for doc in docs:
        splits = markdown_splitter.split_text(doc.page_content)
        # Preserve filename metadata
        for split in splits:
            split.metadata["source"] = doc.metadata["source"]
        header_splits.extend(splits)

    print(f"   Split into {len(header_splits)} semantic sections.")

    # 3. Phase 2: Token Splitting (Chunking)
    # Ensure no chunk is too big for the vector DB
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    final_chunks = text_splitter.split_documents(header_splits)
    print(f"   Final chunks to index: {len(final_chunks)}")

    # 4. Create Vector DB
    print(f"🧠 Loading Embeddings ({EMBEDDING_MODEL})...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # Reset DB if exists (Clean slate)
    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR)

    print(f"💾 Saving to ChromaDB at {DB_DIR}...")
    Chroma.from_documents(
        documents=final_chunks,
        embedding=embeddings,
        persist_directory=DB_DIR,
        collection_name="acme_knowledge"
    )

    print(f"✅ Ingestion Complete! DB is ready.")

if __name__ == "__main__":
    ingest()
