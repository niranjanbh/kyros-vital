import json
import re
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

log = structlog.get_logger(__name__)

_MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
_PII_KEYS = {
    # Auth / credentials
    "password", "token", "secret", "authorization",
    # Contact info
    "email", "phone",
    # Healthcare-specific PHI
    "drug_name", "dosage", "dose", "condition", "diagnosis",
    "patient_name", "patient_phone", "patient_email",
    "lab_value", "result", "parsed",
}
_UUID_RE = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.IGNORECASE
)

_CallNext = Callable[[Request], Awaitable[Response]]


def _scrub_pii(data: Any) -> Any:
    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if k.lower() in _PII_KEYS else _scrub_pii(v) for k, v in data.items()
        }
    if isinstance(data, list):
        return [_scrub_pii(item) for item in data]
    return data


def _extract_resource_type(path: str) -> str:
    parts = [p for p in path.split("/") if p and not _UUID_RE.match(p)]
    return parts[-1] if parts else path


def _extract_resource_id(path: str) -> str | None:
    segments = path.split("/")
    for seg in reversed(segments):
        if _UUID_RE.match(seg):
            return seg
    return None


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: _CallNext) -> Response:
        response: Response = await call_next(request)

        if request.method not in _MUTATING_METHODS:
            return response
        if not (200 <= response.status_code < 300):
            return response

        try:
            await self._write_audit(request, response)
        except Exception:
            log.exception("audit.write_failed")

        return response

    async def _write_audit(self, request: Request, response: Response) -> None:
        from app.database import AsyncSessionLocal
        from app.shared.models.audit_log import AuditLog

        user = getattr(request.state, "user", None)
        user_id = user.id if user else None

        body: dict[str, Any] | None = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                body = _scrub_pii(json.loads(body_bytes))
        except Exception:
            pass

        resource_id_str = _extract_resource_id(request.url.path)
        resource_id = uuid.UUID(resource_id_str) if resource_id_str else None

        entry = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            actor_type="user" if user_id else "system",
            action=f"{request.method} {request.url.path}",
            resource_type=_extract_resource_type(request.url.path),
            resource_id=resource_id,
            payload=body,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )

        async with AsyncSessionLocal() as session:
            session.add(entry)
            await session.commit()
