import json

from agentforge.prompts import PROMPT_VERSION


def meta(state: dict, agent: str) -> dict:
    return {
        "trace_id": state["run_id"],
        "generation_name": agent,
        "trace_user_id": state["user_id"],
        "tags": [agent, f"prompt:{PROMPT_VERSION}"],
    }


def usage_delta(usage: dict) -> dict:
    return {"tokens_used": usage["tokens"], "cost_usd": usage["cost_usd"]}


def render_files(files: dict[str, str]) -> str:
    return "\n\n".join(f"### {path}\n{content}" for path, content in sorted(files.items()))


def plan_text(state: dict) -> str:
    return json.dumps(state["plan"], indent=2)
