import asyncio
import sys
import uuid
from dotenv import load_dotenv
from agentforge.core.graph import build_graph
from agentforge.core.db import initialize_checkpointer

load_dotenv()

async def run(prompt: str):
    checkpointer = await initialize_checkpointer()
    graph = build_graph().compile(checkpointer=checkpointer)

    initial_state = {
        "task_id": str(uuid.uuid4()),
        "user_prompt": prompt,
        "workspace_path": "./workspace",
        "git_branch": "main",
        "plan": None,
        "active_subtask_index": 0,
        "active_patch": None,
        "code_patches": [],
        "execution_stdout": "",
        "execution_stderr": "",
        "execution_exit_code": 0,
        "test_passed": False,
        "iteration_count": 0,
        "max_iterations": 3,
        "review_approved": False,
        "human_intervention_required": False,
    }

    config = {"configurable": {"thread_id": initial_state["task_id"]}}
    result = await graph.ainvoke(initial_state, config=config)
    print(result)

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:])
    asyncio.run(run(prompt))