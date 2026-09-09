"""Runs the real compiled LangGraph with the LLM and search layers faked.

Routing unit tests prove the predicates; these prove the wiring -- that the
refiner edge is reachable, that the cycle terminates, and that a fatal node
short-circuits to the error handler.
"""
from contextlib import contextmanager

import pytest

import config
import events
from agents import analyst as analyst_mod
from agents import planner as planner_mod
from agents import refiner as refiner_mod
from agents import researcher as researcher_mod
from agents import writer as writer_mod
from graph import compiled_graph
from tools.search import SearchError


class FakeMessages:
    def __init__(self, text, chunks=None):
        self.text = text
        self.chunks = chunks or [text]

    def create(self, **kwargs):
        block = type("B", (), {"text": self.text})()
        return type("M", (), {"content": [block]})()

    @contextmanager
    def stream(self, **kwargs):
        outer = self

        class _S:
            text_stream = iter(outer.chunks)

        yield _S()


def _client(text, chunks=None):
    return type("C", (), {"messages": FakeMessages(text, chunks)})()


INITIAL = {
    "query": "why is the sky blue",
    "sub_tasks": [],
    "search_results": {},
    "analysis": "",
    "final_report": "",
    "agent_logs": [],
    "current_agent": "",
    "error": None,
    "unanswered_tasks": [],
    "retry_count": 0,
}


@pytest.fixture(autouse=True)
def _fast(monkeypatch):
    monkeypatch.setattr(config, "SEARCH_PACING_SECONDS", 0.0)
    monkeypatch.setattr(config, "MAX_RESEARCH_RETRIES", 1)
    monkeypatch.setattr(config, "MIN_COVERAGE_RATIO", 0.6)


def _wire_llms(monkeypatch, plan, refined):
    monkeypatch.setattr(planner_mod, "get_client", lambda: _client(plan))
    monkeypatch.setattr(refiner_mod, "get_client", lambda: _client(refined))
    monkeypatch.setattr(analyst_mod, "get_client", lambda: _client("ANALYSIS"))
    monkeypatch.setattr(
        writer_mod, "get_client", lambda: _client("REPORT", ["RE", "PORT"])
    )


def _run():
    final = dict(INITIAL)
    for chunk in compiled_graph.stream(dict(INITIAL), stream_mode="updates"):
        for _node, out in chunk.items():
            for k, v in out.items():
                if v is not None:
                    final[k] = v
    return final


def test_happy_path_never_visits_the_refiner(monkeypatch):
    _wire_llms(monkeypatch, '["a", "b"]', '["x"]')
    monkeypatch.setattr(
        researcher_mod,
        "search_web",
        lambda t, max_results=None: [{"title": "T", "url": f"https://{t}.com", "content": "c"}],
    )

    final = _run()

    assert final["error"] is None
    assert final["retry_count"] == 0
    assert final["final_report"] == "REPORT"
    assert not any(log["agent"] == "Refiner" for log in final["agent_logs"])


def test_thin_pass_loops_through_the_refiner_then_completes(monkeypatch):
    """planner -> researcher (thin) -> refiner -> researcher -> analyst -> writer."""
    _wire_llms(monkeypatch, '["a", "b", "c"]', '["a-refined", "b-refined"]')

    def search(task, max_results=None):
        # Only the original "c" and the refined queries return anything.
        if task in ("c", "a-refined", "b-refined"):
            return [{"title": "T", "url": f"https://{task}.com", "content": "c"}]
        return []

    monkeypatch.setattr(researcher_mod, "search_web", search)

    final = _run()

    assert final["error"] is None
    assert final["retry_count"] == 1
    refiner_logs = [l for l in final["agent_logs"] if l["agent"] == "Refiner"]
    assert len(refiner_logs) == 1
    assert set(final["search_results"]) == {"c", "a-refined", "b-refined"}
    assert final["final_report"] == "REPORT"


def test_retry_loop_terminates_when_refinement_never_helps(monkeypatch):
    """The cycle must be bounded even if every pass stays empty."""
    _wire_llms(monkeypatch, '["a", "b"]', '["a2", "b2"]')
    monkeypatch.setattr(researcher_mod, "search_web", lambda t, max_results=None: [])

    final = _run()

    # One refine round, then the Analyst refuses rather than inventing an answer.
    assert final["retry_count"] == 1
    assert final["error"] and "nothing to synthesize" in final["error"]


def test_total_search_failure_short_circuits_to_error(monkeypatch):
    _wire_llms(monkeypatch, '["a", "b"]', '["x"]')
    monkeypatch.setattr(
        researcher_mod,
        "search_web",
        lambda t, max_results=None: (_ for _ in ()).throw(SearchError("down")),
    )

    final = _run()

    assert final["current_agent"] == "Error"
    assert "every search request failed" in final["error"]
    assert final["final_report"] == ""


def test_report_tokens_are_emitted_during_a_full_run(monkeypatch):
    _wire_llms(monkeypatch, '["a"]', '["x"]')
    monkeypatch.setattr(
        researcher_mod,
        "search_web",
        lambda t, max_results=None: [{"title": "T", "url": "https://a.com", "content": "c"}],
    )

    seen = []
    events.set_emitter(lambda t, d: seen.append((t, d)))
    try:
        final = _run()
    finally:
        events.set_emitter(None)

    assert [t for t, _ in seen] == ["report_token", "report_token"]
    assert "".join(d["text"] for _, d in seen) == final["final_report"]
