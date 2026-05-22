from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services import error_log as svc

router = APIRouter(prefix="/errors")

PAGE_SIZE = svc.PAGE_SIZE


@router.get("", response_class=Response)
async def errors_list(
    request: Request,
    page: int = 1,
    status_code: str = "",
    path_contains: str = "",
    error_type: str = "",
    from_date: str = "",
    to_date: str = "",
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    sc = int(status_code) if status_code.strip().isdigit() else None
    fd = _parse_date(from_date)
    td = _parse_date(to_date)

    entries, total = await svc.list_errors(
        db,
        page=page,
        status_code=sc,
        path_contains=path_contains or None,
        error_type=error_type or None,
        from_date=fd,
        to_date=td,
    )
    summary = await svc.error_summary_last_24h(db)

    return templates.TemplateResponse(
        request,
        "error_log.html",
        {
            "title": "Error Logs",
            "admin": admin,
            "entries": entries,
            "total": total,
            "page": page,
            "page_size": PAGE_SIZE,
            "summary_24h": summary,
            "filter_status_code": status_code,
            "filter_path": path_contains,
            "filter_error_type": error_type,
            "filter_from_date": from_date,
            "filter_to_date": to_date,
        },
    )


@router.get("/{error_id}", response_class=Response)
async def error_detail(
    error_id: str,
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    entry = await svc.get_error(db, error_id)
    if entry is None:
        return templates.TemplateResponse(
            request, "404.html", {"title": "Not found", "admin": admin}, status_code=404
        )
    return templates.TemplateResponse(
        request,
        "error_detail.html",
        {"title": f"Error {entry.status_code}", "admin": admin, "entry": entry},
    )


@router.post("/purge", response_class=Response)
async def purge_old_errors(
    request: Request,
    days: int = Form(default=30),
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    deleted = await svc.delete_old_errors(db, days=days)
    return HTMLResponse(
        f'<p style="color:var(--positive)">Deleted {deleted} entries older than {days} days. '
        f'<a href="/admin/errors">Back</a></p>'
    )


def _parse_date(s: str) -> date | None:
    try:
        return date.fromisoformat(s) if s else None
    except ValueError:
        return None
