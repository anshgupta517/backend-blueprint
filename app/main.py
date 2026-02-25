from fastapi import FastAPI
from app.core.config import settings


def create_app() -> FastAPI:
    """
    Application factory pattern.
    """
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,  # Hide docs in prod
        redoc_url="/redoc" if not settings.is_production else None,
    )

    @app.get("/health")
    async def health_check():
        """
        Always have a health check endpoint.
        """
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app

app = create_app()