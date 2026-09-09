import importlib

import pytest


@pytest.fixture
def reloaded_config(monkeypatch):
    def _load(**env):
        for k, v in env.items():
            monkeypatch.setenv(k, v)
        import config

        return importlib.reload(config)

    yield _load
    import config

    importlib.reload(config)


def test_defaults_to_local_dev_origins(reloaded_config, monkeypatch):
    monkeypatch.delenv("CORS_ALLOW_ORIGINS", raising=False)
    monkeypatch.delenv("CORS_ALLOW_ORIGIN_REGEX", raising=False)
    cfg = reloaded_config()
    assert cfg.CORS_ALLOW_ORIGINS == [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    assert cfg.CORS_ALLOW_ORIGIN_REGEX is None


def test_deployed_origins_are_configurable(reloaded_config):
    """The original bug: only localhost was allowed, so a Vercel frontend
    calling a Render backend was blocked."""
    cfg = reloaded_config(
        CORS_ALLOW_ORIGINS="https://app.vercel.app, https://www.example.com",
        CORS_ALLOW_ORIGIN_REGEX=r"https://mar-.*\.vercel\.app",
    )
    assert cfg.CORS_ALLOW_ORIGINS == [
        "https://app.vercel.app",
        "https://www.example.com",
    ]
    assert cfg.CORS_ALLOW_ORIGIN_REGEX == r"https://mar-.*\.vercel\.app"


def test_model_id_is_configurable(reloaded_config):
    assert reloaded_config(ANTHROPIC_MODEL="claude-opus-5").ANTHROPIC_MODEL == (
        "claude-opus-5"
    )
