import json
import os
import logging
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from lib.extract_text import extract_text

# Basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("clausecraft")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT = os.getenv("OPENAI_PROJECT")

from openai import OpenAI

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

SCHEMA = """
Return ONLY valid JSON with this exact shape:
{
  "deviations": [
    {
      "clause": "string",
      "customerAsk": "string",
      "ourStandard": "string",
      "deviation": 0-100,
      "risk": "High" | "Medium" | "Low",
      "suggestion": "string"
    }
  ],
  "redlinesHTML": "<p>...</p>",
  "kpis": {
    "cycleTimeCutPct": number,
    "firstDraftCoveragePct": number,
    "riskReductionPct": number
  }
}
"""

def build_prompt(rfq_text: str, sow_texts: List[str]) -> str:
    return f"""
You are a contracts analyst. Compare the customer's RFQ to our SOW/MSA standards.

Tasks:
1) Identify key clauses and show the customer's ask vs. our standard.
2) Score "deviation" as a percentage (0–100) based on how far the ask is from our standard.
3) Assign risk: High / Medium / Low, justified in the suggestion text.
4) Produce concise counter-suggestions aligned to common B2B SaaS norms.
5) Generate a short redlined draft snippet as HTML:
   - Use <span class="line-through">deleted</span> for removals
   - Use <span class="underline">added</span> for additions
6) Provide rough KPIs after redlining (best-effort estimates).

RFQ (customer ask):
\"\"\"{rfq_text}\"\"\"

Our standards (one or more SOWs/MSAs; later docs override earlier if conflicts):
\"\"\"{chr(10).join(sow_texts)}\"\"\"

{SCHEMA}
Only output JSON. No extra text.
""".strip()

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/analyze")
async def analyze(rfq: UploadFile, sows: List[UploadFile] = []):
    if not rfq:
        return JSONResponse({"error": "RFQ required"}, status_code=400)
    if not OPENAI_API_KEY:
        return JSONResponse({"error": "Missing OPENAI_API_KEY"}, status_code=500)

    try:
        rfq_bytes = await rfq.read()
        rfq_text, _ = extract_text(rfq_bytes, rfq.filename)
    except Exception as e:
        return JSONResponse({"error": "Failed to read RFQ", "detail": str(e)}, status_code=400)

    sow_texts: List[str] = []
    for f in sows:
        try:
            data = await f.read()
            text, _ = extract_text(data, f.filename)
            if text.strip():
                sow_texts.append(text)
        except Exception as e:
            return JSONResponse({"error": f"Failed to read SOW {getattr(f, 'filename', '')}", "detail": str(e)}, status_code=400)

    prompt = build_prompt(rfq_text, sow_texts)
    logger.info("Analyze invoked. rfq_len=%s sow_count=%s", len(rfq_text or ""), len(sow_texts))

    client = OpenAI(
        api_key=OPENAI_API_KEY,
        base_url=OPENAI_BASE_URL,
        organization=OPENAI_ORG_ID,
        project=OPENAI_PROJECT,
    )
    try:
        # Chat Completions API (messages-based)
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a contracts analyst that outputs strictly valid JSON when asked."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )
        text = resp.choices[0].message.content
    except Exception as e:
        status_code = getattr(e, "status_code", None)
        body = None
        resp_obj = getattr(e, "response", None)
        if resp_obj is not None:
            try:
                body = resp_obj.json()
            except Exception:
                try:
                    body = resp_obj.text
                except Exception:
                    body = None
            if status_code is None:
                status_code = getattr(resp_obj, "status_code", None)
        logger.error("OpenAI upstream error status=%s body=%s err=%s", status_code, body, str(e))
        return JSONResponse(
            {"error": "Model request failed", "detail": body or str(e)},
            status_code=int(status_code) if isinstance(status_code, int) and 100 <= status_code <= 599 else 502,
        )
    if not text:
        return JSONResponse({"error": "No model output"}, status_code=502)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return JSONResponse({"error": "Malformed model output", "detail": text[:500]}, status_code=502)
        try:
            parsed = json.loads(text[start : end + 1])
        except Exception:
            return JSONResponse({"error": "Malformed model output", "detail": text[:500]}, status_code=502)

    return JSONResponse(parsed, status_code=200)