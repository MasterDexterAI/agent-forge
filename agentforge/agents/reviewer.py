# decide what happens next
from langgraph.types import interrupt

from agentforge.agents.common import meta, plan_text, render_files, usage_delta
from agentforge.config import settings
from agentforge.core.guards import compress_error, hash_files, scan_secrets
from agentforge.core.llm import structured_call
from agentforge.core.schemas import Review
from agentforge.prompts.reviewer_prompt import REVIEWER_SYSTEM


def _fix(comments: list[str]) -> dict:
    return {"review": {"verdict": "fix", "score": 0.0, "comments": comments}, "status": "fixing"}


def _escalate(state: dict, reason: str) -> dict:
    decision = interrupt(
        {
            "reason": reason,
            "iteration": state["iteration_count"],
            "failure": compress_error(state["execution_stdout"], state["execution_stderr"]),
            "files": sorted(state["code_files"]),
            "review": state.get("review"),
        }
    )
    action = (decision or {}).get("action", "abort")
    guidance = ((decision or {}).get("guidance") or "")[:2000]
    if action == "retry":
        return {
            **_fix([f"Human guidance: {guidance}"] if guidance else ["Try a different approach."]),
            "human_guidance": guidance or None,
            "max_iterations": state["iteration_count"] + 2,
        }
    if action == "replan":
        return {
            "review": {
                "verdict": "replan",
                "score": 0.0,
                "comments": [guidance or "Human requested a new plan."],
            },
            "human_guidance": guidance or None,
            "status": "replanning",
            "replans": state["replans"] + 1,
            "max_iterations": state["iteration_count"] + settings.max_iterations,
        }
    return {"status": "aborted", "review_approved": False}


async def reviewer_node(state: dict) -> dict:
    if state["tokens_used"] > settings.max_tokens_per_run or state["cost_usd"] > settings.run_budget_usd:
        return {"status": "budget_exceeded", "review_approved": False}

    if not state["test_passed"]:
        sigs = state["error_signatures"]
        stuck = len(sigs) >= 2 and sigs[-1] == sigs[-2]
        if stuck or state["iteration_count"] >= state["max_iterations"]:
            return _escalate(state, "stuck_same_error" if stuck else "max_iterations")
        return _fix(["Tests are failing. Fix the cause in the failure report."])

    if hash_files(state["test_files"]) != state["tests_hash"]:
        return _fix(["Test files were modified. Tests are locked. Restore them and fix the code instead."])

    leaks = scan_secrets(state["code_files"])
    if leaks:
        return _fix([f"Possible hardcoded secret, remove it: {leak}" for leak in leaks])

    review, usage = await structured_call(
        settings.reviewer_model,
        REVIEWER_SYSTEM,
        f"PLAN:\n{plan_text(state)}\n\nCODE:\n{render_files(state['code_files'])}\n\nTESTS:\n{render_files(state['test_files'])}",
        Review,
        meta(state, "reviewer"),
    )
    spent = usage_delta(usage)

    if review.verdict == "approve" and review.score >= settings.review_threshold:
        return {"review": review.model_dump(), "review_approved": True, "status": "approved", **spent}

    if state["iteration_count"] >= state["max_iterations"] + 2:
        return {**_escalate(state, "reviewer_not_satisfied"), **spent}

    if review.verdict == "replan" and state["replans"] < settings.max_replans:
        return {
            "review": review.model_dump(),
            "status": "replanning",
            "replans": state["replans"] + 1,
            "max_iterations": state["iteration_count"] + settings.max_iterations,
            **spent,
        }

    return {"review": {**review.model_dump(), "verdict": "fix"}, "status": "fixing", **spent}
