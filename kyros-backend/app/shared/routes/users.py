import structlog
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.database import get_db
from app.shared.models.user import User
from app.shared.schemas.user import UserRead, UserUpdate

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post("/guest", status_code=status.HTTP_200_OK, response_model=UserRead)
async def create_guest(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    """Idempotent: returns existing user for this device_id, or creates one."""
    # Reuse the same find-or-create logic from get_current_user
    return await get_current_user(request, db)


@router.get("/me", response_model=UserRead)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    if body.email is not None:
        current_user.email = body.email
    if body.timezone is not None:
        current_user.timezone = body.timezone

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user
