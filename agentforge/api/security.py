import base64
import hashlib
import hmac
import time

from fastapi import Header, HTTPException

from agentforge.config import settings


def require_internal(x_internal_key: str = Header(...), x_user_id: str = Header(...)) -> str:
    if not hmac.compare_digest(x_internal_key, settings.internal_api_key):
        raise HTTPException(status_code=401, detail="bad internal key")
    if not x_user_id or len(x_user_id) > 64:
        raise HTTPException(status_code=400, detail="bad user id")
    return x_user_id


def _sign(payload: str) -> str:
    return hmac.new(settings.stream_token_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def make_stream_token(run_id: str, user_id: str, ttl_s: int = 6 * 3600) -> str:
    payload = f"{run_id}|{user_id}|{int(time.time()) + ttl_s}"
    raw = f"{payload}|{_sign(payload)}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_stream_token(token: str, run_id: str) -> str:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        token_run, user_id, expires, signature = raw.split("|")
    except Exception:
        raise HTTPException(status_code=401, detail="bad token")
    payload = f"{token_run}|{user_id}|{expires}"
    if not hmac.compare_digest(signature, _sign(payload)):
        raise HTTPException(status_code=401, detail="bad token")
    if token_run != run_id or int(expires) < time.time():
        raise HTTPException(status_code=401, detail="token expired or wrong run")
    return user_id
