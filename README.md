# ClauseCraft.ai

ClauseCraft.ai analyzes RFQs against your SOW/MSA standards, highlights deviations and risks, and drafts suggested redlines. Built with FastAPI + Jinja templates and the Gemini API.

## Features
- Upload an RFQ (PDF/DOCX/TXT) and optional SOWs/MSAs
- Deviation report with clause-by-clause comparison and risk badges
- AI Draft (redlines) with basic diff styling
- KPI estimates (cycle time, coverage, risk reduction)
- Clean, responsive UI
- Four-tab layout: Deviations, AI Draft, Approvals, Summary

## Tech Stack
- Backend: FastAPI (Python)
- Frontend: Jinja2 templates, vanilla JS, CSS
- AI: Google Gemini via `google-genai`
- File parsing: pdfminer.six, python-docx
- Runtime: Uvicorn

## Prerequisites
- Python 3.10+
- A Google Gemini API key (`GEMINI_API_KEY`)

## Quick Start (Local)
```bash
# 1) Clone
git clone https://github.com/<your-account>/clausecraft.git
cd clausecraft

# 2) Python deps
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3) Env vars
echo "GEMINI_API_KEY=your_key_here" > .env

# 4) Run
uvicorn main:app --reload --host 0.0.0.0 --port 8000
# Open http://localhost:8000
```

## How It Works
1. Upload the RFQ and optional SOWs/MSAs.
2. Backend extracts text (PDF/DOCX/TXT) and builds a structured prompt.
3. Gemini returns JSON containing deviations, redlines HTML, and KPIs.
4. The frontend renders a deviation table, AI draft, and KPIs inside tabs.

## Project Structure
```
clausecraft/
  ├─ lib/
  │  └─ extract_text.py
  ├─ static/
  │  └─ styles.css
  ├─ templates/
  │  └─ index.html
  ├─ main.py
  ├─ requirements.txt
  ├─ Dockerfile
  ├─ render.yaml
  └─ README.md
```

## API
- POST `/api/analyze`
  - Form fields: `rfq` (file, required), `sows` (files, optional)
  - Response: JSON of deviations, `redlinesHTML`, and `kpis`

## Docker
```bash
# Build
docker build -t clausecraft .

# Run (maps 8000 → container $PORT)
docker run -e GEMINI_API_KEY=your_key -e PORT=8000 -p 8000:8000 clausecraft
# Open http://localhost:8000
```

## Deploy
### Render (recommended)
- Connect the GitHub repo in Render → New → Web Service
- Build: `pip install --upgrade pip && pip install -r requirements.txt`
- Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Env var: `GEMINI_API_KEY`
- Alternatively, use `render.yaml` in the repo for autodiscover

### Railway / Other PaaS
- Set `GEMINI_API_KEY`
- Build with `pip install -r requirements.txt`
- Start `uvicorn main:app --host 0.0.0.0 --port $PORT`

### Docker Anywhere
- Use the Docker section above to run on any VM or container platform

## Supabase (optional)
Supabase is great for DB/auth/storage. This app doesn't require a DB, but you can:
- Add Supabase for user auth and persistence
- Store analyses and approval workflows in Postgres
- Use `supabase-py` to integrate with FastAPI

## Environment Variables
- `GEMINI_API_KEY` (required): Google Gemini API key

## Notes
- PDFs and DOCX are parsed best-effort; quality of input affects output
- Gemini output is parsed as JSON; basic fallback attempts to recover JSON if needed

## License
MIT
