# it can turn vague human prompts into a concrete ordered list of steps

from agentforge.agents.common import meta, usage_delta
from agentforge.config import settings
from agentforge.core.llm import structured_call
from agentforge.core.schemas import Plan
from agentforge.prompts.planner_prompt import PLANNER_SYSTEM


async def planner_node(state: dict) -> dict:
    parts = [f"USER REQUEST:\n{state['user_prompt']}"]
    review = state.get("review")
    if review and review.get("verdict") == "replan":
        parts.append("THE PREVIOUS PLAN WAS REJECTED:\n- " + "\n- ".join(review.get("comments", [])))
    if state.get("human_guidance"):
        parts.append(f"HUMAN GUIDANCE:\n{state['human_guidance']}")

    plan, usage = await structured_call(
        settings.planner_model, PLANNER_SYSTEM, "\n\n".join(parts), Plan, meta(state, "planner")
    )
    if plan.subtasks[0].title.strip().upper() == "REFUSED":
        return {"plan": plan.model_dump(), "status": "refused", **usage_delta(usage)}
    return {"plan": plan.model_dump(), "status": "planned", **usage_delta(usage)}
