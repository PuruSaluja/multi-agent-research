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
    "You are a research planner. Given a user's question, break it down into "
    "3-5 specific, searchable sub-questions that together would fully answer "
    "the original query. Return ONLY a JSON array of strings."
)


def planner_node(state: ResearchState) -> dict:
    client = get_client()
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": state["query"]}],
        )
        raw = message.content[0].text.strip()

        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        sub_tasks = json.loads(raw)
        if not isinstance(sub_tasks, list):
            raise ValueError("LLM did not return a JSON array")

        log_entry = {
            "agent": "Planner",
            "action": "Generated sub-tasks",
            "detail": sub_tasks,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return {
            "sub_tasks": sub_tasks,
            "agent_logs": state.get("agent_logs", []) + [log_entry],
            "current_agent": "Planner",
            "error": None,
        }
    except Exception as e:
        return {
            "error": f"Planner failed: {str(e)}",
            "current_agent": "Planner",
            "agent_logs": state.get("agent_logs", []),
        }
