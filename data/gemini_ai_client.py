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

    Reliability design (why the AI feature stays working on the free tier):
      1. ONE bullet per request -- each call is tiny and fast, which avoids the
         504 "deadline exceeded" that large requests cause.
      2. STREAMING -- the response is read token-by-token so the connection
         stays active and does not idle out waiting for a full answer (the main
         cure for 504s).
      3. MODEL FALLBACK + RETRY -- a prioritized list of models, each retried a
         couple of times, so 503 "high demand" on one model falls through to the
         next instead of failing the feature.

    Security:
      - The API key is read from the GEMINI_API_KEY environment variable and is
        never hard-coded or committed (.env is git-ignored).
      - The SDK client is created lazily (on first use), so merely importing
        this module never requires a key. That keeps CI and tests import-safe.
    """

    # Tried in order. "lite" models first: faster and far less likely to hit
    # the free tier's "high demand" throttling. Every name here was confirmed
    # available on the project's API key via models.list().
    MODELS = (
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

    _RETRIES_PER_MODEL = 2
    _BACKOFF_SECONDS = 1.0
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

    def build_prompt(self, bullet: str, job_keywords: list[str]) -> str:
        """Build the instruction to rewrite ONE bullet, tailored to the job."""
        keywords_block = ", ".join(job_keywords) if job_keywords else "(none provided)"
        intro = (
            "You are a resume-writing assistant. Rewrite the single resume "
            "bullet point below so it is specific and quantified (include a "
            "concrete metric or number) and tailored to the target job."
        )
        closing = (
            "Return ONLY the rewritten bullet as one line, with no label, "
            "quotes, bullet character, or extra commentary."
        )
        parts = [
            intro,
            "",
            f"Target job keywords: {keywords_block}",
            "",
            f"Bullet to rewrite: {bullet}",
            "",
            closing,
        ]
        return NL.join(parts)

    def _stream_once(self, client, model: str, prompt: str) -> str:
        """Stream a single request to one model and return the assembled text.

        Streaming keeps the connection active while the model generates, which
        is the main defense against 504 "deadline exceeded".
        """
        from google.genai import types

        chunks = []
        stream = client.models.generate_content_stream(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                http_options=types.HttpOptions(timeout=self._TIMEOUT_MS)
            ),
        )
        for chunk in stream:
            piece = getattr(chunk, "text", None)
            if piece:
                chunks.append(piece)
        return "".join(chunks).strip()

    def _rewrite_one(self, client, bullet: str, job_keywords: list[str]) -> str:
        """Rewrite a single bullet, trying each model with retries."""
        prompt = self.build_prompt(bullet, job_keywords)
        last_error: Exception | None = None
        for model in self.MODELS:
            for attempt in range(self._RETRIES_PER_MODEL):
                try:
                    text = self._stream_once(client, model, prompt)
                    if text:
                        # Collapse any accidental line breaks into one line.
                        return " ".join(text.split())
                    last_error = AIClientError("The AI returned an empty response.")
                except Exception as exc:  # noqa: BLE001 - fall through to next model
                    last_error = exc
                if attempt < self._RETRIES_PER_MODEL - 1:
                    time.sleep(self._BACKOFF_SECONDS)
        raise AIClientError(
            f"The AI service is unavailable right now (tried "
            f"{len(self.MODELS)} models): {last_error}"
        )

    def generate_revisions(
        self, flagged_bullets: list[str], job_keywords: list[str]
    ) -> list[str]:
        """Rewrite each flagged bullet, one small streamed request at a time.

        Returns one rewritten string per input bullet (same order). Returns an
        empty list if there are no bullets to rewrite (no API call).

        Raises:
            AIClientError: if the key is missing, or every model fails every
                attempt for a bullet.
        """
        if not flagged_bullets:
            return []

        client = self._get_client()
        return [self._rewrite_one(client, bullet, job_keywords) for bullet in flagged_bullets]
