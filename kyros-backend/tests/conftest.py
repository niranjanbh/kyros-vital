import asyncio
import os
import tempfile
from collections.abc import AsyncGenerator, Generator

# Set DATABASE_URL *before* any app module is imported so that
# app.database.engine, AsyncSessionLocal, and the audit middleware all
# point at the test database.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://kyros:kyros@localhost:5433/kyros_test")
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("STORAGE_DIR", tempfile.mkdtemp(prefix="kyros_test_storage_"))
os.environ.setdefault("SIGNING_SECRET", "test-signing-secret")
os.environ.setdefault("ADMIN_USERNAME", "testadmin")
# Pre-computed bcrypt hash for "testpassword" — avoids bcrypt cost per test run
os.environ.setdefault(
    "ADMIN_PASSWORD_HASH",
    "$2b$12$Z4ADivVyenK.e9gZybyu.O/90einLThkuexEX9YEwi1OVCCuJdjp.",
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

# Import all models so Base.metadata is fully populated before create_all
import app.clinic.models  # noqa: F401, E402
import app.shared.models  # noqa: F401, E402
import app.wellness.models  # noqa: F401, E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

TEST_DATABASE_URL = "postgresql+asyncpg://kyros:kyros@localhost:5433/kyros_test"


async def _run_schema(drop: bool = False) -> None:
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
def _setup_schema() -> Generator[None, None, None]:
    """Session-scoped sync fixture — asyncio.run() keeps schema setup in its own loop."""
    asyncio.run(_run_schema(drop=True))
    yield
    asyncio.run(_drop_schema())


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    # NullPool + function-scoped loop: fresh connection per test, no cross-loop contamination.
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
    factory = async_sessionmaker(
        bind=eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with factory() as session:
        yield session
    await eng.dispose()


@pytest_asyncio.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def _override_db() -> AsyncGenerator[AsyncSession, None]:
        try:
            yield db
            await db.commit()  # mirror real get_db so FK-dependent middleware sees committed rows
        except Exception:
            await db.rollback()
            raise

    app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
