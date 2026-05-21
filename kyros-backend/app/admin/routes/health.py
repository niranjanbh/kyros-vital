from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import templates
from app.admin.deps import get_admin_db, require_admin
from app.admin.services.metrics import db_alive, disk_usage_gb, last_alembic_version
from app.config import settings

router = APIRouter(prefix="/health")


@router.get("", response_class=Response)
async def health_view(
    request: Request,
    admin: str = Depends(require_admin),
    db: AsyncSession = Depends(get_admin_db),
) -> Response:
    import redis.asyncio as aioredis

    db_ok = await db_alive(db)
    disk = disk_usage_gb()
    alembic_ver = await last_alembic_version(db)

    redis_ok = False
    try:
        r = aioredis.from_url(settings.REDIS_URL)
        await r.ping()
        redis_ok = True
        await r.aclose()
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "health.html",
        {
            "title": "System Health",
            "admin": admin,
            "db_ok": db_ok,
            "redis_ok": redis_ok,
            "disk": disk,
            "alembic_version": alembic_ver,
            "sentry_url": settings.SENTRY_DASHBOARD_URL,
            "uptime_url": settings.UPTIME_DASHBOARD_URL,
        },
    )
