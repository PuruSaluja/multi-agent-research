from typing import Literal
from langgraph.graph import StateGraph, END

from models import ResearchState
from agents.planner import planner_node
from agents.researcher import researcher_node
from agents.analyst import analyst_node
from agents.writer import writer_node


def error_handler_node(state: ResearchState) -> dict:
    return {"current_agent": "Error", "error": state.get("error", "Unknown error")}


def route_after_node(state: ResearchState) -> Literal["error_handler", "continue"]:
    if state.get("error"):
        return "error_handler"
    return "continue"


def build_graph() -> StateGraph:
    graph = StateGraph(ResearchState)

    graph.add_node("planner", planner_node)
    graph.add_node("researcher", researcher_node)
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
        route_after_node,
        {"error_handler": "error_handler", "continue": "analyst"},
    )
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
