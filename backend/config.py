"""Central configuration, read from the environment.

Every tunable the app has lives here so that nothing is hardcoded in more than
one place. Import the module (``from config import ANTHROPIC_MODEL``) rather
than re-reading ``os.getenv`` at each call site.
"""
import os


def _split_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


# --- LLM -------------------------------------------------------------------
# Every agent reads this. Switching models is a one-line env change, not a
# code edit in four files.
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

# --- Search ----------------------------------------------------------------
SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "3"))
# Attempts per query before giving up on it (transient network/API errors).
SEARCH_MAX_ATTEMPTS = int(os.getenv("SEARCH_MAX_ATTEMPTS", "3"))
SEARCH_BACKOFF_SECONDS = float(os.getenv("SEARCH_BACKOFF_SECONDS", "1.0"))
# Politeness delay between sub-task searches.
SEARCH_PACING_SECONDS = float(os.getenv("SEARCH_PACING_SECONDS", "0.5"))

# --- Research loop ---------------------------------------------------------
# How many times the graph may refine unanswered sub-questions and search
# again before moving on to analysis. 0 disables the retry loop.
MAX_RESEARCH_RETRIES = int(os.getenv("MAX_RESEARCH_RETRIES", "1"))
# A pass is "thin" if fewer than this fraction of sub-tasks produced results.
MIN_COVERAGE_RATIO = float(os.getenv("MIN_COVERAGE_RATIO", "0.6"))

# --- Sessions --------------------------------------------------------------
RESEARCH_TIMEOUT_SECONDS = int(os.getenv("RESEARCH_TIMEOUT_SECONDS", "180"))
# Sessions whose client never connects are swept after this long.
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "600"))
SESSION_SWEEP_INTERVAL_SECONDS = int(os.getenv("SESSION_SWEEP_INTERVAL_SECONDS", "30"))
# Backpressure: refuse new research once this many are in flight.
MAX_ACTIVE_SESSIONS = int(os.getenv("MAX_ACTIVE_SESSIONS", "50"))

# --- CORS ------------------------------------------------------------------
# Comma-separated exact origins.
CORS_ALLOW_ORIGINS = _split_env(
    "CORS_ALLOW_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
)
# Optional regex, for Vercel preview deployments whose hostname changes per
# build, e.g. r"https://multi-agent-research-.*\.vercel\.app"
CORS_ALLOW_ORIGIN_REGEX = os.getenv("CORS_ALLOW_ORIGIN_REGEX") or None
