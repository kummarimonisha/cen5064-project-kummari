from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_reject_invalid_file_type():
    # Test the edge case we fixed
    response = client.post(
        "/api/upload",
        files={"file": ("image.png", b"fake image data", "image/png")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Only PDF or DOCX files are allowed."