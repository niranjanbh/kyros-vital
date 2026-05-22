import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services.audit import write_admin_audit
from app.shared.models.audit_log import AuditLog
from app.shared.models.user import User
from app.wellness.models.log_entry import LogEntry
from app.wellness.models.tracked_item import TrackedItem

router = APIRouter(prefix="/users")

_PAGE_SIZE = 50
_DEACTIVATE_PHRASE = "DEACTIVATE"
_DELETE_PHRASE = "DELETE"
_VALID_TIERS = ("free", "plus", "kyros")
_VALID_ROLES = ("user", "superadmin")

_ADHERENCE_WINDOW_DAYS = 30


async def _compute_item_adherence(
    db: AsyncSession, user_id: uuid.UUID, items: list[Any]
) -> dict[uuid.UUID, dict[str, Any]]:
    """Return per-item adherence stats for the last 30 days.

    Returns a dict keyed by TrackedItem.id with keys:
        taken, skipped, snoozed, logged_value, total, rate (float | None)
    """
    if not items:
        return {}

    cutoff = datetime.now(UTC) - timedelta(days=_ADHERENCE_WINDOW_DAYS)
    item_ids = [i.id for i in items]

    rows = await db.execute(
        select(LogEntry.tracked_item_id, LogEntry.action, func.count().label("cnt"))
        .where(LogEntry.user_id == user_id)
        .where(LogEntry.tracked_item_id.in_(item_ids))
        .where(LogEntry.occurred_at >= cutoff)
        .group_by(LogEntry.tracked_item_id, LogEntry.action)
    )

    # Pivot: {item_id: {action: count}}
    pivot: dict[uuid.UUID, dict[str, int]] = {}
    for item_id, action, cnt in rows.all():
        pivot.setdefault(item_id, {})[action] = cnt

    result: dict[uuid.UUID, dict[str, Any]] = {}
    for item in items:
        ac = pivot.get(item.id, {})
        taken = ac.get("taken", 0) + ac.get("logged_value", 0) + ac.get("acknowledged", 0)
        skipped = ac.get("skipped", 0)
        snoozed = ac.get("snoozed", 0)
        total = sum(ac.values())
        denom = taken + skipped
        result[item.id] = {
            "taken": taken,
            "skipped": skipped,
            "snoozed": snoozed,
            "total": total,
            "rate": (taken / denom) if denom > 0 else None,
        }
    return result


@router.get("", response_class=Response)
async def users_list(
    request: Request,
    page: int = Query(default=1, ge=1),
    q: str = Query(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    offset = (page - 1) * _PAGE_SIZE

    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(User.device_id.ilike(like) | User.email.ilike(like))
    stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(_PAGE_SIZE)

    rows = await db.execute(stmt)
    users = list(rows.scalars().all())

    count_stmt = select(func.count()).select_from(User)
    if q:
        like = f"%{q}%"
        count_stmt = count_stmt.where(User.device_id.ilike(like) | User.email.ilike(like))
    total = (await db.execute(count_stmt)).scalar_one()

    return templates.TemplateResponse(
        request,
        "users_list.html",
        {
            "title": "Users",
            "users": users,
            "page": page,
            "total": total,
            "page_size": _PAGE_SIZE,
            "q": q,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


@router.get("/{user_id}", response_class=Response)
async def user_detail(
    user_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return templates.TemplateResponse(
            request, "404.html", {"title": "Not Found", "admin": admin}, status_code=404
        )

    items_row = await db.execute(
        select(TrackedItem)
        .where(TrackedItem.user_id == user_id)
        .order_by(TrackedItem.created_at.desc())
    )
    items = list(items_row.scalars().all())

    logs_row = await db.execute(
        select(LogEntry)
        .where(LogEntry.user_id == user_id)
        .order_by(LogEntry.occurred_at.desc())
        .limit(30)
    )
    recent_logs = list(logs_row.scalars().all())

    audit_row = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.occurred_at.desc())
        .limit(30)
    )
    recent_audit = list(audit_row.scalars().all())

    item_adherence = await _compute_item_adherence(db, user_id, items)

    await write_admin_audit(
        db,
        request,
        action="admin.read.user_detail",
        resource_type="user",
        resource_id=user_id,
        payload={"user_device_id": user.device_id},
        admin_username=admin,
    )

    return templates.TemplateResponse(
        request,
        "user_detail.html",
        {
            "title": f"User {str(user_id)[:8]}",
            "user": user,
            "items": items,
            "item_adherence": item_adherence,
            "adherence_window_days": _ADHERENCE_WINDOW_DAYS,
            "recent_logs": recent_logs,
            "recent_audit": recent_audit,
            "valid_tiers": _VALID_TIERS,
            "valid_roles": _VALID_ROLES,
            "admin": admin,
            "flash": request.query_params.get("flash"),
            "error": request.query_params.get("error"),
        },
    )


_VALID_GENDERS = ("male", "female", "other", "prefer_not_to_say")


async def _load_user_detail_context(
    user_id: uuid.UUID,
    db: AsyncSession,
    admin: str,
) -> dict:
    """Shared context loader for the user detail page (used by GET and failed POST)."""
    items_row = await db.execute(
        select(TrackedItem)
        .where(TrackedItem.user_id == user_id)
        .order_by(TrackedItem.created_at.desc())
    )
    items = list(items_row.scalars().all())

    logs_row = await db.execute(
        select(LogEntry)
        .where(LogEntry.user_id == user_id)
        .order_by(LogEntry.occurred_at.desc())
        .limit(30)
    )
    audit_row = await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.occurred_at.desc())
        .limit(30)
    )
    item_adherence = await _compute_item_adherence(db, user_id, items)

    return {
        "items": items,
        "item_adherence": item_adherence,
        "adherence_window_days": _ADHERENCE_WINDOW_DAYS,
        "recent_logs": list(logs_row.scalars().all()),
        "recent_audit": list(audit_row.scalars().all()),
        "valid_tiers": _VALID_TIERS,
        "valid_roles": _VALID_ROLES,
        "admin": admin,
    }


@router.post("/{user_id}/edit", response_class=Response)
async def user_edit(
    user_id: uuid.UUID,
    request: Request,
    name: str = Form(default=""),
    age: str = Form(default=""),
    gender: str = Form(default=""),
    email: str = Form(default=""),
    timezone: str = Form(default=""),
    subscription_tier: str = Form(default=""),
    role: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    # ── Server-side validation for mandatory fields ───────────────────────────
    errors: list[str] = []

    stripped_name = name.strip()
    if not stripped_name:
        errors.append("Full name is required.")

    age_int: int | None = None
    if not age.strip():
        errors.append("Age is required.")
    else:
        try:
            age_int = int(age)
            if not (1 <= age_int <= 129):
                errors.append("Age must be between 1 and 129.")
        except ValueError:
            errors.append("Age must be a whole number.")

    if gender not in _VALID_GENDERS:
        errors.append("Gender is required — please select an option.")

    if errors:
        ctx = await _load_user_detail_context(user_id, db, admin)
        return templates.TemplateResponse(
            request,
            "user_detail.html",
            {
                **ctx,
                "title": f"User {str(user_id)[:8]}",
                "user": user,
                "error": " ".join(errors),
            },
            status_code=422,
        )

    # ── Apply changes ─────────────────────────────────────────────────────────
    changed: list[str] = []

    if stripped_name != (user.name or ""):
        user.name = stripped_name
        changed.append("name")

    if age_int is not None and age_int != user.age:
        user.age = age_int
        changed.append("age")

    if gender != user.gender:
        user.gender = gender
        changed.append("gender")

    if email.strip() and email.strip() != user.email:
        user.email = email.strip()
        changed.append("email")

    if timezone.strip() and timezone.strip() != user.timezone:
        user.timezone = timezone.strip()
        changed.append("timezone")

    if subscription_tier in _VALID_TIERS and subscription_tier != user.subscription_tier:
        user.subscription_tier = subscription_tier
        changed.append("subscription_tier")

    if role in _VALID_ROLES and role != user.role:
        user.role = role
        changed.append("role")

    if changed:
        await write_admin_audit(
            db,
            request,
            action="admin.write.edit_user",
            resource_type="user",
            resource_id=user_id,
            payload={"changed_fields": changed},
            admin_username=admin,
        )

    return RedirectResponse(
        url=f"/admin/users/{user_id}?flash=User+updated+successfully", status_code=303
    )


@router.get("/{user_id}/deactivate", response_class=Response)
async def deactivate_confirm_get(
    user_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    if not user.is_active:
        # Already inactive — offer reactivation instead
        return templates.TemplateResponse(
            request,
            "confirm_action.html",
            {
                "title": "Reactivate User",
                "admin": admin,
                "action_label": f"Reactivate user: {user.email or user.device_id}",
                "action_description": "This will restore API access for this user.",
                "confirmation_phrase": "REACTIVATE",
                "submit_url": f"/admin/users/{user_id}/deactivate",
                "cancel_url": f"/admin/users/{user_id}",
                "error": request.query_params.get("error"),
            },
        )

    return templates.TemplateResponse(
        request,
        "confirm_action.html",
        {
            "title": "Deactivate User",
            "admin": admin,
            "action_label": f"Deactivate user: {user.email or user.device_id}",
            "action_description": (
                "This blocks all API access for this user. "
                "Their data is preserved. You can reactivate them later."
            ),
            "confirmation_phrase": _DEACTIVATE_PHRASE,
            "submit_url": f"/admin/users/{user_id}/deactivate",
            "cancel_url": f"/admin/users/{user_id}",
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{user_id}/deactivate", response_class=Response)
async def deactivate_confirm_post(
    user_id: uuid.UUID,
    request: Request,
    confirmation: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    expected = "REACTIVATE" if not user.is_active else _DEACTIVATE_PHRASE
    if confirmation != expected:
        return RedirectResponse(
            url=f"/admin/users/{user_id}/deactivate?error=Wrong+confirmation+phrase",
            status_code=303,
        )

    old_state = user.is_active
    user.is_active = not old_state

    await write_admin_audit(
        db,
        request,
        action="admin.write.deactivate_user" if old_state else "admin.write.reactivate_user",
        resource_type="user",
        resource_id=user_id,
        payload={"was_active": old_state, "now_active": user.is_active},
        admin_username=admin,
    )

    verb = "deactivated" if old_state else "reactivated"
    return RedirectResponse(
        url=f"/admin/users/{user_id}?flash=User+{verb}", status_code=303
    )


@router.get("/{user_id}/delete", response_class=Response)
async def delete_confirm_get(
    user_id: uuid.UUID,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    return templates.TemplateResponse(
        request,
        "confirm_action.html",
        {
            "title": "Permanently Delete User",
            "admin": admin,
            "action_label": f"DELETE user: {user.email or user.device_id or str(user_id)[:8]}",
            "action_description": (
                "Permanently removes this user and ALL their data "
                "(tracked items, reminders, logs, measurements, lab reports). "
                "This cannot be undone."
            ),
            "confirmation_phrase": _DELETE_PHRASE,
            "submit_url": f"/admin/users/{user_id}/delete",
            "cancel_url": f"/admin/users/{user_id}",
            "error": request.query_params.get("error"),
        },
    )


@router.post("/{user_id}/delete", response_class=Response)
async def delete_confirm_post(
    user_id: uuid.UUID,
    request: Request,
    confirmation: str = Form(default=""),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    if confirmation != _DELETE_PHRASE:
        return RedirectResponse(
            url=f"/admin/users/{user_id}/delete?error=Wrong+confirmation+phrase",
            status_code=303,
        )

    user_row = await db.execute(select(User).where(User.id == user_id))
    user = user_row.scalar_one_or_none()
    if user is None:
        return RedirectResponse(url="/admin/users?error=User+not+found", status_code=303)

    identity = user.email or user.device_id or str(user_id)[:8]

    # Audit before delete (row will be gone after)
    await write_admin_audit(
        db,
        request,
        action="admin.write.delete_user",
        resource_type="user",
        resource_id=user_id,
        payload={"identity": identity},
        admin_username=admin,
    )
    await db.flush()

    await db.delete(user)

    return RedirectResponse(
        url=f"/admin/users?flash=User+{identity}+permanently+deleted", status_code=303
    )
