import uuid

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services.audit import write_admin_audit
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

router = APIRouter(prefix="/reminders")

_PAGE_SIZE = 50
_CONFIRM_PHRASE = "TOGGLE"


@router.get("", response_class=Response)
async def reminders_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    offset = (page - 1) * _PAGE_SIZE
    stmt = (
        select(Reminder, TrackedItem.name, TrackedItem.category)
        .join(TrackedItem, Reminder.tracked_item_id == TrackedItem.id)
        .order_by(Reminder.created_at.desc())
        .offset(offset)
        .limit(_PAGE_SIZE)
    )
    rows = await db.execute(stmt)
    results = rows.all()

    total = (await db.execute(select(func.count()).select_from(Reminder))).scalar_one()

    return templates.TemplateResponse(
        request,
        "reminders_list.html",
        {
            "title": "Reminders",
            "results": results,
            "page": page,
            "total": total,
            "page_size": _PAGE_SIZE,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/{reminder_id}/toggle", response_class=Response)
async def toggle_confirm_get(
    reminder_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    row = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = row.scalar_one_or_none()
    if reminder is None:
        return RedirectResponse(url="/admin/reminders?error=Reminder+not+found", status_code=303)

    verb = "Pause" if reminder.active else "Resume"
    return templates.TemplateResponse(
        request,
        "confirm_action.html",
        {
            "title": f"Confirm {verb} Reminder",
            "admin": admin,
            "action_label": f"{verb} reminder {str(reminder_id)[:8]}",
            "action_description": (
                f"This will {'deactivate' if reminder.active else 'reactivate'} the reminder."
            ),
            "confirmation_phrase": _CONFIRM_PHRASE,
            "submit_url": f"/admin/reminders/{reminder_id}/toggle",
            "cancel_url": "/admin/reminders",
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{reminder_id}/toggle", response_class=Response)
async def toggle_confirm_post(
    reminder_id: uuid.UUID,
    request: Request,
    confirmation: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    if confirmation != _CONFIRM_PHRASE:
        return RedirectResponse(
            url=f"/admin/reminders/{reminder_id}/toggle?error=Wrong+confirmation+phrase",
            status_code=303,
        )

    row = await db.execute(select(Reminder).where(Reminder.id == reminder_id))
    reminder = row.scalar_one_or_none()
    if reminder is None:
        return RedirectResponse(url="/admin/reminders?error=Reminder+not+found", status_code=303)

    old_state = reminder.active
    reminder.active = not old_state

    await write_admin_audit(
        db,
        request,
        action="admin.write.toggle_reminder",
        resource_type="reminder",
        resource_id=reminder_id,
        payload={"was_active": old_state, "now_active": reminder.active},
        admin_username=admin,
    )

    verb = "paused" if old_state else "resumed"
    return RedirectResponse(
        url=f"/admin/reminders?flash=Reminder+{str(reminder_id)[:8]}+{verb}", status_code=303
    )
