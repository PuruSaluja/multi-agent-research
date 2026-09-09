import json
from datetime import datetime, timezone

import config
from events import emit_log
from llm import get_client
from models import ResearchState

SYSTEM_PROMPT = (
    "You are a research planner. Given a user's question, break it down into "
    "3-5 specific, searchable sub-questions that together would fully answer "
    "the original query. Return ONLY a JSON array of strings."
)


def parse_task_list(raw: str) -> list[str]:
    """Parse a JSON array of strings out of an LLM response.

    Tolerates the model wrapping its answer in a Markdown code fence.
    """
    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) > 1:
            raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    tasks = json.loads(raw)
    if not isinstance(tasks, list) or not all(isinstance(t, str) for t in tasks):
        raise ValueError("LLM did not return a JSON array of strings")
    return tasks


def planner_node(state: ResearchState) -> dict:
    client = get_client()
    try:
        message = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": state["query"]}],
        )
        sub_tasks = parse_task_list(message.content[0].text)

        logs = emit_log(list(state.get("agent_logs", [])), {
            "agent": "Planner",
            "action": "Generated sub-tasks",
            "detail": sub_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return {
            "sub_tasks": sub_tasks,
            "unanswered_tasks": [],
            "retry_count": 0,
            "agent_logs": logs,
            "current_agent": "Planner",
            "error": None,
        }
    except Exception as e:
        return {
            "error": f"Planner failed: {e}",
            "current_agent": "Planner",
            "agent_logs": state.get("agent_logs", []),
        }
