import json
from typing import Any

from psycopg_pool import AsyncConnectionPool


async def create_run(
    pool: AsyncConnectionPool, run_id: str, user_id: str, prompt: str, idem: str | None
) -> tuple[str, bool]:
    async with pool.connection() as conn:
        row = await (
            await conn.execute(
                "insert into runs (id, user_id, prompt, idempotency_key) values (%s, %s, %s, %s) "
                "on conflict (user_id, idempotency_key) do nothing returning id",
                (run_id, user_id, prompt, idem or None),
            )
        ).fetchone()
        if row:
            return str(row["id"]), True
        row = await (
            await conn.execute(
                "select id from runs where user_id = %s and idempotency_key = %s", (user_id, idem)
            )
        ).fetchone()
        return str(row["id"]), False


async def runs_today(pool: AsyncConnectionPool, user_id: str) -> int:
    async with pool.connection() as conn:
        row = await (
            await conn.execute(
                "select count(*) as n from runs where user_id = %s and created_at > now() - interval '1 day'",
                (user_id,),
            )
        ).fetchone()
        return int(row["n"])


async def get_run(pool: AsyncConnectionPool, run_id: str) -> dict[str, Any] | None:
    async with pool.connection() as conn:
        return await (await conn.execute("select * from runs where id = %s", (run_id,))).fetchone()


async def list_runs(pool: AsyncConnectionPool, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
    async with pool.connection() as conn:
        return await (
            await conn.execute(
                "select id, prompt, status, cost_usd, tokens_used, iterations, created_at, updated_at "
                "from runs where user_id = %s order by created_at desc limit %s",
                (user_id, limit),
            )
        ).fetchall()


async def set_status(pool: AsyncConnectionPool, run_id: str, status: str, error: str | None = None) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "update runs set status = %s, error = coalesce(%s, error), updated_at = now() where id = %s",
            (status, error, run_id),
        )


async def finish_run(pool: AsyncConnectionPool, run_id: str, values: dict[str, Any]) -> None:
    result = {
        "plan": values.get("plan"),
        "code_files": values.get("code_files"),
        "test_files": values.get("test_files"),
        "review": values.get("review"),
        "last_stdout": (values.get("execution_stdout") or "")[-4000:],
    }
    async with pool.connection() as conn:
        await conn.execute(
            "update runs set status = %s, cost_usd = %s, tokens_used = %s, iterations = %s, "
            "result = %s, updated_at = now() where id = %s",
            (
                values.get("status", "unknown"),
                values.get("cost_usd", 0),
                values.get("tokens_used", 0),
                values.get("iteration_count", 0),
                json.dumps(result),
                run_id,
            ),
        )


async def audit(pool: AsyncConnectionPool, run_id: str | None, actor: str, action: str, detail: dict) -> None:
    async with pool.connection() as conn:
        await conn.execute(
            "insert into audit_log (run_id, actor, action, detail) values (%s, %s, %s, %s)",
            (run_id, actor, action, json.dumps(detail, default=str)),
        )
