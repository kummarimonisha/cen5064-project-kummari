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

def _chunk(text):
    """A fake streaming chunk with a .text attribute."""
    c = MagicMock()
    c.text = text
    return c


def test_prompt_includes_bullet_and_job_keywords():
    ai = GeminiAIClient(api_key="test-key")
    prompt = ai.build_prompt(
        bullet="Led the backend team",
        job_keywords=["python", "fastapi"],
    )
    # The prompt must contain BOTH the bullet and the job keywords.
    assert "Led the backend team" in prompt
    assert "python" in prompt
    assert "fastapi" in prompt

def test_generate_revisions_parses_streamed_response():
    # generate_content_stream returns an iterable of chunks; one call per bullet.
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content_stream.side_effect = [
        [_chunk("Rewrote bullet one "), _chunk("with 30% impact")],
        [_chunk("Rewrote bullet two")],
    ]

    ai = GeminiAIClient(client=fake_sdk)
    revisions = ai.generate_revisions(
        flagged_bullets=["bullet one", "bullet two"],
        job_keywords=["python"],
    )

    assert revisions == ["Rewrote bullet one with 30% impact", "Rewrote bullet two"]
    # One streamed call per bullet.
    assert fake_sdk.models.generate_content_stream.call_count == 2

def test_generate_revisions_empty_bullets_makes_no_call():
    fake_sdk = MagicMock()
    ai = GeminiAIClient(client=fake_sdk)
    assert ai.generate_revisions([], ["python"]) == []
    fake_sdk.models.generate_content.assert_not_called()

@patch("data.gemini_ai_client.time.sleep", lambda *_a, **_k: None)
def test_generate_revisions_raises_when_all_models_fail():
    # Every streamed call yields no text -> after exhausting all models/retries,
    # the client raises. time.sleep is patched so retries are instant.
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content_stream.return_value = []  # no chunks

    ai = GeminiAIClient(client=fake_sdk)
    try:
        ai.generate_revisions(["a bullet"], ["python"])
        raise AssertionError("expected AIClientError")
    except AIClientError:
        pass


@patch("data.gemini_ai_client.time.sleep", lambda *_a, **_k: None)
def test_generate_revisions_falls_back_to_next_model():
    # First model's two attempts raise "high demand"; the SECOND model streams
    # a good answer. The feature should still work (503 does not break it).
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content_stream.side_effect = [
        Exception("503 UNAVAILABLE high demand"),
        Exception("503 UNAVAILABLE high demand"),
        [_chunk("Rewritten bullet with 20% improvement")],  # second model works
    ]

    ai = GeminiAIClient(client=fake_sdk)
    result = ai.generate_revisions(["a bullet"], ["python"])
    assert result == ["Rewritten bullet with 20% improvement"]

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
