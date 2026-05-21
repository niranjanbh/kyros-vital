import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.shared.models.audit_log import AuditLog

router = APIRouter(prefix="/audit")

_PAGE_SIZE = 50


@router.get("", response_class=Response)
async def audit_log_view(
    request: Request,
    page: int = Query(default=1, ge=1),
    actor_type: str = Query(default=""),
    action: str = Query(default=""),
    user_id: str = Query(default=""),
    from_date: str = Query(default=""),
    to_date: str = Query(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    offset = (page - 1) * _PAGE_SIZE
    stmt = select(AuditLog)

    if actor_type:
        stmt = stmt.where(AuditLog.actor_type == actor_type)
    if action:
        stmt = stmt.where(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        try:
            uid = uuid.UUID(user_id)
            stmt = stmt.where(AuditLog.user_id == uid)
        except ValueError:
            pass
    if from_date:
        try:
            dt = datetime.fromisoformat(from_date).replace(tzinfo=UTC)
            stmt = stmt.where(AuditLog.occurred_at >= dt)
        except ValueError:
            pass
    if to_date:
        try:
            dt = datetime.fromisoformat(to_date).replace(tzinfo=UTC)
            stmt = stmt.where(AuditLog.occurred_at <= dt)
        except ValueError:
            pass

    stmt = stmt.order_by(AuditLog.occurred_at.desc()).offset(offset).limit(_PAGE_SIZE)
    rows = await db.execute(stmt)
    entries = list(rows.scalars().all())

    # Count without limit for pagination
    count_stmt = select(AuditLog.id)
    total_rows = await db.execute(count_stmt)
    total = len(total_rows.all())

    return templates.TemplateResponse(
        request,
        "audit_log.html",
        {
            "title": "Audit Log",
            "entries": entries,
            "page": page,
            "total": total,
            "page_size": _PAGE_SIZE,
            "filter_actor_type": actor_type,
            "filter_action": action,
            "filter_user_id": user_id,
            "filter_from_date": from_date,
            "filter_to_date": to_date,
            "admin": admin,
        },
    )
