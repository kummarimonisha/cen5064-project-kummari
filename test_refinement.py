from unittest.mock import MagicMock

from data.gemini_ai_client import AIClientError, GeminiAIClient
from service.resume_analysis_service import ResumeAnalysisService

# --------------------------------------------------------------------------
# GeminiAIClient: prompt building + response parsing (API fully mocked)
# --------------------------------------------------------------------------

def test_prompt_includes_bullets_and_job_keywords():
    client = GeminiAIClient(api_key="test-key")
    prompt = client.build_prompt(
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
    fake_response.text = "Rewrote bullet one with 30% impact\nRewrote bullet two"
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content.return_value = fake_response

    client = GeminiAIClient(client=fake_sdk)
    revisions = client.generate_revisions(
        flagged_bullets=["bullet one", "bullet two"],
        job_keywords=["python"],
    )

    assert revisions == ["Rewrote bullet one with 30% impact", "Rewrote bullet two"]
    # Confirm the model was actually invoked once.
    fake_sdk.models.generate_content.assert_called_once()

def test_generate_revisions_empty_bullets_makes_no_call():
    fake_sdk = MagicMock()
    client = GeminiAIClient(client=fake_sdk)
    assert client.generate_revisions([], ["python"]) == []
    fake_sdk.models.generate_content.assert_not_called()

def test_generate_revisions_raises_on_empty_response():
    fake_response = MagicMock()
    fake_response.text = ""
    fake_sdk = MagicMock()
    fake_sdk.models.generate_content.return_value = fake_response

    client = GeminiAIClient(client=fake_sdk)
    try:
        client.generate_revisions(["a bullet"], ["python"])
        raise AssertionError("expected AIClientError")
    except AIClientError:
        pass

# --------------------------------------------------------------------------
# ResumeAnalysisService.refine_bullets: orchestration (AI client mocked)
# --------------------------------------------------------------------------

def test_service_refines_only_unquantified_bullets():
    # The AI client is a mock that echoes a fixed revision list.
    fake_ai = MagicMock()
    fake_ai.generate_revisions.return_value = ["Led the backend team of 8 engineers"]

    service = ResumeAnalysisService(ai_client=fake_ai)
    bullets = [
        "Managed 12 microservices",  # already quantified -> NOT sent to AI
        "Led the backend team",      # unquantified      -> sent to AI
    ]
    result = service.refine_bullets(bullets, job_text="Python backend engineer")

    assert result == ["Led the backend team of 8 engineers"]
    # The service must send ONLY the flagged (unquantified) bullet to the AI.
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
