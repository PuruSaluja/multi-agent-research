from typing import Literal

from langgraph.graph import END, StateGraph

import config
from agents.analyst import analyst_node
from agents.planner import planner_node
from agents.refiner import refiner_node
from agents.researcher import researcher_node
from agents.writer import writer_node
from models import ResearchState


def error_handler_node(state: ResearchState) -> dict:
    return {"current_agent": "Error", "error": state.get("error", "Unknown error")}


def route_after_node(state: ResearchState) -> Literal["error_handler", "continue"]:
    if state.get("error"):
        return "error_handler"
    return "continue"


def coverage_ratio(state: ResearchState) -> float:
    """Fraction of planned sub-questions that produced at least one source."""
    sub_tasks = state.get("sub_tasks", [])
    if not sub_tasks:
        return 0.0
    return len(state.get("search_results", {})) / len(sub_tasks)


def route_after_research(
    state: ResearchState,
) -> Literal["error_handler", "refine", "continue"]:
    """Decide whether the research pass was good enough to analyse.

    This is the branch that justifies a state graph over a linear chain: a thin
    pass with retries left loops back through the refiner for another attempt,
    rather than handing sparse context to the Analyst.
    """
    if state.get("error"):
        return "error_handler"

    unanswered = state.get("unanswered_tasks", [])
    retries_left = state.get("retry_count", 0) < config.MAX_RESEARCH_RETRIES
    thin = coverage_ratio(state) < config.MIN_COVERAGE_RATIO

    if unanswered and retries_left and thin:
        return "refine"
    return "continue"


def build_graph():
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("refiner", refiner_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)
    graph.add_node("error_handler", error_handler_node)

    graph.set_entry_point("planner")

    graph.add_conditional_edges(
        "planner",
        route_after_node,
        {"error_handler": "error_handler", "continue": "researcher"},
    )
    graph.add_conditional_edges(
        "researcher",
        route_after_research,
        {
            "error_handler": "error_handler",
            "refine": "refiner",
            "continue": "analyst",
        },
    )
    # The refiner always loops back for another search pass; retry_count and
    # MAX_RESEARCH_RETRIES bound the cycle.
    graph.add_edge("refiner", "researcher")
    graph.add_conditional_edges(
        "analyst",
        route_after_node,
        {"error_handler": "error_handler", "continue": "writer"},
    )
    graph.add_conditional_edges(
        "writer",
        route_after_node,
        {"error_handler": "error_handler", "continue": END},
    )
    graph.add_edge("error_handler", END)

    return graph.compile()


compiled_graph = build_graph()
