import io

import docx
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_docx_bytes(paragraphs: list[str]) -> bytes:
    """Build a real, in-memory DOCX document for use as a mock upload."""
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
