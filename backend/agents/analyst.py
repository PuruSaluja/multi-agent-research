import json
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
    "You are a research analyst. You have been given a set of web search "
    "results for several sub-questions. Synthesize the key findings, note any "
    "contradictions between sources, identify what is well-supported vs "
    "uncertain, and summarize the overall picture in 3-4 paragraphs."
)


def _format_results(search_results: dict[str, list]) -> str:
    parts = []
    for task, results in search_results.items():
        parts.append(f"Sub-question: {task}")
        for i, r in enumerate(results, 1):
            parts.append(f"  [{i}] {r['title']}")
            parts.append(f"      URL: {r['url']}")
            parts.append(f"      Content: {r['content']}")
        parts.append("")
    return "\n".join(parts)


def analyst_node(state: ResearchState) -> dict:
    client = get_client()
    logs = list(state.get("agent_logs", []))

    try:
        context = _format_results(state.get("search_results", {}))
        user_message = (
            f"Original question: {state['query']}\n\n"
            f"Search results:\n{context}"
        )

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        analysis = message.content[0].text.strip()

        logs.append({
            "agent": "Analyst",
            "action": "Synthesized findings",
            "detail": f"Analyzed {len(state.get('search_results', {}))} sub-questions",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "analysis": analysis,
            "agent_logs": logs,
            "current_agent": "Analyst",
            "error": None,
        }
    except Exception as e:
        return {
            "agent_logs": logs,
            "current_agent": "Analyst",
            "error": f"Analyst failed: {str(e)}",
        }
