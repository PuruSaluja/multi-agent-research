from datetime import datetime, timezone

import config
from agents.planner import parse_task_list
from events import emit_log
from llm import get_client
from models import ResearchState

SYSTEM_PROMPT = (
    "You are a search query specialist. You will be given research "
    "sub-questions that returned no useful web results. Rewrite each one so it "
    "is more likely to match indexed pages: prefer concrete nouns and proper "
    "names over abstractions, drop conversational phrasing, and broaden any "
    "term that is too niche. Return ONLY a JSON array of strings, the same "
    "length as the input."
)


def refiner_node(state: ResearchState) -> dict:
    """Rewrite sub-questions that came back empty so they can be retried."""
    unanswered = state.get("unanswered_tasks", [])
    logs = list(state.get("agent_logs", []))
    retry_count = state.get("retry_count", 0) + 1

    if not unanswered:
        return {"retry_count": retry_count, "current_agent": "Refiner", "error": None}

    client = get_client()
    try:
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Original question: {state['query']}\n\n"
                        f"Sub-questions that found nothing:\n"
                        + "\n".join(f"- {t}" for t in unanswered)
                    ),
                }
            ],
        )
        refined = parse_task_list(message.content[0].text)
    except Exception as e:
        # Not fatal: fall through to analysis with what the first pass found.
        emit_log(logs, {
            "agent": "Refiner",
            "action": "Refinement failed, continuing with existing results",
            "detail": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "unanswered_tasks": [],
            "retry_count": retry_count,
            "agent_logs": logs,
            "current_agent": "Refiner",
            "error": None,
        }

    emit_log(logs, {
        "agent": "Refiner",
        "action": f"Rewrote {len(refined)} unproductive sub-question(s)",
        "detail": refined,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    return {
        "sub_tasks": state.get("sub_tasks", []) + refined,
        "unanswered_tasks": refined,
        "retry_count": retry_count,
        "agent_logs": logs,
        "current_agent": "Refiner",
        "error": None,
    }
