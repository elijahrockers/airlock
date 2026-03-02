import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)

from src.models import Base


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest.fixture
async def db_connection(engine):
    """Create a connection with a transaction that rolls back after each test."""
    async with engine.connect() as conn:
        txn = await conn.begin()
        yield conn
        await txn.rollback()


@pytest.fixture
async def db(db_connection) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(bind=db_connection, expire_on_commit=False)
    yield session
    await session.close()


@pytest.fixture
async def client(db_connection) -> AsyncGenerator[AsyncClient, None]:
    from src.database import get_db
    from src.main import app

    async def override_get_db():
        session = AsyncSession(bind=db_connection, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
