from collections.abc import AsyncGenerator

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.auth import verify_admin
from app.database import get_db


def require_admin(admin: str = Depends(verify_admin)) -> str:
    return admin


async def get_admin_db(
    _admin: str = Depends(verify_admin),
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    """DB session for admin routes with a 5-second statement timeout to protect the app."""
    await db.execute(text("SET LOCAL statement_timeout = 5000"))
    yield db  # type: ignore[misc]
