from datetime import datetime, timezone

import config
from events import emit_log
from llm import get_client
from models import ResearchState

SYSTEM_PROMPT = (
    "You are a research analyst. You have been given a set of web search "
    "results for several sub-questions. Synthesize the key findings, note any "
    "contradictions between sources, identify what is well-supported vs "
    "uncertain, and summarize the overall picture in 3-4 paragraphs. If some "
    "sub-questions returned no sources, say plainly which parts of the "
    "question remain unevidenced rather than filling the gap from memory."
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
    logs = list(state.get("agent_logs", []))
    search_results = state.get("search_results", {})

    if not search_results:
        return {
            "agent_logs": logs,
            "current_agent": "Analyst",
            "error": (
                "Analyst failed: no search results were gathered, so there is "
                "nothing to synthesize."
            ),
        }

    client = get_client()
    try:
        unanswered = state.get("unanswered_tasks", [])
        gaps = (
            "\n\nSub-questions that returned no sources:\n"
            + "\n".join(f"- {t}" for t in unanswered)
            if unanswered
            else ""
        )
        user_message = (
            f"Original question: {state['query']}\n\n"
            f"Search results:\n{_format_results(search_results)}{gaps}"
        )

        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        analysis = message.content[0].text.strip()

        emit_log(logs, {
            "agent": "Analyst",
            "action": "Synthesized findings",
            "detail": f"Analyzed {len(search_results)} sub-questions",
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
            "error": f"Analyst failed: {e}",
        }
