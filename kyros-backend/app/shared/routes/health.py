from typing import Any

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.core.storage import get_storage
from app.database import AsyncSessionLocal

log = structlog.get_logger(__name__)
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    db_status = "unreachable"
    storage_status = "unreachable"

    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_status = "reachable"
    except Exception:
        log.exception("health.db_check_failed")

    try:
        storage = get_storage()
        await storage.signed_url("healthcheck")
        storage_status = "reachable"
    except Exception:
        log.exception("health.storage_check_failed")

    return {
        "status": "ok",
        "version": "0.1.0",
        "env": settings.ENV,
        "db": db_status,
        "storage": storage_status,
    }
