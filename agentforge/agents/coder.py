# take one subtask and produce a patch

from agentforge.agents.common import meta, plan_text, render_files, usage_delta
from agentforge.config import settings
from agentforge.core.guards import GuardError, compress_error, validate_code_files
from agentforge.core.llm import structured_call
from agentforge.core.schemas import CodePatch
from agentforge.prompts.coder_prompt import CODER_SYSTEM


def _coder_input(state: dict) -> str:
    parts = [
        f"PLAN:\n{plan_text(state)}",
        f"TESTS (read only, you cannot change these):\n{render_files(state['test_files'])}",
    ]
    if state["code_files"]:
        parts.append(f"CURRENT CODE:\n{render_files(state['code_files'])}")
    if state["iteration_count"] > 0 and not state["test_passed"]:
        parts.append(
            "FAILURE REPORT FROM THE LAST TEST RUN:\n"
            + compress_error(state["execution_stdout"], state["execution_stderr"])
        )
    review = state.get("review")
    if review and review.get("verdict") == "fix" and review.get("comments"):
        parts.append("REVIEWER NOTES:\n- " + "\n- ".join(review["comments"]))
    if state.get("human_guidance"):
        parts.append(f"HUMAN GUIDANCE:\n{state['human_guidance']}")
    return "\n\n".join(parts)


async def coder_node(state: dict) -> dict:
    patch, usage = await structured_call(
        settings.coder_model, CODER_SYSTEM, _coder_input(state), CodePatch, meta(state, "coder")
    )
    try:
        written = validate_code_files(patch.files)
    except GuardError as exc:
        return {"guard_violation": str(exc), "status": "coded", **usage_delta(usage)}
    return {
        "code_files": {**state["code_files"], **written},
        "guard_violation": None,
        "status": "coded",
        **usage_delta(usage),
    }
