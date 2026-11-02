import os


class AIClientError(Exception):
    """Raised when the AI service cannot be reached or returns nothing usable.

    Lives in the Data tier so the Service tier can react to one known error
    type without knowing the underlying SDK or HTTP details.
    """

class GeminiAIClient:
    """Data tier: talks to Google AI Studio (Gemini) to rewrite resume bullets.

    This is the ONLY place that knows about the Gemini SDK and the network. It
    builds the prompt, makes the call, and returns plain Python strings. The
    Service tier depends on this client, never on the SDK directly.

    Security:
      - The API key is read from the GEMINI_API_KEY environment variable and is
        never hard-coded or committed (.env is git-ignored). If the key is
        missing, a call fails loudly rather than leaking or guessing.
      - The SDK client is created lazily (on first use), so merely importing
        this module never requires a key. That keeps CI import-safe.
    """

    MODEL = "gemini-1.5-pro"

    def __init__(self, api_key: str | None = None, client=None):
        # Allow an explicit key or a pre-built client to be injected (tests pass
        # a fake client here). Otherwise fall back to the environment variable.
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = client

    def _get_client(self):
        """Create the Gemini SDK client on first use (lazy initialization)."""
        if self._client is not None:
            return self._client
        if not self._api_key:
            raise AIClientError(
                "GEMINI_API_KEY is not set. Provide the key via the environment "
                "to call the AI service."
            )
        # Imported here (not at module top) so importing this module never
        # requires the SDK to be configured — important for CI and tests.
        from google import genai

        self._client = genai.Client(api_key=self._api_key)
        return self._client

    def build_prompt(self, flagged_bullets: list[str], job_keywords: list[str]) -> str:
        """Build the instruction sent to Gemini.

        The prompt includes BOTH the flagged bullets and the target job
        requirements, so the rewrite is tailored to the role.
        """
        bullets_block = "\n".join(f"- {b}" for b in flagged_bullets)
        keywords_block = ", ".join(job_keywords) if job_keywords else "(none provided)"
        return (
            "You are a resume-writing assistant. Rewrite each resume bullet "
            "point below so it is specific and quantified (include a concrete "
            "metric or number), and tailor it to the target job requirements.\n\n"
            f"Target job requirements (keywords): {keywords_block}\n\n"
            "Bullet points to rewrite:\n"
            f"{bullets_block}\n\n"
            "Return exactly one rewritten bullet per line, in the same order, "
            "with no numbering, blank lines, or extra commentary."
        )

    def generate_revisions(
        self, flagged_bullets: list[str], job_keywords: list[str]
    ) -> list[str]:
        """Ask Gemini to rewrite the flagged bullets. Returns one string each.

        Returns an empty list if there are no bullets to rewrite (no API call).

        Raises:
            AIClientError: if the key is missing or the service returns nothing.
        """
        # No bullets -> nothing to do, and no reason to spend an API call.
        if not flagged_bullets:
            return []

        prompt = self.build_prompt(flagged_bullets, job_keywords)
        client = self._get_client()

        try:
            response = client.models.generate_content(
                model=self.MODEL,
                contents=prompt,
            )
        except Exception as exc:
            raise AIClientError("The AI service call failed.") from exc

        text = getattr(response, "text", None)
        if not text:
            raise AIClientError("The AI service returned an empty response.")

        # One rewritten bullet per non-empty line.
        return [line.strip() for line in text.splitlines() if line.strip()]
