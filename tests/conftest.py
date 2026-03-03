# tests/conftest.py
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db

# --- Test Database Engine ---

test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,         
)

TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# --- Fixtures ---

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Runs ONCE for the entire test session.
    Creates all tables before tests start, drops them after.
    
    scope="session" → setup/teardown happens once for ALL tests
    autouse=True    → runs automatically, no need to request it
    """
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield   # All tests run here

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """
    Runs before and after EACH test.
    Clears all table data so tests don't affect each other.
    
    autouse=True → every test gets a clean database automatically
    """
    yield   # Test runs here

    # After each test — delete all rows but keep the table structure
    async with TestSessionLocal() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()


@pytest_asyncio.fixture
async def db_session():
    """
    Provides a real async DB session connected to the TEST database.
    Use this when testing services/repos directly.
    """
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    Provides an async HTTP test client connected to your FastAPI app.
    
    The key trick: we override get_db() to use the TEST database session.
    Without this override, routes would hit your real development database.
    """
    async def override_get_db():
        yield db_session

    # Dependency override — swap real DB for test DB
    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up the override after test
    app.dependency_overrides.clear()


# --- Helper Fixtures ---

@pytest_asyncio.fixture
async def test_user(client: AsyncClient) -> dict:
    """
    Creates a real user via the API and returns the response data.
    Use this in tests that need an existing user.
    """
    response = await client.post("/api/v1/users", json={
        "name": "Test User",
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient, test_user: dict) -> dict:
    """
    Logs in as test_user and returns the Authorization header.
    Use this in tests that need an authenticated request.
    
    Usage:
        async def test_something(client, auth_headers):
            response = await client.get("/protected", headers=auth_headers)
    """
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpassword123",
    })
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}