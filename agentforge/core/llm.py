import json
import re
from pathlib import Path
from typing import Any, TypeVar

import litellm
from litellm import acompletion, completion_cost
from pydantic import BaseModel, ValidationError

from agentforge.config import settings
from agentforge.metrics import LLM_COST, LLM_FAILURES, LLM_TOKENS

T = TypeVar("T", bound=BaseModel)

if settings.langfuse_enabled:
    litellm.success_callback = ["langfuse"]
    litellm.failure_callback = ["langfuse"]


class LLMError(Exception):
    pass


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if fenced:
        return fenced.group(1).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise LLMError("response contained no JSON object")
    return text[start : end + 1]


def _safe_cost(resp: Any) -> float:
    try:
        return float(completion_cost(completion_response=resp) or 0.0)
    except Exception:
        return 0.0


def _fake(schema: type[T]) -> T:
    path = Path(settings.fake_llm_dir) / f"{schema.__name__}.json"
    return schema.model_validate_json(path.read_text())


async def structured_call(
    model: str, system: str, user: str, schema: type[T], meta: dict[str, Any]
) -> tuple[T, dict[str, Any]]:
    agent = meta.get("generation_name", "unknown")
    if settings.llm_mode == "fake":
        return _fake(schema), {"model": "fake", "tokens": 0, "cost_usd": 0.0}

    schema_hint = json.dumps(schema.model_json_schema())
    base = [
        {
            "role": "system",
            "content": f"{system}\n\nReply with ONE JSON object that matches this JSON schema. No prose.\n{schema_hint}",
        },
        {"role": "user", "content": user},
    ]
    last_error: Exception | None = None

    for candidate in [model, *[m for m in settings.fallback_models if m != model]]:
        messages = list(base)
        for _ in range(2):
            try:
                resp = await acompletion(
                    model=candidate,
                    messages=messages,
                    temperature=0.2,
                    max_tokens=8192,
                    timeout=120,
                    num_retries=2,
                    metadata=meta,
                )
            except Exception as exc:
                LLM_FAILURES.labels(candidate).inc()
                last_error = exc
                break
            text = resp.choices[0].message.content or ""
            try:
                parsed = schema.model_validate_json(_extract_json(text))
            except (ValidationError, LLMError, json.JSONDecodeError) as exc:
                last_error = exc
                messages = messages + [
                    {"role": "assistant", "content": text[:4000]},
                    {
                        "role": "user",
                        "content": f"That was invalid: {str(exc)[:800]}. Return only the corrected JSON object.",
                    },
                ]
                continue
            tokens = (resp.usage.prompt_tokens or 0) + (resp.usage.completion_tokens or 0)
            cost = _safe_cost(resp)
            LLM_TOKENS.labels(agent).inc(tokens)
            LLM_COST.labels(agent).inc(cost)
            return parsed, {"model": candidate, "tokens": tokens, "cost_usd": cost}

    raise LLMError(f"all models failed for {agent}: {last_error}")
