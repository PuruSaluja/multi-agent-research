import os
import time
from tavily import TavilyClient

_client: TavilyClient | None = None


def get_client() -> TavilyClient:
    global _client
    if _client is None:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable not set")
        _client = TavilyClient(api_key=api_key)
    return _client


def search_web(query: str, max_results: int = 3) -> list[dict]:
    """Search the web using Tavily and return top results."""
    client = get_client()
    try:
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
        )
        results = []
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:500],  # truncate to 500 chars
            })
        return results
    except Exception as e:
        return []
