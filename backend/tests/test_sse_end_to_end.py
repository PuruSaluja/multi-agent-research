"""Drives the real app over HTTP and parses the actual SSE stream.

The other API tests stub the graph out, so the worker thread, emitter, queue
hand-off and SSE framing were never covered together. Only the Anthropic and
Tavily clients are faked here.
"""
import json
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

import config
from agents import analyst as analyst_mod
from agents import planner as planner_mod
from agents import refiner as refiner_mod
from agents import researcher as researcher_mod
from agents import writer as writer_mod
from main import app, sessions

REPORT_CHUNKS = ["## Executive Summary\n\n", "Water is wet.\n\n", "## References\n[1] ..."]


class FakeMessages:
    def __init__(self, text, chunks):
        self._text = text
        self._chunks = chunks

    def create(self, **kwargs):
        block = type("B", (), {"text": self._text})()
        return type("M", (), {"content": [block]})()

    @contextmanager
    def stream(self, **kwargs):
        chunks = self._chunks

        class _S:
            text_stream = iter(chunks)

        yield _S()


def _client(text, chunks=None):
    return type("C", (), {"messages": FakeMessages(text, chunks or [text])})()


@pytest.fixture(autouse=True)
def _wire(monkeypatch):
    sessions.clear()
    monkeypatch.setattr(config, "SEARCH_PACING_SECONDS", 0.0)
    monkeypatch.setattr(planner_mod, "get_client", lambda: _client('["a", "b"]'))
    monkeypatch.setattr(refiner_mod, "get_client", lambda: _client('["a2"]'))
    monkeypatch.setattr(analyst_mod, "get_client", lambda: _client("ANALYSIS"))
    monkeypatch.setattr(
        writer_mod, "get_client", lambda: _client("".join(REPORT_CHUNKS), REPORT_CHUNKS)
    )
    monkeypatch.setattr(
        researcher_mod,
        "search_web",
        lambda t, max_results=None: [
            {"title": f"Source for {t}", "url": f"https://{t}.example.com", "content": "c"}
        ],
    )
    yield
    sessions.clear()


def read_sse(response):
    """Parse an SSE byte stream into (event, data) pairs."""
    events, event = [], None
    for raw in response.iter_lines():
        line = raw if isinstance(raw, str) else raw.decode()
        if line.startswith("event: "):
            event = line[len("event: ") :]
        elif line.startswith("data: "):
            events.append((event, json.loads(line[len("data: ") :])))
        elif line.startswith(":"):
            continue  # keepalive
    return events


def test_full_run_streams_the_report_over_real_sse():
    with TestClient(app) as client:
        session_id = client.post(
            "/api/research", json={"query": "is water wet"}
        ).json()["session_id"]

        with client.stream("GET", f"/api/research/{session_id}/stream") as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            events = read_sse(r)

    kinds = [k for k, _ in events]

    # The contract the frontend is written against.
    assert kinds[-1] == "complete"
    assert "agent_update" in kinds
    assert "report_token" in kinds
    assert "error" not in kinds

    # Progress arrives before the report starts.
    assert kinds.index("agent_update") < kinds.index("report_token")

    # Streamed chunks reassemble into exactly the final report.
    streamed = "".join(d["text"] for k, d in events if k == "report_token")
    final = dict(events[-1][1])
    assert streamed == "".join(REPORT_CHUNKS)
    assert final["final_report"] == streamed
    assert len(final["sources"]) == 2
    assert final["sub_tasks"] == ["a", "b"]


def test_session_is_dropped_after_the_stream_completes():
    with TestClient(app) as client:
        session_id = client.post("/api/research", json={"query": "q"}).json()["session_id"]
        with client.stream("GET", f"/api/research/{session_id}/stream") as r:
            read_sse(r)

        assert session_id not in sessions
        # A second connection to a finished run is a clean 404, not a hang.
        assert client.get(f"/api/research/{session_id}/stream").status_code == 404


def test_search_outage_surfaces_as_an_error_event(monkeypatch):
    from tools.search import SearchError

    monkeypatch.setattr(
        researcher_mod,
        "search_web",
        lambda t, max_results=None: (_ for _ in ()).throw(SearchError("tavily down")),
    )

    with TestClient(app) as client:
        session_id = client.post("/api/research", json={"query": "q"}).json()["session_id"]
        with client.stream("GET", f"/api/research/{session_id}/stream") as r:
            events = read_sse(r)

    kinds = [k for k, _ in events]
    assert kinds[-1] == "error"
    assert "report_token" not in kinds
    assert "every search request failed" in events[-1][1]["message"]
