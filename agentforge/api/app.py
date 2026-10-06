import uuid
from contextlib import asynccontextmanager
from typing import Literal

from arq import create_pool
from arq.connections import RedisSettings
from arq.jobs import Job
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from agentforge.api.security import make_stream_token, require_internal, verify_stream_token
from agentforge.config import settings
from agentforge.core import events
from agentforge.core.db import open_pool
from agentforge.store import runs as store

TERMINAL = {"approved", "aborted", "failed", "cancelled", "budget_exceeded", "refused"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await open_pool()
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    yield
    await app.state.arq.close()
    await app.state.pool.close()


app = FastAPI(title="Agent Forge", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["GET"],
    allow_headers=["Last-Event-ID"],
)
app.mount("/metrics", make_asgi_app())


class CreateRun(BaseModel):
    prompt: str = Field(min_length=10)
    idempotency_key: str | None = Field(default=None, max_length=64)


class ResumeRun(BaseModel):
    action: Literal["retry", "replan", "abort"]
    guidance: str = Field(default="", max_length=2000)


async def _owned_run(request: Request, run_id: str, user_id: str) -> dict:
    try:
        uuid.UUID(run_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="not found")
    run = await store.get_run(request.app.state.pool, run_id)
    if not run or run["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="not found")
    return run


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/readyz")
async def readyz(request: Request):
    async with request.app.state.pool.connection() as conn:
        await conn.execute("select 1")
    await events.redis.ping()
    queued = await events.redis.zcard("arq:queue")
    return {
        "ok": True,
        "queued_jobs": queued,
        "accepting_runs": await events.accepting_runs(settings.accept_new_runs),
    }


@app.get("/v1/quota")
async def quota(request: Request, user_id: str = Depends(require_internal)):
    used = await store.runs_today(request.app.state.pool, user_id)
    return {
        "limit": settings.runs_per_user_per_day,
        "used": used,
        "remaining": max(settings.runs_per_user_per_day - used, 0),
    }


@app.post("/v1/runs")
async def create_run(body: CreateRun, request: Request, user_id: str = Depends(require_internal)):
    if not await events.accepting_runs(settings.accept_new_runs):
        raise HTTPException(status_code=503, detail="New runs are paused. Try again later.")
    prompt = body.prompt.strip()
    if len(prompt) > settings.max_prompt_chars:
        raise HTTPException(
            status_code=413, detail=f"Prompt is longer than {settings.max_prompt_chars} characters."
        )
    pool = request.app.state.pool
    if await store.runs_today(pool, user_id) >= settings.runs_per_user_per_day:
        raise HTTPException(status_code=429, detail="Daily run limit reached. Come back tomorrow.")

    run_id, created = await store.create_run(pool, str(uuid.uuid4()), user_id, prompt, body.idempotency_key)
    if created:
        await request.app.state.arq.enqueue_job("execute_run", run_id, None, _job_id=run_id)
        await store.audit(pool, run_id, user_id, "run.created", {"chars": len(prompt)})
        await events.publish(run_id, "status", {"status": "queued"})
    return {"run_id": run_id, "created": created, "stream_token": make_stream_token(run_id, user_id)}


@app.get("/v1/runs")
async def list_runs(request: Request, user_id: str = Depends(require_internal)):
    return {"runs": await store.list_runs(request.app.state.pool, user_id)}


@app.get("/v1/runs/{run_id}")
async def get_run(run_id: str, request: Request, user_id: str = Depends(require_internal)):
    run = await _owned_run(request, run_id, user_id)
    return {**run, "stream_token": make_stream_token(run_id, user_id)}


@app.post("/v1/runs/{run_id}/resume")
async def resume_run(
    run_id: str, body: ResumeRun, request: Request, user_id: str = Depends(require_internal)
):
    run = await _owned_run(request, run_id, user_id)
    if run["status"] != "awaiting_human":
        raise HTTPException(status_code=409, detail=f"Run is {run['status']}, not waiting for you.")
    pool = request.app.state.pool
    await store.set_status(pool, run_id, "queued")
    await store.audit(pool, run_id, user_id, "run.resumed", body.model_dump())
    await request.app.state.arq.enqueue_job(
        "execute_run", run_id, body.model_dump(), _job_id=f"{run_id}:resume:{uuid.uuid4().hex[:8]}"
    )
    await events.publish(run_id, "status", {"status": "queued", "resumed_with": body.action})
    return {"ok": True}


@app.post("/v1/runs/{run_id}/cancel")
async def cancel_run(run_id: str, request: Request, user_id: str = Depends(require_internal)):
    run = await _owned_run(request, run_id, user_id)
    if run["status"] in TERMINAL:
        return {"ok": True}
    await Job(run_id, request.app.state.arq).abort(timeout=0)
    await store.set_status(request.app.state.pool, run_id, "cancelled")
    await store.audit(request.app.state.pool, run_id, user_id, "run.cancelled", {})
    await events.publish(run_id, "done", {"status": "cancelled"})
    return {"ok": True}


@app.get("/v1/runs/{run_id}/stream")
async def stream(run_id: str, request: Request, token: str):
    verify_stream_token(token, run_id)
    cursor = request.headers.get("last-event-id") or "0-0"

    async def generator():
        nonlocal cursor
        while not await request.is_disconnected():
            batch = await events.read(run_id, cursor)
            for entry_id, fields in batch:
                cursor = entry_id
                yield {"id": entry_id, "event": fields["kind"], "data": fields["data"]}

    return EventSourceResponse(generator(), ping=15)
