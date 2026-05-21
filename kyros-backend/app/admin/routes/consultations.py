import contextlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services.audit import write_admin_audit
from app.clinic.models.consultation import Consultation

router = APIRouter(prefix="/consultations")

_PAGE_SIZE = 50
_CONFIRM_PHRASE = "UPDATE"
_VALID_STATUSES = ("requested", "scheduled", "completed", "cancelled", "no_show")


@router.get("", response_class=Response)
async def consultations_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    status: str = Query(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    offset = (page - 1) * _PAGE_SIZE
    stmt = select(Consultation)
    if status:
        stmt = stmt.where(Consultation.status == status)
    stmt = stmt.order_by(Consultation.created_at.desc()).offset(offset).limit(_PAGE_SIZE)

    rows = await db.execute(stmt)
    consultations = list(rows.scalars().all())

    count_stmt = select(func.count()).select_from(Consultation)
    if status:
        count_stmt = count_stmt.where(Consultation.status == status)
    total = (await db.execute(count_stmt)).scalar_one()

    return templates.TemplateResponse(
        request,
        "consultations_list.html",
        {
            "title": "Consultations",
            "consultations": consultations,
            "page": page,
            "total": total,
            "page_size": _PAGE_SIZE,
            "filter_status": status,
            "valid_statuses": _VALID_STATUSES,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/{consultation_id}", response_class=Response)
async def consultation_detail(
    consultation_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    row = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consult = row.scalar_one_or_none()
    if consult is None:
        return templates.TemplateResponse(
            request, "404.html", {"title": "Not Found", "admin": admin}, status_code=404
        )

    await write_admin_audit(
        db,
        request,
        action="admin.read.consultation_detail",
        resource_type="consultation",
        resource_id=consultation_id,
        payload={"patient_name": consult.patient_name, "status": consult.status},
        admin_username=admin,
    )

    return templates.TemplateResponse(
        request,
        "consultation_detail.html",
        {
            "title": f"Consultation — {consult.patient_name}",
            "consult": consult,
            "valid_statuses": _VALID_STATUSES,
            "confirm_phrase": _CONFIRM_PHRASE,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{consultation_id}/status", response_class=Response)
async def consultation_update_status(
    consultation_id: uuid.UUID,
    request: Request,
    confirmation: str = Form(default=""),
    status: str = Form(default=""),
    meeting_link: str = Form(default=""),
    meeting_provider: str = Form(default=""),
    scheduled_at_str: str = Form(default="", alias="scheduled_at"),
    notes: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    if confirmation != _CONFIRM_PHRASE:
        return RedirectResponse(
            url=f"/admin/consultations/{consultation_id}?error=Wrong+confirmation+phrase",
            status_code=303,
        )

    row = await db.execute(
        select(Consultation).where(Consultation.id == consultation_id)
    )
    consult = row.scalar_one_or_none()
    if consult is None:
        return RedirectResponse(
            url="/admin/consultations?error=Consultation+not+found", status_code=303
        )

    if status and status in _VALID_STATUSES:
        consult.status = status
    if meeting_link:
        consult.meeting_link = meeting_link
    if meeting_provider in ("zoom", "meet"):
        consult.meeting_provider = meeting_provider
    if scheduled_at_str:
        with contextlib.suppress(ValueError):
            consult.scheduled_at = datetime.fromisoformat(scheduled_at_str).replace(
                tzinfo=UTC
            )
    if notes:
        consult.notes = notes
    if status == "completed" and consult.completed_at is None:
        consult.completed_at = datetime.now(tz=UTC)

    await write_admin_audit(
        db,
        request,
        action="admin.write.update_consultation",
        resource_type="consultation",
        resource_id=consultation_id,
        payload={
            "new_status": consult.status,
            "patient_name": consult.patient_name,
        },
        admin_username=admin,
    )

    return RedirectResponse(
        url=f"/admin/consultations/{consultation_id}?flash=Consultation+updated",
        status_code=303,
    )
