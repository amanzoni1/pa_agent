# Personal Assistant Agent with LangGraph

A powerful conversational agent with retrieval-augmented generation, MCP server, long- and short-term memory, and tool integrations—powered by LangGraph, LangChain, Redis, PostgreSQL, and Pinecone.

---

## Features

- **Conversational Chat**
  - Interactive CLI (`app/run.py`)
  - Programmatic access via Python SDK (`langgraph_sdk`)
- **Retrieval-Augmented Generation**
  - Ingest & query PDF, Markdown, HTML, CSV & DOCX into Pinecone
  - `index_docs(name, path_or_url)` & `query_index(name, question, k)` tools
- **MCP Server**
  - 25+ CoinMarketCap endpoints exposed
- **Long-Term Memory**
  - Profile, projects & instructions stored in PostgreSQL, namespaced by user
- **Short-Term Memory**
  - Rolling summary of recent conversation (pruned after 10+ turns)
- **Tool Integrations**
  - **Web & Knowledge**: `web_fetch`, `wiki_search`, `tavily_search`
  - **File Handling**: `inspect_file`, `summarise_file`, `extract_tables`, `ocr_image`, `save_uploaded_file`
  - **Finance**: `get_stock_quote`, `get_stock_news`
- **Robustness**
  - Automatic retries on transient OpenAI errors
  - Healthchecks on Redis & Postgres in Docker Compose

## Project Structure

```
personal_assistant/
├── app/
│   ├── config.py
│   ├── run.py           # CLI entrypoint
│   ├── graph/
│   │   ├── assistant.py # StateGraph definition
│   │   ├── state.py     # ChatState schema
│   │   └── memory/      # summarization, schemas
│   ├── tools/           # external tool fns
│   ├── rag/             # RAG loaders & indexers
│   ├── mcp/             # MCP server logic
│   └── schemas/
├── requirements.txt
├── docker-compose.yml
├── langgraph.json
└── README.md
```

## Prerequisites

- Python 3.11+
- Docker & Docker Compose (for containerized deployment)
- Redis & PostgreSQL (local or via Docker)
- OpenAI, Pinecone, Tavily & CoinMarketCap API keys

## Getting Started

### Local Setup

1. Clone the repo:

   ```bash
   git clone https://github.com/amanzoni1/pa_agent && cd personal_assistant
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in project root:

   ```ini
   OPENAI_API_KEY=your_openai_key
   LANGSMITH_API_KEY=your_langsmith_key
   REDIS_URI=redis://localhost:6379
   POSTGRES_URI=postgresql://postgres:postgres@localhost:5432/personal_assistant?sslmode=disable
   PINECONE_API_KEY=your_pinecone_key
   TAVILY_API_KEY=your_tavily_key
   COINMARKETCAP_API_KEY=your_cmc_key
   ```

5. Ensure Redis and Postgres are running locally.

## Command-Line Interface (CLI)

Interact via chat in terminal:

```bash
python -m app.run --thread-id <optional-uuid> --user-id <optional-your_id>
```

Commands:

- `/memory`: Show long-term memory (profile, projects, instructions) stored.
- `/mcp`: get all the tools available from the MCP server.
- `/exit` or Ctrl-D: Quit.

## Docker Compose Deployment

1. Build your LangGraph image:

   ```bash
   langgraph build -t my-assistant
   ```

2. Launch via Docker Compose:

   ```bash
   docker compose up -d
   ```

3. Access:

   - API: `http://localhost:8123`
   - Swagger Docs: `http://localhost:8123/docs`

### Python SDK Usage

Install the SDK:

```bash
pip install langgraph_sdk
```

Example:

```python
import asyncio
from langgraph_sdk import get_client
from langchain_core.messages import HumanMessage

async def main():
    client = get_client(url="http://localhost:8123")
    thread = await client.threads.create()
    run = await client.runs.create(
        thread["thread_id"],
        "my-assistant",
        input={"messages": [HumanMessage(content="Hello!")]},
        config={"configurable": {"user_id": "you", "thread_id": thread["thread_id"]}},
    )
    final = await client.runs.join(thread["thread_id"], run["run_id"])
    msgs = final.get("messages", [])
    ai = msgs[1]["content"] if len(msgs) > 1 else None
    print("AI:", ai)

asyncio.run(main())
```
