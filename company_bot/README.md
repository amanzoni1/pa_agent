# Company Bot — Acme Corp Support Agent Prototype

A **prototype** of an internal company support chatbot built with **LangGraph** and **deepagents**. The agent acts as a Tier-1 support specialist for the fictional "Acme Corp", using RAG over internal documentation, long-term memory, reusable skills, and a custom retrieval tool.

This is designed as a **demo / show-off project** — it runs locally as a beautiful Rich-based CLI, loads a small fake knowledge base, and demonstrates advanced agent features (memory injection, progressive skill disclosure, tool use, checkpointing).

## Features

- **Deep Agent Architecture** (`deepagents.create_deep_agent`):
  - Static identity & voice guidelines loaded from `/system/AGENTS.md`.
  - Reusable skill workflows from `/system/skills/` (progressive disclosure).
  - Persistent long-term memory via `/memories/` (InMemoryStore → easy swap to Postgres/Redis).
- **RAG Knowledge Base**:
  - Custom tool `lookup_company_policy` searches a Chroma vector DB.
  - Semantic + header-aware splitting for accurate retrieval.
  - Fake company docs in `app/docs/` (easy to replace with real ones).
- **Rich CLI Experience**:
  - Live streaming with spinner.
  - Pretty visualization of thinking steps, tool calls, and final answers.
  - Supports reasoning tags (`<think>`) from models like Qwen/DeepSeek.
- **Flexible Model Support**:
  - Shortcuts (`openai`, `fast`) + prefix parsing for Fireworks, Anthropic, OpenAI.
- **Security Considerations Built-In** (demo-level):
  - `/system/` config isolated in `app/agent/assets/` with `virtual_mode=True`.
  - Strong prompting to protect system files and hide internals.

## Project Structure

```
company_bot/
├── main.py                  # CLI launcher with Rich UI
├── ingest.py                # Ingest company docs → Chroma vector DB
├── requirements.txt         # Dependencies
├── .env.example             # Example environment file
├── .gitignore
├── app/
│   ├── docs/                # Company policy Markdown files
│   ├── vector_db/           # Generated Chroma DB
│   └── agent/
│       ├── assets/          # Isolated config (AGENTS.md + skills/)
│       │   ├── AGENTS.md
│       │   └── skills/
│       │       └── rag_skill.md
│       ├── graph.py         # Agent construction
│       ├── config.py        # Model loading & provider parsing
│       ├── backend.py       # CompositeBackend with /system/ routing
│       └── tools.py         # RAG retrieval tool
```

## Quick Start

This project is inside a larger personal agents repo: https://github.com/amanzoni1/pa_agent

1. **Clone & Install**
   ```bash
    git clone https://github.com/amanzoni1/pa_agent
    cd pa_agent/company_bot
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
   ```

2. **Set Up API Keys** (copy `.env.example` → `.env`)
   ```env
   OPENAI_API_KEY=sk-...
   ANTHROPIC_API_KEY=...
   FIREWORKS_API_KEY=...
   ```
   You need at least one provider.

3. **(Optional) Ingest Knowledge Base**
   
    The repository includes a pre-built Chroma vector DB in `app/vector_db/` with the 7 sample docs already indexed — you can run the bot immediately.
    Run ingestion only if you add, remove, or modify files in `app/docs/`:

   ```bash
   python ingest.py
   ```

   This will re-process `app/docs/*.md` and regenerate the vector DB.

5. **Run the Bot**
   ```bash
   python main.py --model openai        # or 'fast', 'claude', 'fw-...', etc.
   ```

   Example models:
   - `--model openai` → GPT-4o
   - `--model fast`   → Fireworks GPT-OSS-20B (cheap/fast)
   - `--model fw-accounts/fireworks/models/qwen3-235b-a22b-instruct-2507`

   Type messages, quit with `q` or `quit`.

## Demo Tips

The knowledge base includes realistic fake docs on VPN, benefits, Project Chimera (AI sales agents), HR policies, and more. Try these queries to see RAG + skills in action:

- VPN/IT: "How do I set up the company VPN?", "What's the VPN shared secret?", "Troubleshoot VPN connection"
- Benefits/HR: "What health insurance do we have?", "How many mental health days do I get?", "Gym membership reimbursement?"
- Projects: "Tell me about Project Chimera", "What's the status of Chimera beta?"

## Security Notes (Demo Only)

This prototype uses `FilesystemBackend` routed to `/system/` (the `assets/` folder) for easy loading of static config.

**Current protections**:
- `virtual_mode=True` → no path traversal.
- Isolated `assets/` folder containing **only** config files.
- Strong prompting to refuse modifications and hide filesystem details.

**Recommended additional hardening** (do this now):
```bash
chmod -R 444 app/agent/assets   # Make config truly read-only
```
This makes any `edit_file`/`write_file` on `/system/` fail with "Permission denied".

**Do NOT use this pattern in production without further changes** — see below.

## Production Considerations

This is a **prototype**. For a real company deployment:

1. **Switch to Preloaded Files (Maximum Security)**
   - Remove `/system/` Filesystem route.
   - Cache `AGENTS.md` + skills contents at startup.
   - Pass `{"files": PRELOADED_DICT}` on every `invoke/astream`.
   - Agent has zero real filesystem access for config → no probing/writes possible.

2. **Persistent Storage**
   - Swap `InMemoryStore` → `PostgresStore` or Redis for `/memories/`.
   - Swap `MemorySaver` → RedisSaver for thread checkpointing.

3. **Deployment**
   - Wrap in FastAPI/Streamlit for web UI.
   - Add authentication (e.g., company SSO).
   - Rate limiting & logging.


## Possible Improvements

- Add more skills (e.g., ticket creation, calendar lookup).
- Multi-modal support (image upload for troubleshooting).
- Voice mode (when available).
- Web interface.
- Hot-reload for config changes.
