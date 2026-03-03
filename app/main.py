from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import logger
from app.routes.v1 import users, auth


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # --- Middleware (runs on every request) ---
    app.add_middleware(RequestLoggingMiddleware)

    # --- Exception Handlers ---
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # --- Routers ---
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    # --- Startup/Shutdown Events ---
    @app.on_event("startup")
    async def startup():
        logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info(f"Shutting down {settings.app_name}")

    @app.get("/health")
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
        }

    return app


app = create_app()