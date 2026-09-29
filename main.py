from fastapi import FastAPI, UploadFile, File, HTTPException
from data.document_parser import extract_text_from_file

app = FastAPI()

@app.post("/api/upload")
async def parse_resume(file: UploadFile = File(...)):
    # Fix: Happy-path only defect. Block bad file types.
    if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are allowed.")

    content = await file.read()

    # Fix: Architecture blindness defect. Call the data tier, don't write logic here.
    extracted_text = extract_text_from_file(file.filename, content)

    return {
        "filename": file.filename, 
        "extracted_text": extracted_text
    }