from langgraph.graph import END, START, StateGraph

from agentforge.agents.coder import coder_node
from agentforge.agents.planner import planner_node
from agentforge.agents.reviewer import reviewer_node
from agentforge.agents.tester import run_tests_node, write_tests_node
from agentforge.core.state import AgentForgeState

TERMINAL = {"approved", "aborted", "budget_exceeded", "refused"}


def route_after_planner(state: dict) -> str:
    return END if state["status"] == "refused" else "test_writer"


def route_after_review(state: dict) -> str:
    if state["status"] in TERMINAL:
        return END
    if state["status"] == "replanning":
        return "planner"
    return "coder"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentForgeState)
    graph.add_node("planner", planner_node)
    graph.add_node("test_writer", write_tests_node)
    graph.add_node("coder", coder_node)
    graph.add_node("tester", run_tests_node)
    graph.add_node("reviewer", reviewer_node)

    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", route_after_planner, ["test_writer", END])
    graph.add_edge("test_writer", "coder")
    graph.add_edge("coder", "tester")
    graph.add_edge("tester", "reviewer")
    graph.add_conditional_edges("reviewer", route_after_review, ["coder", "planner", END])
    return graph


# # wires 4 agents into langgraph state machine

# from langgraph.graph import StateGraph, END
# from agentforge.core.state import AgentForgeState
# from agentforge.agents.planner import plan_node
# from agentforge.agents.coder import coder_node
# from agentforge.agents.tester import tester_node
# from agentforge.agents.reviewer import reviewer_node

# def route_after_reviewer(state: AgentForgeState) -> str:
#     if state["review_approved"]:
#         return END
#     if state["iteration_count"] >= state["max_iterations"]:
#         return END
#     return "coder"

# def build_graph():
#     graph = StateGraph(AgentForgeState)

#     graph.add_node("planner", plan_node)
#     graph.add_node("coder", coder_node)
#     graph.add_node("tester", tester_node)
#     graph.add_node("reviewer", reviewer_node)

#     graph.set_entry_point("planner")
#     graph.add_edge("planner", "coder")
#     graph.add_edge("coder", "tester")
#     graph.add_edge("tester", "reviewer")
#     graph.add_conditional_edges("reviewer", route_after_reviewer)

#     return graph
