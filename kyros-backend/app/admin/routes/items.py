import uuid

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services.audit import write_admin_audit
from app.shared.models.user import User
from app.wellness.models.reminder import Reminder
from app.wellness.models.tracked_item import TrackedItem

router = APIRouter(prefix="/items")

_PAGE_SIZE = 50
_CONFIRM_PHRASE = "DISCONTINUE"


@router.get("", response_class=Response)
async def items_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    status: str = Query(default=""),
    category: str = Query(default=""),
    source: str = Query(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    offset = (page - 1) * _PAGE_SIZE
    stmt = select(TrackedItem)
    if status:
        stmt = stmt.where(TrackedItem.status == status)
    if category:
        stmt = stmt.where(TrackedItem.category == category)
    if source:
        stmt = stmt.where(TrackedItem.source == source)
    stmt = stmt.order_by(TrackedItem.created_at.desc()).offset(offset).limit(_PAGE_SIZE)

    rows = await db.execute(stmt)
    items = list(rows.scalars().all())

    count_stmt = select(func.count()).select_from(TrackedItem)
    if status:
        count_stmt = count_stmt.where(TrackedItem.status == status)
    total = (await db.execute(count_stmt)).scalar_one()

    # Fetch reminder counts per item
    reminder_counts: dict[uuid.UUID, int] = {}
    if items:
        item_ids = [i.id for i in items]
        count_rows = await db.execute(
            select(Reminder.tracked_item_id, func.count())
            .where(Reminder.tracked_item_id.in_(item_ids))
            .group_by(Reminder.tracked_item_id)
        )
        reminder_counts = {row[0]: row[1] for row in count_rows.all()}

    # Resolve user identifiers for display
    user_ids = list({i.user_id for i in items})
    user_map: dict[uuid.UUID, str] = {}
    if user_ids:
        user_rows = await db.execute(select(User).where(User.id.in_(user_ids)))
        for u in user_rows.scalars():
            user_map[u.id] = u.email or u.device_id or str(u.id)[:8]

    return templates.TemplateResponse(
        request,
        "items_list.html",
        {
            "title": "Tracked Items",
            "items": items,
            "reminder_counts": reminder_counts,
            "user_map": user_map,
            "page": page,
            "total": total,
            "page_size": _PAGE_SIZE,
            "filter_status": status,
            "filter_category": category,
            "filter_source": source,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/{item_id}/discontinue", response_class=Response)
async def discontinue_confirm_get(
    item_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    row = await db.execute(select(TrackedItem).where(TrackedItem.id == item_id))
    item = row.scalar_one_or_none()
    if item is None or item.status != "active":
        return RedirectResponse(
            url="/admin/items?error=Item+not+found+or+not+active", status_code=303
        )

    return templates.TemplateResponse(
        request,
        "confirm_action.html",
        {
            "title": "Confirm Discontinue",
            "admin": admin,
            "action_label": f"Discontinue tracked item: {item.name}",
            "action_description": (
                "This will set the item status to 'discontinued' and deactivate "
                "all associated reminders. This cannot be undone from the UI."
            ),
            "confirmation_phrase": _CONFIRM_PHRASE,
            "submit_url": f"/admin/items/{item_id}/discontinue",
            "cancel_url": "/admin/items",
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{item_id}/discontinue", response_class=Response)
async def discontinue_confirm_post(
    item_id: uuid.UUID,
    request: Request,
    confirmation: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    if confirmation != _CONFIRM_PHRASE:
        return RedirectResponse(
            url=f"/admin/items/{item_id}/discontinue?error=Wrong+confirmation+phrase",
            status_code=303,
        )

    row = await db.execute(select(TrackedItem).where(TrackedItem.id == item_id))
    item = row.scalar_one_or_none()
    if item is None:
        return RedirectResponse(url="/admin/items?error=Item+not+found", status_code=303)

    item.status = "discontinued"

    # Deactivate all reminders in the same transaction
    reminder_rows = await db.execute(
        select(Reminder).where(Reminder.tracked_item_id == item_id)
    )
    for reminder in reminder_rows.scalars():
        reminder.active = False

    await write_admin_audit(
        db,
        request,
        action="admin.write.discontinue_item",
        resource_type="tracked_item",
        resource_id=item_id,
        payload={"item_name": item.name, "category": item.category},
        admin_username=admin,
    )

    return RedirectResponse(
        url=f"/admin/items?flash=Item+{item.name}+discontinued", status_code=303
    )
