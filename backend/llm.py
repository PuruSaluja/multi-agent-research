"""Shared Anthropic client.

One memoized client for every agent, so the API key is read once and the model
choice lives in ``config`` rather than being repeated at each call site.
"""
import os

from anthropic import Anthropic

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


def reset_client() -> None:
    """Drop the memoized client. Used by tests."""
    global _client
    _client = None
