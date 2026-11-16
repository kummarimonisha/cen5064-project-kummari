from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_ai_access_token, get_gemini_api_key
from data.gemini_ai_client import AIClientError, GeminiAIClient
from service.resume_analysis_service import DocumentParseError, ResumeAnalysisService

app = FastAPI(title="AI-Powered Resume Optimizer & ATS Matcher")

# Allow the Next.js dev server (localhost:3000) to call this API from the
# browser. In production this list would be the real frontend origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The default service handles the free, local features (parse + score). It has
# no AI client, so it can never make a paid call by accident.
service = ResumeAnalysisService()

@app.post("/api/upload")
async def analyze_resume(
    file: UploadFile = File(...),
    job_description: str = Form(""),
):
    # Input hygiene at the door (Presentation tier): reject obviously wrong
    # file types fast, before reading the body.
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed.")

    content = await file.read()

    # Hand off to the Service tier. It orchestrates the Data parser and the
    # Domain scorer so one request goes from upload all the way to a report.
    try:
        result = service.analyze(file.filename, content, job_description)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "extracted_text": result["extracted_text"],
        "ats_score": result["ats_score"],
        "matched_keywords": result["matched_keywords"],
        "missing_keywords": result["missing_keywords"],
    }

class RefineRequest(BaseModel):
    """Body for the AI refinement endpoint."""

    bullets: list[str]
    job_description: str = ""

def _require_ai_access(x_ai_token: str | None) -> None:
    """Gate the paid AI endpoint behind a shared secret token.

    The token is checked BEFORE any Gemini call, so a missing or wrong token
    costs zero API credits. If the server has no token configured, the AI
    endpoint is closed to everyone (fail safe, not fail open).
    """
    expected = get_ai_access_token()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="AI features are not enabled on this server.",
        )
    if x_ai_token != expected:
        raise HTTPException(
            status_code=403,
            detail="A valid X-AI-Token header is required to use the AI features.",
        )

@app.post("/api/refine")
async def refine_bullets(
    body: RefineRequest,
    x_ai_token: str | None = Header(default=None),
):
    # 1. Access control first -- no token, no Gemini call, no credits spent.
    _require_ai_access(x_ai_token)

    # 2. Build an AI-enabled service using the server's key. The key is read
    #    from the environment here, never from the request.
    ai_client = GeminiAIClient(api_key=get_gemini_api_key())
    ai_service = ResumeAnalysisService(ai_client=ai_client)

    # 3. Run the refinement. Map AI failures to a clean HTTP error.
    try:
        revisions = ai_service.refine_bullets(body.bullets, body.job_description)
    except AIClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"revisions": revisions}
