"""Search result and research plan cache, backed by Redis when configured.

Falls back to a bounded in-process dict so a single worker still benefits.
Cache misses and backend errors are never fatal: a failure here degrades to
"not cached", never to a failed run.

Plans are cached as well as search results because the Planner rewords its
sub-questions on every call. Without a stable plan, a repeated question
produces different search strings and almost every lookup misses.
"""
import json
import threading
import time
from collections import OrderedDict

import config
from shared import get_redis

_local: "OrderedDict[str, tuple[float, list]]" = OrderedDict()
_lock = threading.Lock()


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _key(query: str, max_results: int) -> str:
    return f"search:{max_results}:{_normalize(query)}"


def _plan_key(query: str) -> str:
    return f"plan:{_normalize(query)}"


def _get(key: str):
    if config.SEARCH_CACHE_TTL_SECONDS <= 0:
        return None

    redis = get_redis()
    if redis is not None:
        try:
            raw = redis.get(key)
            return json.loads(raw) if raw else None
        except Exception:
            return None

    with _lock:
        entry = _local.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if expires_at < time.time():
            _local.pop(key, None)
            return None
        _local.move_to_end(key)
        return value


def _put(key: str, value) -> None:
    if config.SEARCH_CACHE_TTL_SECONDS <= 0:
        return

    redis = get_redis()
    if redis is not None:
        try:
            redis.setex(key, config.SEARCH_CACHE_TTL_SECONDS, json.dumps(value))
        except Exception:
            pass
        return

    with _lock:
        _local[key] = (time.time() + config.SEARCH_CACHE_TTL_SECONDS, value)
        _local.move_to_end(key)
        while len(_local) > config.SEARCH_CACHE_MAX_ENTRIES:
            _local.popitem(last=False)


def get(query: str, max_results: int) -> list | None:
    return _get(_key(query, max_results))


def set(query: str, max_results: int, results: list) -> None:
    _put(_key(query, max_results), results)


def get_plan(query: str) -> list[str] | None:
    return _get(_plan_key(query))


def set_plan(query: str, sub_tasks: list[str]) -> None:
    _put(_plan_key(query), sub_tasks)


def clear() -> None:
    with _lock:
        _local.clear()
