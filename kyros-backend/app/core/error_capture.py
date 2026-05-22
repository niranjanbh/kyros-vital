"""Error capture middleware — writes 4xx/5xx and unhandled exceptions to error_log."""

from __future__ import annotations

import json
import time
import traceback as tb_mod
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.audit import _scrub_pii
from app.core.logging import request_id_var

log = structlog.get_logger(__name__)

# Don't log errors from admin routes (would cause feedback loops) or health checks
_SKIP_PREFIXES = ("/admin", "/health", "/docs", "/redoc", "/openapi")

_CallNext = Callable[[Request], Awaitable[Response]]


class ErrorCaptureMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: _CallNext) -> Response:
        if any(request.url.path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        start = time.monotonic()
        exc_info: tuple[Any, Any, Any] | None = None
        response: Response | None = None

        try:
            response = await call_next(request)
        except Exception as exc:
            exc_info = (type(exc), exc, exc.__traceback__)
            # Re-raise so FastAPI exception handlers can still produce the JSON response
            raise
        finally:
            elapsed_ms = (time.monotonic() - start) * 1000
            status_code = response.status_code if response is not None else 500

            if status_code >= 400:
                try:
                    await _record(request, status_code, elapsed_ms, exc_info)
                except Exception:
                    log.exception("error_capture.write_failed")

        return response  # type: ignore[return-value]


async def _record(
    request: Request,
    status_code: int,
    duration_ms: float,
    exc_info: tuple[Any, Any, Any] | None,
) -> None:
    from app.database import AsyncSessionLocal
    from app.shared.models.error_log import ErrorLog

    error_type: str | None = None
    error_detail: str | None = None
    traceback_str: str | None = None

    if exc_info and exc_info[1] is not None:
        exc = exc_info[1]
        error_type = type(exc).__name__
        error_detail = str(exc)[:2000]
        if status_code >= 500:
            traceback_str = "".join(tb_mod.format_exception(*exc_info))[:8000]

    # For non-exception 4xx (e.g. validation errors), extract detail from body if available
    if error_type is None and status_code >= 400:
        error_type = f"HTTP {status_code}"

    body: dict[str, Any] | None = None
    if request.method in {"POST", "PATCH", "PUT"}:
        try:
            raw = await request.body()
            if raw:
                body = _scrub_pii(json.loads(raw))
        except Exception:
            pass

    query = str(request.url.query)[:500] if request.url.query else None
    user = getattr(request.state, "user", None)
    user_id = user.id if user else None
    req_id = request_id_var.get(None)

    # Which FastAPI route handler was invoked — e.g. "create_tracked_item"
    route = request.scope.get("route")
    endpoint_name: str | None = getattr(route, "name", None)

    # Human-readable summary of what the server told the client
    response_summary: str | None = None
    if error_detail:
        prefix = f"{error_type}: " if error_type else ""
        response_summary = f"{prefix}{error_detail}"[:500]

    entry = ErrorLog(
        id=uuid.uuid4(),
        occurred_at=datetime.now(tz=UTC),
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        error_type=error_type,
        error_detail=error_detail,
        traceback=traceback_str,
        user_id=user_id,
        request_id=req_id,
        ip_address=request.client.host if request.client else None,
        duration_ms=round(duration_ms, 2),
        query_params=query,
        request_body=body,
        user_agent=(request.headers.get("user-agent") or "")[:500] or None,
        endpoint=endpoint_name,
        response_summary=response_summary,
    )

    async with AsyncSessionLocal() as session:
        session.add(entry)
        await session.commit()
