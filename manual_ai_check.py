"""Manual, one-off check that the REAL Gemini call works.

This is NOT a unit test (pytest never runs it) and it is NOT used by CI. Run it
yourself after setting GEMINI_API_KEY to confirm the live AI actually rewrites
bullets.

Usage:
    1. Put your key in a local .env file:  GEMINI_API_KEY=your-real-key
    2. Run:  python manual_ai_check.py

It makes a real API call and spends a small amount of your Gemini quota.
"""

from config import get_gemini_api_key
from data.gemini_ai_client import AIClientError, GeminiAIClient

def main() -> None:
    if not get_gemini_api_key():
        print("GEMINI_API_KEY is not set. Add it to a .env file first.")
        return

    ai = GeminiAIClient(api_key=get_gemini_api_key())
    bullets = [
        "Led the backend team",
        "Improved the deployment process",
    ]
    job_keywords = ["python", "fastapi", "aws"]

    print("Calling Gemini model " + ai.MODEL + " ...")
    print("")
    try:
        revisions = ai.generate_revisions(bullets, job_keywords)
    except AIClientError as exc:
        print("AI call failed:", exc)
        return

    print("Rewritten bullets:")
    for original, rewritten in zip(bullets, revisions):
        print("  - before: " + original)
        print("    after : " + rewritten)

if __name__ == "__main__":
    main()
