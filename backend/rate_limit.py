"""Fixed-window rate limiting, backed by Redis when configured.

Like the cache, it falls back to an in-process counter, which is exact for a
single worker. A Redis failure lets the request through rather than locking
everyone out: this guards against bulk sign-ups, it is not an auth control.
"""
import threading
import time

from shared import get_redis

_local: dict[str, tuple[float, int]] = {}
_lock = threading.Lock()


def hit(bucket: str, key: str, limit: int, window_seconds: int) -> int | None:
    """Count one attempt. Returns None if allowed, else seconds until it is.

    A limit of 0 or less disables the check.
    """
    if limit <= 0:
        return None
    name = f"ratelimit:{bucket}:{key}"

    redis = get_redis()
    if redis is not None:
        try:
            count = redis.incr(name)
            if count == 1:
                redis.expire(name, window_seconds)
            if count > limit:
                ttl = redis.ttl(name)
                return ttl if ttl and ttl > 0 else window_seconds
            return None
        except Exception:
            return None

    now = time.time()
    with _lock:
        started, count = _local.get(name, (now, 0))
        if now - started >= window_seconds:
            started, count = now, 0
        count += 1
        _local[name] = (started, count)
        if count > limit:
            return max(1, int(started + window_seconds - now))
    return None


def clear() -> None:
    with _lock:
        _local.clear()
