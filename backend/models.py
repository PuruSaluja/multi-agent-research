from typing import Optional
from typing_extensions import TypedDict


class ResearchState(TypedDict):
    query: str
    sub_tasks: list[str]
    search_results: dict[str, list]
    analysis: str
    final_report: str
    agent_logs: list[dict]
    current_agent: str
    error: Optional[str]
