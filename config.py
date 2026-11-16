import os

# Load variables from a local .env file if one exists. This is a no-op in CI
# (there is no .env there) and in production (real env vars are set by the host).
# .env is git-ignored, so secrets never get committed to this public repo.
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional at runtime; real env vars still work without it.
    pass

def get_gemini_api_key() -> str | None:
    """Return the Gemini API key from the environment (or None if unset).

    The key is NEVER stored in code. It comes from the GEMINI_API_KEY env var,
    supplied via a local .env file during development or as a host secret in
    production.
    """
    return os.environ.get("GEMINI_API_KEY")

def get_ai_access_token() -> str | None:
    """Return the shared access token that gates the AI endpoint (or None).

    This is the "password to use the AI" control. Only requests presenting this
    token in the X-AI-Token header may trigger a (paid) Gemini call, so random
    public visitors cannot exhaust the owner's quota. The token is set via the
    AI_ACCESS_TOKEN env var and is never committed.
    """
    return os.environ.get("AI_ACCESS_TOKEN")
