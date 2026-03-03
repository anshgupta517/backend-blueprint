from fastapi import FastAPI
from app.core.config import settings
from app.routes.v1 import users, auth


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.include_router(users.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app


app = create_app()