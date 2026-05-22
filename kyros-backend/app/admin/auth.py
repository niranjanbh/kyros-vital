import secrets
import time

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings

_security = HTTPBasic()

# In-process brute-force counter: ip -> (fail_count, window_start)
_fail_counts: dict[str, tuple[int, float]] = {}
_MAX_FAILURES = 10
_LOCKOUT_SECONDS = 300  # 5 minutes


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_lockout(ip: str) -> None:
    count, since = _fail_counts.get(ip, (0, 0.0))
    if time.monotonic() - since > _LOCKOUT_SECONDS:
        _fail_counts.pop(ip, None)
        return
    if count >= _MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Try again in 5 minutes.",
            headers={"Retry-After": "300"},
        )


def _record_failure(ip: str) -> None:
    count, since = _fail_counts.get(ip, (0, time.monotonic()))
    _fail_counts[ip] = (count + 1, since)


def _clear_failure(ip: str) -> None:
    _fail_counts.pop(ip, None)


def verify_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(_security),
) -> str:
    """Validate HTTP Basic credentials against env-var-configured admin account.

    Constant-time username comparison prevents timing oracle on the username.
    bcrypt.checkpw does constant-time comparison internally.
    Returns the admin username on success, raises 429 after 10 failures in 5 min.
    """
    ip = _get_client_ip(request)
    _check_lockout(ip)

    if not settings.ADMIN_PASSWORD_HASH:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin access not configured.",
            headers={"WWW-Authenticate": "Basic"},
        )

    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        settings.ADMIN_USERNAME.encode("utf-8"),
    )

    try:
        password_ok = bcrypt.checkpw(
            credentials.password.encode("utf-8"),
            settings.ADMIN_PASSWORD_HASH.encode("utf-8"),
        )
    except Exception:
        password_ok = False

    if not (username_ok and password_ok):
        _record_failure(ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    _clear_failure(ip)
    return credentials.username
