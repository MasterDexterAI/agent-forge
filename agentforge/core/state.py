# shared state objects every agent can access

from typing import TypeDict, List, Dict, Any, Optional, Annotated
import operator

class AgentForgeState(TypeDict):
    task_id: str
    user_prompt: str
    workspace_path: str
    git_branch: str

    plan: Optional[Dict[str, Any]]
    active_subtask_index: int

    active_patch: Optional[str]
    code_patches: Annotated[List[Dict[str, Any]], operator.add]

    execution_stdout: str
    execution_stderr: str
    execution_exit_code: int
    test_passed: bool

    iteration_count: int
    max_iterations: int
    review_approved: bool
    human_intervention_required: bool