"""Hosted Postgres URLs are routed to the installed driver."""
import pytest

from db import normalize_url


@pytest.mark.parametrize(
    "given",
    [
        "postgresql://u:p@host:5432/db",  # Render's form
        "postgres://u:p@host:5432/db",  # rejected by SQLAlchemy 2 as-is
    ],
)
def test_bare_postgres_urls_use_psycopg(given):
    assert normalize_url(given) == "postgresql+psycopg://u:p@host:5432/db"


@pytest.mark.parametrize(
    "given",
    [
        "postgresql+psycopg://u:p@host/db",  # already explicit
        "sqlite:///./data/app.db",
        "sqlite:///:memory:",
    ],
)
def test_other_urls_are_untouched(given):
    assert normalize_url(given) == given
