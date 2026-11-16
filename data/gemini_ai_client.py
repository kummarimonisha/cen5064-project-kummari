import os
import time

# A newline, built with chr(10) instead of the escape sequence so copy-pasting
# this file can never turn a backslash-n into a real line break inside a string.
NL = chr(10)


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

    Resilience: Google's free tier frequently throttles an individual model
    (503 "high demand") or times out (504). To keep the feature working, the
    client tries a prioritized LIST of models and retries each a few times with
    a short backoff. It only fails if every model fails every attempt.

    Security:
      - The API key is read from the GEMINI_API_KEY environment variable and is
        never hard-coded or committed (.env is git-ignored).
      - The SDK client is created lazily (on first use), so merely importing
        this module never requires a key. That keeps CI and tests import-safe.
    """

    # Tried in order. If one is busy/slow, the client falls back to the next.
    # These are the free-tier text models observed on the project's key; the
    # list is easy to reorder or extend.
    MODELS = (
        # "lite" models first -- they are faster and far less likely to hit the
        # free tier's "high demand" throttling. Then the standard flash models.
        # Every name here was confirmed available on the project's API key.
        "models/gemini-3.1-flash-lite",
        "models/gemini-3.5-flash-lite",
        "models/gemini-2.5-flash-lite",
        "models/gemini-3.5-flash",
        "models/gemini-3.6-flash",
        "models/gemini-3.7-flash",
        "models/gemini-3.8-flash",
        "models/gemini-2.5-flash",
    )
    # Kept for backward compatibility / display; the first model is the default.
    MODEL = MODELS[0]

    # How many times to try EACH model before moving to the next, and the base
    # wait (seconds) between retries (grows a little each attempt).
    _RETRIES_PER_MODEL = 2
    _BACKOFF_SECONDS = 1.5
    _TIMEOUT_MS = 60_000

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
        # requires the SDK to be configured -- important for CI and tests.
        from google import genai

        self._client = genai.Client(api_key=self._api_key)
        return self._client

    def build_prompt(self, flagged_bullets: list[str], job_keywords: list[str]) -> str:
        """Build the instruction sent to Gemini.

        The prompt includes BOTH the flagged bullets and the target job
        requirements, so the rewrite is tailored to the role.
        """
        bullets_block = NL.join(f"- {b}" for b in flagged_bullets)
        keywords_block = ", ".join(job_keywords) if job_keywords else "(none provided)"
        intro = (
            "You are a resume-writing assistant. Rewrite each resume bullet point "
            "below so it is specific and quantified (include a concrete metric or "
            "number), and tailor it to the target job requirements."
        )
        closing = (
            "Return exactly one rewritten bullet per line, in the same order, "
            "with no numbering, blank lines, or extra commentary."
        )
        parts = [
            intro,
            "",
            f"Target job requirements (keywords): {keywords_block}",
            "",
            "Bullet points to rewrite:",
            bullets_block,
            "",
            closing,
        ]
        return NL.join(parts)

    def _call_model(self, client, model: str, prompt: str) -> str:
        """Make a single generate_content call to one model and return its text."""
        from google.genai import types

        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=self._TIMEOUT_MS)
            ),
        )
        return getattr(response, "text", None) or ""

    def generate_revisions(
        self, flagged_bullets: list[str], job_keywords: list[str]
    ) -> list[str]:
        """Ask Gemini to rewrite the flagged bullets. Returns one string each.

        Returns an empty list if there are no bullets to rewrite (no API call).
        Tries each model in MODELS, retrying each a few times, so transient
        throttling (503) or timeouts (504) on one model do not break the feature.

        Raises:
            AIClientError: only if the key is missing, or every model fails every
                attempt (the last provider error is included).
        """
        # No bullets -> nothing to do, and no reason to spend an API call.
        if not flagged_bullets:
            return []

        prompt = self.build_prompt(flagged_bullets, job_keywords)
        client = self._get_client()

        last_error: Exception | None = None
        for model in self.MODELS:
            for attempt in range(self._RETRIES_PER_MODEL):
                try:
                    text = self._call_model(client, model, prompt)
                    if text.strip():
                        return [ln.strip() for ln in text.splitlines() if ln.strip()]
                    # Empty text: treat as a soft failure and try again / next model.
                    last_error = AIClientError("The AI service returned an empty response.")
                except Exception as exc:  # noqa: BLE001 - we try the next model
                    last_error = exc
                # Short backoff before the next attempt (not after the final one).
                if attempt < self._RETRIES_PER_MODEL - 1:
                    time.sleep(self._BACKOFF_SECONDS * (attempt + 1))

        # Every model failed every attempt. Surface the last provider message;
        # the API key is never part of these messages, so this does not leak it.
        raise AIClientError(
            f"The AI service is unavailable right now (tried "
            f"{len(self.MODELS)} models): {last_error}"
        )
