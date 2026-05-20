import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Import all models so Base.metadata is fully populated before create_all
import app.shared.models  # noqa: F401
import app.wellness.models  # noqa: F401
from app.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://kyros:kyros@localhost:5433/kyros_test"


async def _run_schema(drop: bool = False) -> None:
    """Create (or drop+create) test schema in a self-contained event loop run."""
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        if drop:
            await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()


async def _drop_schema() -> None:
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest.fixture(scope="session", autouse=True)
def _setup_schema() -> "Generator[None, None, None]":
    """Session-scoped SYNC fixture — schema setup via asyncio.run() avoids loop-scope issues."""
    asyncio.run(_run_schema(drop=True))
    yield
    asyncio.run(_drop_schema())


# Type stub for the generator — not imported at runtime
from collections.abc import Generator  # noqa: E402


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    # NullPool + function-scoped loop: fresh connection each test, no cross-loop contamination.
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    session_factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session
    await eng.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        yield db

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
