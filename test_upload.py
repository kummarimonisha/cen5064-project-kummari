import io

import docx
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    #Build a real, in-memory DOCX document for use as a mock upload.
    document = docx.Document()
    for text in paragraphs:
        document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()

def test_reject_invalid_file_type():
    # A .png must be rejected before any parsing happens.
    response = client.post(
        "/api/upload",
        files={"file": ("image.png", b"fake image data", "image/png")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF or DOCX files are allowed."

def test_extract_text_from_mock_docx():
    # A real DOCX built in memory stands in for an uploaded resume.
    content = _make_docx_bytes(["Experience", "Built a resume analyzer in Python."])
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "resume.docx",
                content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "resume.docx"
    assert "Experience" in body["extracted_text"]
    assert "resume analyzer" in body["extracted_text"]

def test_reject_corrupt_docx():
    # Correct extension but garbage bytes: should be a clean 400, not a crash.
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "broken.docx",
                b"this is not a real docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 400

def test_upload_returns_ats_score_end_to_end():
    # One request travels upload -> parse -> score. The job text yields exactly
    # four keywords (python, fastapi, docker, kubernetes) and the resume
    # contains two of them, so the ATS score is 50.0%.
    content = _make_docx_bytes(["Skilled in Python and FastAPI."])
    response = client.post(
        "/api/upload",
        files={
            "file": (
                "resume.docx",
                content,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"job_description": "Python FastAPI Docker Kubernetes"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["ats_score"] == 50.0
    assert "python" in body["matched_keywords"]
    assert "docker" in body["missing_keywords"]
    assert "Python" in body["extracted_text"]


# --------------------------------------------------------------------------
# ParserFactory: Factory Method picks the right parser per file type
# --------------------------------------------------------------------------

def test_parser_factory_returns_correct_parser_types():
    from data.document_parser import DocxParser, ParserFactory, PdfParser

    assert isinstance(ParserFactory.get_parser("resume.pdf"), PdfParser)
    assert isinstance(ParserFactory.get_parser("resume.docx"), DocxParser)
    assert isinstance(ParserFactory.get_parser("RESUME.PDF"), PdfParser)


def test_parser_factory_rejects_unsupported_type():
    from data.document_parser import DocumentParseError, ParserFactory

    try:
        ParserFactory.get_parser("photo.png")
        raise AssertionError("expected DocumentParseError")
    except DocumentParseError:
        pass


# --------------------------------------------------------------------------
# ResumeRepository: analysis results are persisted (logic -> storage)
# --------------------------------------------------------------------------

def test_repository_saves_and_counts(tmp_path):
    from data.resume_repository import ResumeRepository

    db = tmp_path / "test.db"
    repo = ResumeRepository(db_path=str(db))
    assert repo.count() == 0
    row_id = repo.save_analysis(
        "resume.docx",
        {"ats_score": 50.0, "matched_keywords": ["python"], "missing_keywords": ["aws"]},
    )
    assert row_id == 1
    assert repo.count() == 1


def test_service_analyze_persists_result(tmp_path):
    from data.resume_repository import ResumeRepository
    from service.resume_analysis_service import ResumeAnalysisService

    db = tmp_path / "svc.db"
    repo = ResumeRepository(db_path=str(db))
    service = ResumeAnalysisService(repository=repo)

    content = _make_docx_bytes(["Skilled in Python and SQL."])
    service.analyze("resume.docx", content, "Need Python and SQL")

    # The analysis was stored.
    assert repo.count() == 1
