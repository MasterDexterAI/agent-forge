import operator
from typing import Annotated, Any, TypedDict


class AgentForgeState(TypedDict):
    run_id: str
    user_id: str
    user_prompt: str
    status: str

    plan: dict[str, Any] | None
    replans: int

    test_files: dict[str, str]
    tests_hash: str
    code_files: dict[str, str]
    guard_violation: str | None

    execution_stdout: str
    execution_stderr: str
    execution_exit_code: int
    test_passed: bool
    error_signatures: Annotated[list[str], operator.add]

    iteration_count: int
    max_iterations: int

    review: dict[str, Any] | None
    review_approved: bool
    human_guidance: str | None

    tokens_used: Annotated[int, operator.add]
    cost_usd: Annotated[float, operator.add]


def initial_state(run_id: str, user_id: str, prompt: str, max_iterations: int = 3) -> dict:
    return {
        "run_id": run_id,
        "user_id": user_id,
        "user_prompt": prompt,
        "status": "queued",
        "plan": None,
        "replans": 0,
        "test_files": {},
        "tests_hash": "",
        "code_files": {},
        "guard_violation": None,
        "execution_stdout": "",
        "execution_stderr": "",
        "execution_exit_code": 0,
        "test_passed": False,
        "error_signatures": [],
        "iteration_count": 0,
        "max_iterations": max_iterations,
        "review": None,
        "review_approved": False,
        "human_guidance": None,
        "tokens_used": 0,
        "cost_usd": 0.0,
    }


# # shared state objects every agent can access

# from typing import TypeDict, List, Dict, Any, Optional, Annotated
# import operator

# class AgentForgeState(TypeDict):
#     task_id: str
#     user_prompt: str
#     workspace_path: str
#     git_branch: str

#     plan: Optional[Dict[str, Any]]
#     active_subtask_index: int

#     active_patch: Optional[str]
#     code_patches: Annotated[List[Dict[str, Any]], operator.add]

#     execution_stdout: str
#     execution_stderr: str
#     execution_exit_code: int
#     test_passed: bool

#     iteration_count: int
#     max_iterations: int
#     review_approved: bool
#     human_intervention_required: bool
