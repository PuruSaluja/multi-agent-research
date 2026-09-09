import time

from tavily import TavilyClient

import config

_client: TavilyClient | None = None


class SearchError(RuntimeError):
    """A search could not be completed.

    Distinct from a search that completed and found nothing -- that is an empty
    list. Collapsing the two is how a total API outage turns into a confident
    report written from no sources.
    """


def get_client() -> TavilyClient:
    global _client
    if _client is None:
        import os

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise SearchError("TAVILY_API_KEY environment variable not set")
        _client = TavilyClient(api_key=api_key)
    return _client


def reset_client() -> None:
    """Drop the memoized client. Used by tests."""
    global _client
    _client = None


def search_web(query: str, max_results: int | None = None) -> list[dict]:
    """Search the web via Tavily and return the top results.

    Returns an empty list when the search ran but matched nothing. Raises
    SearchError when the search could not be run at all -- the caller needs
    that distinction to decide whether the research is trustworthy.
    """
    if max_results is None:
        max_results = config.SEARCH_MAX_RESULTS

    client = get_client()
    last_error: Exception | None = None

    for attempt in range(1, config.SEARCH_MAX_ATTEMPTS + 1):
        try:
            response = client.search(
                query=query,
                max_results=max_results,
                search_depth="basic",
            )
        except Exception as exc:  # noqa: BLE001 - Tavily raises bare Exceptions
            last_error = exc
            if attempt < config.SEARCH_MAX_ATTEMPTS:
                time.sleep(config.SEARCH_BACKOFF_SECONDS * attempt)
            continue

        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": (r.get("content") or "")[:500],
            }
            for r in response.get("results", [])
        ]

    raise SearchError(
        f"Search failed after {config.SEARCH_MAX_ATTEMPTS} attempts: {last_error}"
    )
