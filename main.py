import json
import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Request, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from lib.extract_text import extract_text

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

from google import genai

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
    if not GEMINI_API_KEY:
        return JSONResponse({"error": "Missing GEMINI_API_KEY"}, status_code=500)

    rfq_bytes = await rfq.read()
    rfq_text, _ = extract_text(rfq_bytes, rfq.filename)

    sow_texts: List[str] = []
    for f in sows:
        data = await f.read()
        text, _ = extract_text(data, f.filename)
        if text.strip():
            sow_texts.append(text)

    prompt = build_prompt(rfq_text, sow_texts)

    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    text = getattr(resp, "text", None)
    if not text:
        return JSONResponse({"error": "No model output"}, status_code=502)

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return JSONResponse({"error": "Malformed model output"}, status_code=502)
        parsed = json.loads(text[start : end + 1])

    return JSONResponse(parsed, status_code=200)