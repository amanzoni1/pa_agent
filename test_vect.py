#!/usr/bin/env python3
import os
import time
from dotenv import load_dotenv

# ──────────────────────────────────────────────────────────────────────────────
# 1️⃣ Load credentials & settings from .env
# ──────────────────────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV = os.getenv("PINECONE_ENV", "us-east-1-aws").strip()
INDEX_NAME = "test"


# ──────────────────────────────────────────────────────────────────────────────
# 2️⃣ Parse PINECONE_ENV into (cloud, region)
# ──────────────────────────────────────────────────────────────────────────────
def parse_env(env: str) -> tuple[str, str]:
    parts = env.split("-")
    if parts[-1] in ("aws", "gcp", "azure"):
        cloud = parts[-1]
        region = "-".join(parts[:-1])
    elif parts[0] in ("aws", "gcp", "azure"):
        cloud = parts[0]
        region = "-".join(parts[1:])
    else:
        raise ValueError(f"Invalid PINECONE_ENV={env!r}")
    return cloud, region


CLOUD, REGION = parse_env(PINECONE_ENV)

# ──────────────────────────────────────────────────────────────────────────────
# 3️⃣ Imports
# ──────────────────────────────────────────────────────────────────────────────
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore


# ──────────────────────────────────────────────────────────────────────────────
# 4️⃣ Main
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # 4.1 Download & parse PDF
    print("📥 Downloading and loading PDF…")
    loader = PyPDFLoader(
        "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
    )
    docs = loader.load()
    print(f"🤖 Loaded {len(docs)} page-docs")

    # 4.2 Split into chunks
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)
    print(f"✂️ Split into {len(chunks)} chunk(s)")

    # 4.3 Control-plane client: list/create index
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [x["name"] for x in pc.list_indexes()]
    print("⛓️ Existing indexes:", existing)

    if INDEX_NAME not in existing:
        print(f"✨ Creating index '{INDEX_NAME}' on {CLOUD}/{REGION}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(cloud=CLOUD, region=REGION),
        )
        # wait until ready
        while not pc.describe_index(INDEX_NAME).status["ready"]:
            time.sleep(1)
        print(f"✅ Index '{INDEX_NAME}' created")

    # 4.4 Prepare embedding model
    embeds = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=OPENAI_API_KEY,
    )

    # 4.5 Get data-plane Index
    index = pc.Index(INDEX_NAME)

    # 4.6 Instantiate LangChain vectorstore & upsert
    vstore = PineconeVectorStore(
        index=index,
        embedding=embeds,
        text_key="page_content",  # where each chunk’s text lives
    )
    vstore.add_documents(chunks)
    print(f"✅ Indexed {len(chunks)} chunks into '{INDEX_NAME}'")


if __name__ == "__main__":
    main()
