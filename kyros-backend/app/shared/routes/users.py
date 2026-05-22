import structlog
from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.exceptions import ForbiddenError
from app.core.rate_limit import limiter
from app.database import get_db
from app.shared.models.user import User
from app.shared.schemas.user import UserRead, UserUpdate

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/v1/users", tags=["Users"])


@router.post("/guest", response_model=UserRead, status_code=status.HTTP_200_OK)
@limiter.limit("10/minute")  # keyed on IP — prevents device_id farming
async def create_guest(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
) -> User:
    """Idempotent find-or-create by X-Device-Id. Returns 201 on first creation, 200 on repeat."""
    if getattr(request.state, "user_created", False):
        response.status_code = status.HTTP_201_CREATED
    return current_user


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
    if body.subscription_tier is not None:
        raise ForbiddenError("subscription_tier can only be changed by an admin.")
    if body.name is not None:
        current_user.name = body.name
    if body.age is not None:
        current_user.age = body.age
    if body.gender is not None:
        current_user.gender = body.gender
    if body.email is not None:
        current_user.email = body.email
    if body.timezone is not None:
        current_user.timezone = body.timezone

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return current_user
