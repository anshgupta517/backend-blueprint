from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from app.core.cache import cache
from app.core.config import settings
from app.core.middleware import RequestLoggingMiddleware, RequestSizeLimitMiddleware
from fastapi.middleware.cors import CORSMiddleware
from app.core.exceptions import (
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler,
)
from app.core.logging import logger
from app.routes.v1 import users, auth

from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    if settings.app_env != "test":
        await cache.connect()
    yield
    
    # Shutdown
    if settings.app_env != "test":
        await cache.disconnect()
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── Middleware ───────────────────────────────────────────────
    app.add_middleware(CORSMiddleware,          
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestSizeLimitMiddleware, max_content_length=1024 * 1024)  # 1MB limit 
    app.add_middleware(RequestLoggingMiddleware)                         
    app.add_middleware(SecurityHeadersMiddleware)                        

    # ── Exception Handlers ───────────────────────────────────────
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Rate Limiting ────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")

    @app.get("/health", methods=["GET"])
    async def health_check():
        return {"status": "Server Running"}

    return app


app = create_app()