import json
from typing import Any

from redis.asyncio import Redis

from agentforge.config import settings

redis = Redis.from_url(settings.redis_url, decode_responses=True)
STREAM_TTL_S = 3 * 24 * 3600


def _key(run_id: str) -> str:
    return f"run:{run_id}:events"


def _shrink(value: Any, limit: int = 20_000) -> Any:
    if isinstance(value, str) and len(value) > limit:
        return value[:limit] + "...[truncated]"
    if isinstance(value, dict):
        return {k: _shrink(v, limit) for k, v in value.items()}
    if isinstance(value, list):
        return [_shrink(v, limit) for v in value[:200]]
    return value


async def publish(run_id: str, kind: str, data: dict[str, Any]) -> None:
    key = _key(run_id)
    await redis.xadd(
        key,
        {"kind": kind, "data": json.dumps(_shrink(data), default=str)},
        maxlen=2000,
        approximate=True,
    )
    await redis.expire(key, STREAM_TTL_S)


async def read(run_id: str, after: str = "0-0", block_ms: int = 15_000) -> list[tuple[str, dict]]:
    result = await redis.xread({_key(run_id): after}, block=block_ms, count=100)
    if not result:
        return []
    return result[0][1]


async def accepting_runs(default: bool) -> bool:
    """Kill switch: Redis flag overrides the env default, no redeploy needed."""
    val = await redis.get("kill_switch:accept_runs")
    return default if val is None else val == "1"
