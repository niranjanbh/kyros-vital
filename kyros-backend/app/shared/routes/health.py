from typing import Any

import structlog
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from redis.asyncio import from_url as redis_from_url
from sqlalchemy import text

from app.config import settings
from app.core.storage import get_storage
from app.database import AsyncSessionLocal

log = structlog.get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> JSONResponse:
    db_ok = False
    redis_ok = False
    storage_ok = False

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        log.exception("health.db_check_failed")

    try:
        r = redis_from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
        redis_ok = True
    except Exception:
        log.warning("health.redis_check_failed")

    try:
        storage = get_storage()
        await storage.signed_url("healthcheck")
        storage_ok = True
    except Exception:
        log.exception("health.storage_check_failed")

    healthy = db_ok  # DB is the critical dependency; Redis/storage degraded is tolerable
    body: dict[str, Any] = {
        "status": "ok" if healthy else "degraded",
        "db": "reachable" if db_ok else "unreachable",
        "redis": "reachable" if redis_ok else "unreachable",
        "storage": "reachable" if storage_ok else "unreachable",
    }
    # Don't expose version or environment to the public in production
    if not settings.is_production:
        body["version"] = "0.1.0"
        body["env"] = settings.ENV

    return JSONResponse(content=body, status_code=200 if healthy else 503)
