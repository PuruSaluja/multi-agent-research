import time

import pytest
from fastapi.testclient import TestClient

import config
import main
from main import Session, app, reap_stale_sessions, sessions


@pytest.fixture(autouse=True)
def _clean_sessions():
    sessions.clear()
    yield
    sessions.clear()


@pytest.fixture
def client(monkeypatch):
    # Routing and agents have their own suites.
    monkeypatch.setattr(main, "_run_graph_streaming", lambda *a, **k: None)
    with TestClient(app) as c:
        yield c


def test_health_reports_model_and_session_count(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["model"] == config.ANTHROPIC_MODEL
    assert body["active_sessions"] == 0


def test_empty_query_rejected(client):
    assert client.post("/api/research", json={"query": "   "}).status_code == 400


def test_research_returns_a_session_id(client):
    body = client.post("/api/research", json={"query": "why"}).json()
    assert body["session_id"] in sessions


def test_unknown_session_stream_is_404(client):
    assert client.get("/api/research/nope/stream").status_code == 404


def test_backpressure_returns_429(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_ACTIVE_SESSIONS", 2)
    assert client.post("/api/research", json={"query": "a"}).status_code == 200
    assert client.post("/api/research", json={"query": "b"}).status_code == 200
    r = client.post("/api/research", json={"query": "c"})
    assert r.status_code == 429


def test_abandoned_sessions_are_reaped(monkeypatch):
    """A POST whose client never opens the stream must not leak a queue."""
    monkeypatch.setattr(config, "SESSION_TTL_SECONDS", 60)
    now = time.monotonic()
    sessions["fresh"] = Session(created_at=now)
    sessions["stale"] = Session(created_at=now - 3600)

    removed = reap_stale_sessions(now=now)

    assert removed == 1
    assert "fresh" in sessions and "stale" not in sessions
