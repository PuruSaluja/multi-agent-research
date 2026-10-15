"""Sign-up rate limiting, over HTTP and in the limiter itself."""
import pytest
from fastapi.testclient import TestClient

import config
import db
import main
import rate_limit
from main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATABASE_URL", f"sqlite:///{tmp_path / 'rl.db'}")
    monkeypatch.setattr(config, "AUTH_SECRET", "t" * 48)
    monkeypatch.setattr(config, "REGISTER_RATE_LIMIT", 2)
    monkeypatch.setattr(main, "_run_graph_streaming", lambda *a, **k: None)
    db.reset()
    with TestClient(app) as c:
        yield c
    db.reset()


def register(client, n):
    return client.post(
        "/api/auth/register",
        json={"email": f"user{n}@example.com", "password": "a-long-passphrase"},
    )


def test_registration_is_throttled_per_ip(client):
    assert register(client, 1).status_code == 201
    assert register(client, 2).status_code == 201

    r = register(client, 3)
    assert r.status_code == 429
    assert int(r.headers["Retry-After"]) > 0


def test_failed_attempts_count_too(client):
    # Retrying a taken email must not be a free way around the limit.
    assert register(client, 1).status_code == 201
    assert register(client, 1).status_code == 409
    assert register(client, 2).status_code == 429


def test_login_is_not_throttled_by_the_signup_limit(client):
    register(client, 1)
    register(client, 2)
    register(client, 3)  # limited
    r = client.post(
        "/api/auth/login",
        json={"email": "user1@example.com", "password": "a-long-passphrase"},
    )
    assert r.status_code == 200


def test_zero_disables_the_limit(client, monkeypatch):
    monkeypatch.setattr(config, "REGISTER_RATE_LIMIT", 0)
    for n in range(5):
        assert register(client, n).status_code == 201


def test_limits_are_per_key():
    assert rate_limit.hit("register", "1.1.1.1", 1, 60) is None
    assert rate_limit.hit("register", "1.1.1.1", 1, 60) is not None
    assert rate_limit.hit("register", "2.2.2.2", 1, 60) is None


def test_window_resets(monkeypatch):
    clock = {"t": 1000.0}
    monkeypatch.setattr(rate_limit.time, "time", lambda: clock["t"])

    assert rate_limit.hit("b", "k", 1, 60) is None
    assert rate_limit.hit("b", "k", 1, 60) is not None
    clock["t"] += 61
    assert rate_limit.hit("b", "k", 1, 60) is None


def test_redis_path_counts_and_reports_ttl(monkeypatch):
    import shared

    class FakeRedis:
        def __init__(self):
            self.n = 0
            self.expiry = None

        def incr(self, key):
            self.n += 1
            return self.n

        def expire(self, key, seconds):
            self.expiry = seconds

        def ttl(self, key):
            return 42

    fake = FakeRedis()
    monkeypatch.setattr(shared, "_redis", fake)
    monkeypatch.setattr(shared, "_checked", True)

    assert rate_limit.hit("register", "ip", 1, 3600) is None
    assert fake.expiry == 3600  # window starts on the first hit
    assert rate_limit.hit("register", "ip", 1, 3600) == 42


def test_redis_failure_lets_requests_through(monkeypatch):
    import shared

    class Broken:
        def incr(self, key):
            raise ConnectionError("redis down")

    monkeypatch.setattr(shared, "_redis", Broken())
    monkeypatch.setattr(shared, "_checked", True)
    assert rate_limit.hit("register", "ip", 1, 60) is None
