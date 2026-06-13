import time
from datetime import datetime, timezone

from models import ResearchState
from tools.search import search_web


def researcher_node(state: ResearchState) -> dict:
    sub_tasks = state.get("sub_tasks", [])
    search_results: dict[str, list] = {}
    logs = list(state.get("agent_logs", []))

    try:
        for task in sub_tasks:
            results = search_web(task, max_results=3)

            if not results:
                logs.append({
                    "agent": "Researcher",
                    "action": "No results found",
                    "detail": task,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            else:
                search_results[task] = results
                logs.append({
                    "agent": "Researcher",
                    "action": "Searched",
                    "detail": task,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            time.sleep(0.5)

        return {
            "search_results": search_results,
            "agent_logs": logs,
            "current_agent": "Researcher",
            "error": None,
        }
    except Exception as e:
        return {
            "search_results": search_results,
            "agent_logs": logs,
            "current_agent": "Researcher",
            "error": f"Researcher failed: {str(e)}",
        }
