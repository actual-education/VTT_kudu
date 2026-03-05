import base64
import hashlib
import hmac
import json
import time

from fastapi import HTTPException, Request

from app.config import settings


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_auth_token() -> str:
    payload = {
        "exp": int(time.time()) + (settings.AUTH_SESSION_TTL_HOURS * 3600),
    }
    payload_raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_enc = _b64url_encode(payload_raw)
    signature = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_enc.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload_enc}.{signature}"


def verify_auth_token(token: str) -> bool:
    try:
        payload_enc, signature = token.split(".", 1)
    except ValueError:
        return False

    expected = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload_enc.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected):
        return False

    try:
        payload = json.loads(_b64url_decode(payload_enc).decode("utf-8"))
    except Exception:
        return False

    exp = int(payload.get("exp", 0) or 0)
    return exp > int(time.time())


def require_authenticated(request: Request) -> None:
    # Auth is optional in local/dev until AUTH_PASSWORD is set.
    if not settings.AUTH_PASSWORD:
        return
    token = request.cookies.get(settings.AUTH_COOKIE_NAME)
    if not token or not verify_auth_token(token):
        raise HTTPException(status_code=401, detail="Authentication required")
