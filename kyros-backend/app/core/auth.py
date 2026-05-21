import re

import structlog
from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthError
from app.database import get_db
from app.shared.models.user import User

log = structlog.get_logger(__name__)

_DEVICE_ID_RE = re.compile(r"^[a-zA-Z0-9\-]{16,64}$")


def _validate_device_id(device_id: str | None) -> str:
    if not device_id:
        raise AuthError("X-Device-Id header is required.")
    if not _DEVICE_ID_RE.match(device_id):
        raise AuthError("X-Device-Id must be 16–64 alphanumeric characters or dashes.")
    return device_id


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    device_id = _validate_device_id(request.headers.get("X-Device-Id"))

    result = await db.execute(select(User).where(User.device_id == device_id))
    user = result.scalar_one_or_none()

    if user is not None and not user.is_active:
        raise AuthError("This account has been deactivated.")

    if user is None:
        await db.execute(
            text("INSERT INTO users (device_id) VALUES (:device_id) ON CONFLICT DO NOTHING"),
            {"device_id": device_id},
        )
        await db.flush()
        result = await db.execute(select(User).where(User.device_id == device_id))
        user = result.scalar_one()
        log.info("user.created", device_id=device_id, user_id=str(user.id))
        request.state.user_created = True
    else:
        request.state.user_created = False

    request.state.user = user
    return user
