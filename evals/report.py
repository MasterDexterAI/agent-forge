import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path


def _passk(attempts: list[bool]) -> float:
    return 1.0 if attempts and all(attempts) else 0.0


def write_report(results: list[dict], args, prompt_version: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    total = len(results)
    approved = sum(bool(r.get("approved")) for r in results)
    hidden = sum(bool(r.get("hidden_passed")) for r in results)
    false_approvals = sum(bool(r.get("false_approve")) for r in results)
    solved = [r for r in results if r.get("hidden_passed")]

    by_task: dict[str, list[bool]] = defaultdict(list)
    for r in results:
        by_task[r["task"]].append(bool(r.get("hidden_passed")))
    reliable = sum(_passk(v) for v in by_task.values())

    summary = {
        "prompt_version": prompt_version,
        "suite": args.suite,
        "repeats": args.repeats,
        "total_runs": total,
        "approve_rate": round(approved / total, 3) if total else 0,
        "hidden_pass_rate": round(hidden / total, 3) if total else 0,
        "false_approve_rate": round(false_approvals / total, 3) if total else 0,
        "reliable_tasks": f"{int(reliable)}/{len(by_task)}",
        "avg_iterations_solved": round(statistics.mean([r["iterations"] for r in solved]), 2)
        if solved
        else None,
        "avg_cost_solved": round(statistics.mean([r["cost_usd"] for r in solved]), 4) if solved else None,
    }

    (out / "results.json").write_text(json.dumps(results, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))

    lines = [
        f"**Agent Forge evals** ({summary['prompt_version']}, {summary['suite']})",
        f"hidden pass: {summary['hidden_pass_rate']:.0%}  ·  false approve: {summary['false_approve_rate']:.0%}",
        f"reliable (pass^{args.repeats}): {summary['reliable_tasks']}  ·  avg cost/solved: ${summary['avg_cost_solved']}",
    ]
    (out / "discord.json").write_text(json.dumps({"content": "\n".join(lines)}))
    print("\n".join(lines))

    floor = float(os.getenv("EVAL_MIN_HIDDEN_PASS", "0"))
    ceil = float(os.getenv("EVAL_MAX_FALSE_APPROVE", "1"))
    if summary["hidden_pass_rate"] < floor or summary["false_approve_rate"] > ceil:
        print(f"FAIL: below floor {floor} or above false-approve ceil {ceil}")
        sys.exit(1)
