from fastapi import FastAPI, File, HTTPException, UploadFile

from service.resume_analysis_service import DocumentParseError, ResumeAnalysisService

app = FastAPI(title="AI-Powered Resume Optimizer & ATS Matcher")

service = ResumeAnalysisService()


@app.post("/api/upload")
async def parse_resume(file: UploadFile = File(...)):
    # Input hygiene at the door (Presentation tier): reject obviously wrong
    # file types fast, before reading the body.
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed.")

    content = await file.read()

    # Hand off to the Service tier; it orchestrates the Data tier parser.
    try:
        extracted_text = service.extract_resume_text(file.filename, content)
    except DocumentParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "filename": file.filename,
        "extracted_text": extracted_text,
    }
