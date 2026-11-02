from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from service.resume_analysis_service import DocumentParseError, ResumeAnalysisService

app = FastAPI(title="AI-Powered Resume Optimizer & ATS Matcher")

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

    # Hand off to the Service tier. It orchestrates the Data tier parser and the
    # Domain tier scorer so one request goes from upload all the way to a score.
    try:
        result = service.analyze(file.filename, content, job_description)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "extracted_text": result["extracted_text"],
        "ats_score": result["ats_score"],
    }
