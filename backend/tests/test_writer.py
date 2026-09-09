from contextlib import contextmanager

import events
from agents import writer as writer_mod
from agents.writer import collect_sources, writer_node


class FakeStreamClient:
    def __init__(self, chunks):
        self.chunks = chunks
        self.messages = self

    @contextmanager
    def stream(self, **kwargs):
        outer = self

        class _S:
            text_stream = iter(outer.chunks)

        yield _S()


def test_collect_sources_dedupes_preserving_order():
    results = {
        "a": [
            {"title": "A", "url": "https://x.com", "content": ""},
            {"title": "B", "url": "https://y.com", "content": ""},
        ],
        "b": [{"title": "A again", "url": "https://x.com", "content": ""}],
    }
    assert [s["url"] for s in collect_sources(results)] == [
        "https://x.com",
        "https://y.com",
    ]


def test_writer_streams_tokens_and_returns_assembled_report(monkeypatch):
    """The dev log claimed token streaming; this is it actually happening."""
    monkeypatch.setattr(
        writer_mod, "get_client", lambda: FakeStreamClient(["# Title", "\n\nBody."])
    )

    seen = []
    events.set_emitter(lambda t, d: seen.append((t, d)))
    try:
        out = writer_node({
            "query": "q",
            "analysis": "a",
            "search_results": {"a": [{"title": "T", "url": "https://x.com", "content": ""}]},
            "agent_logs": [],
        })
    finally:
        events.set_emitter(None)

    assert [t for t, _ in seen] == ["report_token", "report_token"]
    assert "".join(d["text"] for _, d in seen) == "# Title\n\nBody."
    assert out["final_report"] == "# Title\n\nBody."
    assert out["error"] is None


def test_writer_reports_failure_instead_of_raising(monkeypatch):
    class Boom:
        messages = None

        def __getattr__(self, name):
            raise RuntimeError("api down")

    monkeypatch.setattr(writer_mod, "get_client", lambda: Boom())
    out = writer_node({"query": "q", "analysis": "a", "search_results": {}, "agent_logs": []})
    assert out["error"] and "Writer failed" in out["error"]


def test_emit_without_an_emitter_is_a_noop():
    events.set_emitter(None)
    events.emit("report_token", {"text": "x"})  # must not raise
