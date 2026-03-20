import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool  # No connection pooling for tests
from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.core.rate_limit import (
    login_rate_limit,
    change_password_rate_limit,
    no_rate_limit,
)
from unittest.mock import AsyncMock, patch, patch, MagicMock

# --- Engine scoped to the whole session ---
# Created once, shared across all tests (just the engine, not connections)

test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,
    poolclass=NullPool,
    # pool_size not set — NullPool is better for tests
    # Each test gets a fresh connection, no sharing
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- Database setup/teardown ---


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Creates all tables once before the test session starts.
    Drops everything after all tests complete.
    scope="session" → runs once total, not once per test.
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """
    Wipes all rows between tests.
    Each test starts with a completely empty database.
    autouse=True → applies to every test automatically.
    """
    yield

    # Use a fresh connection for cleanup — never reuse a potentially
    # corrupted connection from the test itself
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


# --- Per-test fixtures ---


@pytest_asyncio.fixture
async def db_session():
    """
    Fresh AsyncSession for each test.
    Uses 'async with' so it's always properly closed after the test,
    even if the test raises an exception.
    """
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()  # Roll back any uncommitted changes


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    HTTP test client with the real DB swapped for the test DB.
    Fresh client per test — no shared state between tests.
    """

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[login_rate_limit] = no_rate_limit
    app.dependency_overrides[change_password_rate_limit] = no_rate_limit

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """Creates a real user via the API. Returns the response body."""
    response = await client.post(
        "/api/v1/users",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 201, response.json()
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """Logs in as test_user and returns ready-to-use auth headers."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200, response.json()
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(autouse=True)
async def disable_cache():
    """
    Replace all cache operations with no-ops in tests.
    Tests should test business logic, not cache behaviour.
    Cache behaviour has its own dedicated tests if needed.
    """
    with (
        patch("app.core.cache.cache.get", new_callable=AsyncMock, return_value=None),
        patch("app.core.cache.cache.set", new_callable=AsyncMock, return_value=True),
        patch("app.core.cache.cache.delete", new_callable=AsyncMock, return_value=True),
        patch(
            "app.core.cache.cache.delete_pattern",
            new_callable=AsyncMock,
            return_value=0,
        ),
    ):
        yield


@pytest.fixture(autouse=True)
def disable_celery():
    """
    Replace .delay() with a no-op in tests.
    Tests should not depend on a running Celery worker.
    """
    with patch(
        "app.worker.tasks.email.send_welcome_email.delay",
        return_value=MagicMock(id="test-task-id"),
    ):
        yield


@pytest.fixture(autouse=True)
def mock_event_bus():
    """
    Replace event_bus.publish with a no-op in tests.
    Tests verify service behaviour, not event side effects.
    Event handlers have their own dedicated tests.
    """
    with patch(
        "app.events.bus.event_bus.publish",
        new_callable=AsyncMock,
    ) as mock_publish:
        yield mock_publish
