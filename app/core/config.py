from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):

    # App
    app_name: str = "My Backend"
    app_env: str = "development"
    debug: bool = False
    secret_key: str

    # CORS
    cors_origins: str = (
        "http://localhost:3000"  # Comma-separated list of allowed origins
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str) -> str:
        """Store as string, we'll split it when needed."""
        return v

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug(cls, v: bool | str) -> bool | str:
        if isinstance(v, str):
            normalized = v.strip().lower()
            if normalized in {"1", "true", "yes", "on", "debug", "development", "dev"}:
                return True
            if normalized in {
                "0",
                "false",
                "no",
                "off",
                "release",
                "production",
                "prod",
            }:
                return False
        return v

    @property
    def cors_origins_list(self) -> list[str]:
        """Returns origins as a list for FastAPI's CORSMiddleware."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Database
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str

    # Test database
    postgres_test_db: str = "appdb_test"

    @property
    def test_database_url(self) -> str:
        """Separate async URL pointing at the test database."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_test_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Email (SMTP)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_tls: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "noreply@myapp.com"

    # JWT
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    enable_prometheus: bool = False
    enable_sentry: bool = False

    # Sentry
    sentry_dsn: str = ""  # empty = disabled

    # Google OAuth2
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"

    @property
    def google_oauth_enabled(self) -> bool:
        """Only enable if both credentials are configured."""
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def database_url(self) -> str:
        """
        Async PostgreSQL connection string.
        """
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    """
    return Settings()


settings = get_settings()
