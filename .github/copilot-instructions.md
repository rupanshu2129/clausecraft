# Copilot Instructions for ClauseCraft.ai

## Project Overview
ClauseCraft.ai analyzes RFQs against SOW/MSA standards, highlights deviations/risks, and drafts suggested redlines. It is built with FastAPI (Python backend), Jinja2 templates (frontend), and integrates with OpenAI's API for AI analysis. A Retrieval-Augmented Generation (RAG) service powers knowledge base lookups using ChromaDB and sentence-transformers.

## Key Components
- `main.py`: FastAPI app, API endpoints, prompt construction, OpenAI integration, and HTML rendering.
- `lib/extract_text.py`: Extracts text from PDF, DOCX, and TXT files for analysis.
- `lib/rag_service.py`: RAG service for document chunking, embedding, vector search, and knowledge base management (ChromaDB).
- `static/` and `templates/`: Frontend assets (CSS, HTML).

## Data Flow
1. User uploads RFQ and SOW/MSA files via the web UI.
2. Backend extracts text, builds a prompt, and queries OpenAI for analysis.
3. RAG service provides relevant context from prior uploads.
4. OpenAI returns JSON with deviations, redlines HTML, and KPIs.
5. Frontend displays results in a tabbed interface.

## Developer Workflows
- **Run locally:**
  ```bash
  python -m venv .venv && source .venv/bin/activate
  pip install -r requirements.txt
  uvicorn main:app --reload --host 0.0.0.0 --port 8000
  # Visit http://localhost:8000
  ```
- **Environment:** Requires `OPENAI_API_KEY` in `.env` or environment.
- **Knowledge base:**
  - Add docs: `POST /api/knowledge/add` (multipart files)
  - Clear: `POST /api/knowledge/clear`
  - Stats: `GET /api/knowledge/stats`
- **Analyze:** `POST /api/analyze` with `rfq` and optional `sows` files.
- **Docker:** See `README.md` for build/run instructions.

## Patterns & Conventions
- All AI output must be valid JSON (see `SCHEMA` in `main.py`).
- RAG context is injected into prompts if available.
- File parsing is best-effort; input quality matters.
- ChromaDB persists in `chroma_db/`.
- Use `SentenceTransformer('all-MiniLM-L6-v2')` for embeddings.
- Error handling: API returns JSON with `error` keys on failure.

## Integration Points
- OpenAI API (Chat Completions, JSON mode)
- ChromaDB (vector store)
- Optional: Supabase for user/auth/storage (not required by default)

## Examples
- See `main.py` for API endpoint usage and prompt structure.
- See `lib/rag_service.py` for knowledge base management patterns.

---
For more, see `README.md`. Update this file if you add new workflows, endpoints, or architectural changes.
