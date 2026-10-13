"""A repeated question reuses its plan, so its searches hit the cache.

The Planner rewords sub-questions on every call. Without a cached plan, a
repeated question produces new search strings and the search cache misses.
"""
from agents import planner as planner_mod


class CountingClient:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = 0
        outer = self

        class Messages:
            def create(self, **kw):
                outer.calls += 1
                text = outer.replies.pop(0)
                block = type("B", (), {"text": text})()
                return type("M", (), {"content": [block]})()

        self.messages = Messages()


def state(query):
    return {"query": query, "agent_logs": []}


def test_repeated_question_reuses_the_plan(monkeypatch):
    client = CountingClient(['["a", "b"]', '["reworded a", "reworded b"]'])
    monkeypatch.setattr(planner_mod, "get_client", lambda: client)

    first = planner_mod.planner_node(state("Why is the sky blue?"))
    second = planner_mod.planner_node(state("why is the  SKY blue?"))

    assert client.calls == 1, "second run should not call the model"
    assert first["sub_tasks"] == second["sub_tasks"] == ["a", "b"]
    assert second["agent_logs"][-1]["action"] == "Reused sub-tasks from a recent run"


def test_different_questions_get_their_own_plans(monkeypatch):
    client = CountingClient(['["a"]', '["b"]'])
    monkeypatch.setattr(planner_mod, "get_client", lambda: client)

    assert planner_mod.planner_node(state("q one"))["sub_tasks"] == ["a"]
    assert planner_mod.planner_node(state("q two"))["sub_tasks"] == ["b"]
    assert client.calls == 2


def test_a_failed_plan_is_not_cached(monkeypatch):
    client = CountingClient(["not json", '["recovered"]'])
    monkeypatch.setattr(planner_mod, "get_client", lambda: client)

    assert planner_mod.planner_node(state("q"))["error"]
    assert planner_mod.planner_node(state("q"))["sub_tasks"] == ["recovered"]


def test_plan_cache_respects_the_disable_switch(monkeypatch):
    import config

    monkeypatch.setattr(config, "SEARCH_CACHE_TTL_SECONDS", 0)
    client = CountingClient(['["a"]', '["b"]'])
    monkeypatch.setattr(planner_mod, "get_client", lambda: client)

    planner_mod.planner_node(state("q"))
    planner_mod.planner_node(state("q"))
    assert client.calls == 2
