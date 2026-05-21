from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services import metrics as svc
from app.config import settings

router = APIRouter()


@router.get("/", response_class=Response)
async def dashboard(
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    data = await svc.get_dashboard_metrics(db)
    recent = await svc.get_recent_audit(db, limit=20)
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "title": "Dashboard",
            "admin": admin,
            "metrics": data,
            "recent_audit": recent,
            "sentry_url": settings.SENTRY_DASHBOARD_URL,
            "uptime_url": settings.UPTIME_DASHBOARD_URL,
        },
    )
