"""Settings, read from the environment."""
import os


def _split_env(name: str, default: str) -> list[str]:
    return [x.strip() for x in os.getenv(name, default).split(",") if x.strip()]


ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "3"))
SEARCH_MAX_ATTEMPTS = int(os.getenv("SEARCH_MAX_ATTEMPTS", "3"))
SEARCH_BACKOFF_SECONDS = float(os.getenv("SEARCH_BACKOFF_SECONDS", "1.0"))
SEARCH_PACING_SECONDS = float(os.getenv("SEARCH_PACING_SECONDS", "0.5"))

# Refine-and-search-again rounds allowed before giving up. 0 disables retries.
MAX_RESEARCH_RETRIES = int(os.getenv("MAX_RESEARCH_RETRIES", "1"))
# A pass is thin if fewer than this fraction of sub-tasks found anything.
MIN_COVERAGE_RATIO = float(os.getenv("MIN_COVERAGE_RATIO", "0.6"))

RESEARCH_TIMEOUT_SECONDS = int(os.getenv("RESEARCH_TIMEOUT_SECONDS", "180"))
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "600"))
SESSION_SWEEP_INTERVAL_SECONDS = int(os.getenv("SESSION_SWEEP_INTERVAL_SECONDS", "30"))
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "50"))

CORS_ALLOW_ORIGINS = _split_env(
    "CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
# For origins whose hostname varies per build, e.g. Vercel previews.
CORS_ALLOW_ORIGIN_REGEX = os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None
