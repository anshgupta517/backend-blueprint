from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings
from collections.abc import AsyncGenerator

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,  # Logs every SQL query when DEBUG=True
    pool_pre_ping=True,
    pool_size=10,  # Max persistent connections in the pool
    max_overflow=20,  # Extra connections allowed under heavy load
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — provides a database session per request.
    The 'async with' guarantees the session is closed even if an error occurs.
    """
    async with AsyncSessionLocal() as session:
        yield session