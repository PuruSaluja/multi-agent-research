import os
from datetime import datetime, timezone

from anthropic import Anthropic

from models import ResearchState

_client: Anthropic | None = None


def get_client() -> Anthropic:
    global _client
    if _client is None:
        _client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return _client


SYSTEM_PROMPT = (
    "You are a research writer. Given an analysis and the original sources, "
    "write a comprehensive research report in Markdown format. Include: an "
    "Executive Summary, 3-5 sections covering the main findings, a Limitations "
    "section, and a numbered References list with URLs. Use clear headers (##). "
    "Be thorough but concise."
)


def _collect_sources(search_results: dict[str, list]) -> list[dict]:
    seen_urls: set[str] = set()
    sources = []
    for results in search_results.values():
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                sources.append(r)
    return sources


def writer_node(state: ResearchState) -> dict:
    client = get_client()
    logs = list(state.get("agent_logs", []))
    sources = _collect_sources(state.get("search_results", {}))

    try:
        sources_text = "\n".join(
            f"[{i+1}] {s['title']} — {s['url']}"
            for i, s in enumerate(sources)
        )
        user_message = (
            f"Original question: {state['query']}\n\n"
            f"Analysis:\n{state.get('analysis', '')}\n\n"
            f"Available sources:\n{sources_text}"
        )

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        final_report = message.content[0].text.strip()

        logs.append({
            "agent": "Writer",
            "action": "Report complete",
            "detail": f"Generated report with {len(sources)} sources",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "final_report": final_report,
            "agent_logs": logs,
            "current_agent": "Writer",
            "error": None,
        }
    except Exception as e:
        return {
            "agent_logs": logs,
            "current_agent": "Writer",
            "error": f"Writer failed: {str(e)}",
        }
