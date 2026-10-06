import argparse
import asyncio
import time
import uuid
from pathlib import Path

import yaml
from langgraph.checkpoint.memory import MemorySaver

from agentforge.core.graph import build_graph
from agentforge.core.sandbox import run_in_sandbox
from agentforge.core.state import initial_state
from agentforge.prompts import PROMPT_VERSION

SMOKE = {"slugify", "roman", "lru_cache"}


def load_tasks(suite: str) -> list[dict]:
    tasks = [yaml.safe_load(p.read_text()) for p in sorted(Path("evals/tasks").glob("*.yaml"))]
    return [t for t in tasks if suite == "full" or t["id"] in SMOKE]


async def run_once(graph, task: dict, attempt: int) -> dict:
    run_id = f"eval-{task['id']}-{attempt}-{uuid.uuid4().hex[:6]}"
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
    started = time.monotonic()
    state = await graph.ainvoke(initial_state(run_id, "eval", task["prompt"]), config)

    approved = state["status"] == "approved"
    hidden_passed = False
    if state["code_files"]:
        files = {**state["code_files"], "tests/test_hidden.py": task["hidden_tests"]}
        result = await run_in_sandbox(
            run_id, 999, files, "python -m pytest -q -p no:cacheprovider tests/test_hidden.py"
        )
        hidden_passed = result.exit_code == 0

    return {
        "task": task["id"],
        "attempt": attempt,
        "approved": approved,
        "hidden_passed": hidden_passed,
        "false_approve": approved and not hidden_passed,
        "iterations": state["iteration_count"],
        "cost_usd": round(state["cost_usd"], 4),
        "tokens": state["tokens_used"],
        "seconds": round(time.monotonic() - started, 1),
        "status": state["status"],
    }


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="full")
    parser.add_argument("--repeats", type=int, default=2)
    parser.add_argument("--out", default="eval-report")
    args = parser.parse_args()

    graph = build_graph().compile(checkpointer=MemorySaver())
    results = []
    for task in load_tasks(args.suite):
        for attempt in range(args.repeats):
            try:
                results.append(await run_once(graph, task, attempt))
            except Exception as exc:
                results.append(
                    {
                        "task": task["id"],
                        "attempt": attempt,
                        "approved": False,
                        "hidden_passed": False,
                        "false_approve": False,
                        "error": str(exc)[:300],
                    }
                )

    from evals.report import write_report

    write_report(results, args, PROMPT_VERSION, Path(args.out))


if __name__ == "__main__":
    asyncio.run(main())
