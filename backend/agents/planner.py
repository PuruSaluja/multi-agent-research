import json
from datetime import datetime, timezone

import cache
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
    try:
        # A repeated question reuses its earlier plan. The search cache is keyed
        # on sub-question text, so a freshly reworded plan would miss it.
        sub_tasks = cache.get_plan(state["query"])
        action = "Reused sub-tasks from a recent run"
        if sub_tasks is None:
            message = get_client().messages.create(
                model=config.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": state["query"]}],
            )
            sub_tasks = parse_task_list(message.content[0].text)
            cache.set_plan(state["query"], sub_tasks)
            action = "Generated sub-tasks"

        logs = emit_log(list(state.get("agent_logs", [])), {
            "agent": "Planner",
            "action": action,
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
