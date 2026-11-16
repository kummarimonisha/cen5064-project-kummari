from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from data.gemini_ai_client import AIClientError, GeminiAIClient
from main import app
from service.resume_analysis_service import ResumeAnalysisService

client = TestClient(app)

# A newline built with chr(10) so pasting this file can never split a string.
NL = chr(10)

# --------------------------------------------------------------------------
# GeminiAIClient: prompt building + response parsing (API fully mocked)
# --------------------------------------------------------------------------

def test_prompt_includes_bullets_and_job_keywords():
    ai = GeminiAIClient(api_key="test-key")
    prompt = ai.build_prompt(
        flagged_bullets=["Led the backend team"],
        job_keywords=["python", "fastapi"],
    )
    # The prompt must contain BOTH the flagged bullet and the job requirements.
    assert "Led the backend team" in prompt
    assert "python" in prompt
    assert "fastapi" in prompt

def test_generate_revisions_parses_mocked_response():
    # Build a fake SDK client so NO real network call happens.
    fake_response = MagicMock()
    fake_response.text = "Rewrote bullet one with 30% impact" + NL + "Rewrote bullet two"
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content.return_value = fake_response

    ai = GeminiAIClient(client=fake_sdk)
    revisions = ai.generate_revisions(
        flagged_bullets=["bullet one", "bullet two"],
        job_keywords=["python"],
    )

    assert revisions == ["Rewrote bullet one with 30% impact", "Rewrote bullet two"]
    fake_sdk.models.generate_content.assert_called_once()

def test_generate_revisions_empty_bullets_makes_no_call():
    fake_sdk = MagicMock()
    ai = GeminiAIClient(client=fake_sdk)
    assert ai.generate_revisions([], ["python"]) == []
    fake_sdk.models.generate_content.assert_not_called()

def test_generate_revisions_raises_on_empty_response():
    fake_response = MagicMock()
    fake_response.text = ""
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content.return_value = fake_response

    ai = GeminiAIClient(client=fake_sdk)
    try:
        ai.generate_revisions(["a bullet"], ["python"])
        raise AssertionError("expected AIClientError")
    except AIClientError:
        pass

# --------------------------------------------------------------------------
# ResumeAnalysisService.refine_bullets: orchestration (AI client mocked)
# --------------------------------------------------------------------------

def test_service_refines_only_unquantified_bullets():
    fake_ai = MagicMock()
    fake_ai.generate_revisions.return_value = ["Led the backend team of 8 engineers"]

    service = ResumeAnalysisService(ai_client=fake_ai)
    bullets = [
        "Managed 12 microservices",  # already quantified -> NOT sent to AI
        "Led the backend team",      # unquantified      -> sent to AI
    ]
    result = service.refine_bullets(bullets, job_text="Python backend engineer")

    assert result == [
        {
            "before": "Led the backend team",
            "after": "Led the backend team of 8 engineers",
        }
    ]
    sent_bullets, _sent_keywords = fake_ai.generate_revisions.call_args.args
    assert sent_bullets == ["Led the backend team"]

def test_service_returns_empty_when_all_bullets_quantified():
    fake_ai = MagicMock()
    service = ResumeAnalysisService(ai_client=fake_ai)
    result = service.refine_bullets(["Cut costs by $5000"], job_text="finance")
    assert result == []
    fake_ai.generate_revisions.assert_not_called()

def test_service_without_ai_client_raises():
    service = ResumeAnalysisService()  # no ai_client configured
    try:
        service.refine_bullets(["Led the team"], job_text="python")
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass

# --------------------------------------------------------------------------
# /api/refine endpoint: the access-token gate (AI fully mocked)
# --------------------------------------------------------------------------

def test_refine_endpoint_rejects_missing_token():
    # Server HAS a token configured, but the request sends none -> 403, no call.
    with patch("main.get_ai_access_token", return_value="secret"):
        response = client.post("/api/refine", json={"bullets": ["Led the team"]})
    assert response.status_code == 403

def test_refine_endpoint_rejects_wrong_token():
    with patch("main.get_ai_access_token", return_value="secret"):
        response = client.post(
            "/api/refine",
            json={"bullets": ["Led the team"]},
            headers={"X-AI-Token": "wrong"},
        )
    assert response.status_code == 403

def test_refine_endpoint_disabled_when_no_token_configured():
    # Server has NO token set -> AI is closed to everyone (fail safe).
    with patch("main.get_ai_access_token", return_value=None):
        response = client.post(
            "/api/refine",
            json={"bullets": ["Led the team"]},
            headers={"X-AI-Token": "anything"},
        )
    assert response.status_code == 503

def test_refine_endpoint_allows_valid_token_and_returns_revisions():
    # Correct token -> the request is allowed. The Gemini client is mocked, so
    # no real network call happens and no API key is needed.
    fake_ai = MagicMock()
    fake_ai.generate_revisions.return_value = ["Led a 6-person backend team"]

    with patch("main.get_ai_access_token", return_value="secret"), \
         patch("main.GeminiAIClient", return_value=fake_ai):
        response = client.post(
            "/api/refine",
            json={"bullets": ["Led the backend team"], "job_description": "python"},
            headers={"X-AI-Token": "secret"},
        )

    assert response.status_code == 200
    assert response.json() == {
        "revisions": [
            {
                "before": "Led the backend team",
                "after": "Led a 6-person backend team",
            }
        ]
    }
