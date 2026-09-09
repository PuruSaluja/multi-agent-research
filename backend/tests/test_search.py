import pytest

import config
from tools import search as search_mod
from tools.search import SearchError, search_web


class FakeTavily:
    def __init__(self, behaviour):
        self.behaviour = behaviour
        self.calls = 0

    def search(self, **kwargs):
        self.calls += 1
        result = self.behaviour(self.calls)
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture(autouse=True)
def _fast_retries(monkeypatch):
    monkeypatch.setattr(config, "SEARCH_BACKOFF_SECONDS", 0.0)
    monkeypatch.setattr(config, "SEARCH_MAX_ATTEMPTS", 3)


def _install(monkeypatch, behaviour):
    fake = FakeTavily(behaviour)
    monkeypatch.setattr(search_mod, "get_client", lambda: fake)
    return fake


def test_returns_normalized_results(monkeypatch):
    _install(
        monkeypatch,
        lambda n: {
            "results": [
                {"title": "T", "url": "https://e.com", "content": "x" * 900},
                {"title": "U", "url": "https://f.com"},
            ]
        },
    )
    results = search_web("q")
    assert [r["url"] for r in results] == ["https://e.com", "https://f.com"]
    # Content is truncated to 500 chars, and a missing content field is safe.
    assert len(results[0]["content"]) == 500
    assert results[1]["content"] == ""


def test_empty_results_is_not_an_error(monkeypatch):
    _install(monkeypatch, lambda n: {"results": []})
    assert search_web("q") == []


def test_persistent_failure_raises_rather_than_returning_empty(monkeypatch):
    """The original bug: an outage returned [] and looked like 'no results'."""
    fake = _install(monkeypatch, lambda n: RuntimeError("connection refused"))
    with pytest.raises(SearchError) as exc:
        search_web("q")
    assert "connection refused" in str(exc.value)
    assert fake.calls == config.SEARCH_MAX_ATTEMPTS


def test_transient_failure_is_retried(monkeypatch):
    fake = _install(
        monkeypatch,
        lambda n: RuntimeError("flaky") if n == 1 else {"results": [
            {"title": "T", "url": "https://e.com", "content": "ok"}
        ]},
    )
    assert len(search_web("q")) == 1
    assert fake.calls == 2
