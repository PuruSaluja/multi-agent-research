import time
from datetime import datetime, timezone

import config
from models import ResearchState
from tools.search import SearchError, search_web


def _log(agent: str, action: str, detail) -> dict:
    return {
        "agent": agent,
        "action": action,
        "detail": detail,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def researcher_node(state: ResearchState) -> dict:
    """Search for each outstanding sub-task.

    On the first pass this is every sub-task. On a retry pass it is only the
    sub-questions the refiner rewrote, so earlier results are not re-fetched.

    Three outcomes per task are kept distinct:
      * results found     -> stored
      * ran, found nothing-> task recorded as unanswered
      * could not run     -> task recorded as unanswered *and* as a failure
    If every task failed to run, the whole node errors rather than handing
    empty context to the Analyst.
    """
    pending = state.get("unanswered_tasks") or state.get("sub_tasks", [])
    search_results = dict(state.get("search_results", {}))
    logs = list(state.get("agent_logs", []))

    unanswered: list[str] = []
    failures: list[str] = []

    for task in pending:
        try:
            results = search_web(task)
        except SearchError as exc:
            failures.append(task)
            unanswered.append(task)
            logs.append(_log("Researcher", "Search failed", f"{task} - {exc}"))
        else:
            if results:
                search_results[task] = results
                logs.append(_log("Researcher", "Searched", task))
            else:
                unanswered.append(task)
                logs.append(_log("Researcher", "No results found", task))

        time.sleep(config.SEARCH_PACING_SECONDS)

    if pending and len(failures) == len(pending):
        return {
            "search_results": search_results,
            "unanswered_tasks": unanswered,
            "agent_logs": logs,
            "current_agent": "Researcher",
            "error": (
                f"Researcher failed: every search request failed "
                f"({len(failures)}/{len(pending)}). Check TAVILY_API_KEY and "
                f"network connectivity."
            ),
        }

    return {
        "search_results": search_results,
        "unanswered_tasks": unanswered,
        "agent_logs": logs,
        "current_agent": "Researcher",
        "error": None,
    }
