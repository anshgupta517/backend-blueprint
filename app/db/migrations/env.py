import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import your app's settings and models
from app.core.config import settings
from app.db.base import Base

# Import all models here so Alembic can detect them
# Every new model file created must be imported here
from app.models import User  # noqa: F401

# Alembic Config object
config = context.config

# Override the sqlalchemy.url with our dynamic value from .env
# We use the sync URL here because Alembic's config expects it
# then we convert to async below
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.replace("postgresql+asyncpg", "postgresql+asyncpg"),
)

# Set up logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations without a live DB connection.
    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations with a live async DB connection.
    This is the normal mode.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,    # No connection pooling for migrations
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


# Entry point — Alembic calls this
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())