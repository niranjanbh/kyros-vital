import uuid
from typing import Any

import structlog
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.audit_log import AuditLog

log = structlog.get_logger(__name__)


async def write_admin_audit(
    db: AsyncSession,
    request: Request,
    action: str,
    resource_type: str | None = None,
    resource_id: uuid.UUID | None = None,
    payload: dict[str, Any] | None = None,
    admin_username: str = "",
) -> None:
    """Write an audit_log row for every admin read/write action.

    PHI fields (notes, payload, metadata, etc.) are stored in the DB for legal traceability
    but are redacted from structlog output by the global redact_phi processor.
    """
    log_payload: dict[str, Any] = {"admin_username": admin_username}
    if payload:
        log_payload.update(payload)

    # structlog will redact PHI keys via the redact_phi processor before output
    log.info(
        "admin.audit",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        payload=log_payload,
        path=str(request.url.path),
    )

    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=None,  # admin actions are not tied to a user row
        actor_type="admin",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=log_payload,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(entry)
    await db.flush()
