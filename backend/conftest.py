"""Put the backend root on sys.path so tests import what the app imports."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))


@pytest.fixture(autouse=True)
def _isolate_process_state(monkeypatch):
    """Keep every test off real shared state.

    Inside the compose stack REDIS_URL points at the live Redis, and without
    this the suite wrote its fake search results into the app's real cache,
    where they would be served to users for the cache TTL. Tests that need the
    Redis code path inject a fake client instead.
    """
    import cache
    import config
    import rate_limit
    import sessions
    import shared

    monkeypatch.setattr(config, "REDIS_URL", None)
    cache.clear()
    rate_limit.clear()
    shared.reset()
    sessions.reset_store()
    yield
    cache.clear()
    rate_limit.clear()
    shared.reset()
    sessions.reset_store()
