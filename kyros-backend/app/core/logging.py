import contextvars
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.config import settings

request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

_CallNext = Callable[[Request], Awaitable[Response]]

# Keys that must never appear in structlog output — PHI redaction requirement
_LOG_PHI_KEYS: frozenset[str] = frozenset(
    {"payload", "metadata", "notes", "dose", "lab_value", "result"}
)


def redact_phi(_logger: Any, _method: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    for key in _LOG_PHI_KEYS:
        if key in event_dict:
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        redact_phi,
    ]

    if settings.is_production:
        processors: list[structlog.types.Processor] = [
            *shared_processors,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            *shared_processors,
            structlog.dev.ConsoleRenderer(),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), settings.LOG_LEVEL, 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


_log = structlog.get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: _CallNext) -> Response:
        import time as _time

        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        t0 = _time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((_time.monotonic() - t0) * 1000, 1)

        response.headers["X-Request-Id"] = request_id

        # Emit one structured log line per request so latency is always observable.
        # Admin and health routes are excluded (high volume, low signal).
        skip = request.url.path.startswith(("/admin", "/health", "/docs", "/redoc", "/openapi"))
        if not skip:
            _log.info(
                "request.completed",
                status=response.status_code,
                duration_ms=duration_ms,
            )

        return response
