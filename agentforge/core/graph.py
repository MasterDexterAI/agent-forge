# wires 4 agents into langgraph state machine

from langgraph.graph import StateGraph, END
from agentforge.core.state import AgentForgeState
from agentforge.agents.planner import plan_node
from agentforge.agents.coder import coder_node
from agentforge.agents.tester import tester_node
from agentforge.agents.reviewer import reviewer_node

def route_after_reviewer(state: AgentForgeState) -> str:
    if state["review_approved"]:
        return END
    if state["iteration_count"] >= state["max_iterations"]:
        return END
    return "coder"

def build_graph():
    graph = StateGraph(AgentForgeState)

    graph.add_node("planner", plan_node)
    graph.add_node("coder", coder_node)
    graph.add_node("tester", tester_node)
    graph.add_node("reviewer", reviewer_node)

    graph.set_entry_point("planner")
    graph.add_edge("planner", "coder")
    graph.add_edge("coder", "tester")
    graph.add_edge("tester", "reviewer")
    graph.add_conditional_edges("reviewer", route_after_reviewer)

    return graph