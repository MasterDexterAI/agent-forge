import asyncio
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog
from arq import cron
from arq.connections import RedisSettings
from langgraph.types import Command
from prometheus_client import start_http_server

import docker
from agentforge.config import settings
from agentforge.core import events
from agentforge.core.db import make_checkpointer, open_pool
from agentforge.core.graph import build_graph
from agentforge.core.state import initial_state
from agentforge.metrics import ITERATIONS, RUN_SECONDS, RUNS
from agentforge.store import runs as store

log = structlog.get_logger()


def _summary(node: str, update: dict) -> dict:
    keep = {
        "planner": ["plan", "status"],
        "test_writer": ["test_files", "status"],
        "coder": ["code_files", "guard_violation", "status"],
        "tester": [
            "test_passed",
            "execution_exit_code",
            "execution_stdout",
            "execution_stderr",
            "iteration_count",
        ],
        "reviewer": ["review", "status", "review_approved"],
    }.get(node, list(update))
    return {"node": node, **{k: update.get(k) for k in keep if k in update}}


async def execute_run(ctx: dict, run_id: str, resume: dict | None = None) -> str:
    pool, graph = ctx["pool"], ctx["graph"]
    config = {"configurable": {"thread_id": run_id}, "recursion_limit": 60}
    run = await store.get_run(pool, run_id)
    if run is None or run["status"] in {"cancelled", "approved", "aborted"}:
        return "skipped"

    snapshot = await graph.aget_state(config)
    if resume is not None:
        graph_input = Command(resume=resume)
    elif snapshot.next:
        graph_input = None
        log.info("resuming_from_checkpoint", run_id=run_id, next=snapshot.next)
    else:
        graph_input = initial_state(run_id, run["user_id"], run["prompt"], settings.max_iterations)

    await store.set_status(pool, run_id, "running")
    await events.publish(run_id, "status", {"status": "running"})
    started = time.monotonic()

    try:
        async for chunk in graph.astream(graph_input, config, stream_mode="updates"):
            for node, update in chunk.items():
                if node == "__interrupt__":
                    payload = update[0].value
                    await store.set_status(pool, run_id, "awaiting_human")
                    await events.publish(run_id, "interrupt", payload)
                    await store.audit(
                        pool, run_id, "system", "run.escalated", {"reason": payload.get("reason")}
                    )
                    return "awaiting_human"
                await events.publish(run_id, "node", _summary(node, update or {}))

        final = (await graph.aget_state(config)).values
        await store.finish_run(pool, run_id, final)
        RUNS.labels(final.get("status", "unknown")).inc()
        RUN_SECONDS.observe(time.monotonic() - started)
        ITERATIONS.observe(final.get("iteration_count", 0))
        await events.publish(
            run_id,
            "done",
            {
                "status": final.get("status"),
                "cost_usd": final.get("cost_usd"),
                "tokens_used": final.get("tokens_used"),
                "iterations": final.get("iteration_count"),
            },
        )
        return final.get("status", "unknown")
    except Exception as exc:
        log.exception("run_failed", run_id=run_id)
        RUNS.labels("failed").inc()
        await store.set_status(pool, run_id, "failed", error=str(exc)[:1000])
        await events.publish(
            run_id,
            "error",
            {"message": "The run failed. The team has been notified.", "type": type(exc).__name__},
        )
        return "failed"


def _reap_containers() -> int:
    client = docker.from_env()
    now = datetime.now(timezone.utc)
    removed = 0
    for container in client.containers.list(all=True, filters={"label": "agentforge=sandbox"}):
        created = datetime.fromisoformat(container.attrs["Created"][:19]).replace(tzinfo=timezone.utc)
        too_old = (now - created).total_seconds() > settings.sandbox_timeout_s + 120
        if container.status != "running" or too_old:
            container.remove(force=True)
            removed += 1
    return removed


def _reap_workspaces() -> None:
    root = Path(settings.workspace_root)
    if not root.exists():
        return
    cutoff = time.time() - 3600
    for run_dir in root.iterdir():
        if run_dir.stat().st_mtime < cutoff:
            shutil.rmtree(run_dir, ignore_errors=True)


async def reap(ctx: dict) -> None:
    removed = await asyncio.to_thread(_reap_containers)
    await asyncio.to_thread(_reap_workspaces)
    async with ctx["pool"].connection() as conn:
        await conn.execute(
            "update runs set status = 'failed', error = 'stale: worker lost the job', updated_at = now() "
            "where status in ('running', 'queued') and updated_at < now() - interval '45 minutes'"
        )
    if removed:
        log.warning("reaped_orphan_sandboxes", count=removed)


async def startup(ctx: dict) -> None:
    ctx["pool"] = await open_pool()
    checkpointer = await make_checkpointer(ctx["pool"])
    ctx["graph"] = build_graph().compile(checkpointer=checkpointer)
    start_http_server(9101)
    log.info("worker_ready", concurrency=settings.max_concurrent_sandboxes)


async def shutdown(ctx: dict) -> None:
    await ctx["pool"].close()


class WorkerSettings:
    functions = [execute_run]
    cron_jobs = [cron(reap, minute=set(range(0, 60, 10)))]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = settings.max_concurrent_sandboxes
    job_timeout = 1800
    max_tries = 3
    allow_abort_jobs = True
