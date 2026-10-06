import pytest
from langgraph.checkpoint.memory import MemorySaver

from agentforge.core.graph import build_graph
from agentforge.core.state import initial_state


@pytest.mark.asyncio
async def test_factory_approves_simple_task():
    graph = build_graph().compile(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "ci-1"}, "recursion_limit": 40}
    result = await graph.ainvoke(initial_state("ci-1", "ci", "add two ints"), config)
    assert result["status"] == "approved"
    assert result["test_passed"] is True
    assert result["iteration_count"] == 1
    assert "calc.py" in result["code_files"]
