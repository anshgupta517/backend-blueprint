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
from app.routes.v1 import users, auth, posts
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import AsyncSessionLocal
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from app.events.registry import register_all_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    register_all_handlers()  # Register event handlers before app starts
    if settings.app_env != "test":
        await cache.connect()
    yield

    # Shutdown
    if settings.app_env != "test":
        await cache.disconnect()
    logger.info(f"Shutting down {settings.app_name}")


def create_app() -> FastAPI:

    if settings.enable_sentry and settings.sentry_dsn:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            integrations=[
                FastApiIntegration(
                    transaction_style="endpoint",  # names transactions by route
                ),
                SqlalchemyIntegration(),  # tracks slow queries
            ],
            # Only send errors in production — not dev noise
            environment=settings.app_env,
            # Sample rate — send 100% of errors, 10% of transactions
            # Transactions = performance tracing (costs money at scale)
            traces_sample_rate=0.1 if settings.is_production else 0.0,
            send_default_pii=False,  # don't send passwords, tokens, etc.
        )
        logger.info("Sentry initialised")

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    # ── Middleware ───────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestSizeLimitMiddleware, max_size=1024 * 1024)  # 1MB limit
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)

    # ── Exception Handlers ───────────────────────────────────────
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

    # ── Rate Limiting ────────────────────────────────────────────
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Metrics ───────────────────────────────────────────────────
    if settings.enable_prometheus:
        Instrumentator(
            should_group_status_codes=True,  # groups 2xx, 4xx, 5xx
            should_ignore_untemplated=True,  # ignore /docs, /openapi.json
            excluded_handlers=["/metrics", "/health"],  # don't track these
        ).instrument(app).expose(
            app,
            include_in_schema=False,  # hide from Swagger docs
            tags=["Monitoring"],
        )
        logger.info("Prometheus metrics enabled at /metrics")

    # ── Routers ──────────────────────────────────────────────────
    app.include_router(users.router, prefix="/api/v1")
    app.include_router(auth.router, prefix="/api/v1")
    app.include_router(posts.router, prefix="/api/vi")

    @app.get("/health")
    async def health_check():
        """
        Checks every critical dependency.
        Load balancers and deployment platforms use this to decide
        whether to route traffic to this instance.
        Returns 200 if healthy, 503 if any dependency is down.
        """
        health = {
            "status": "healthy",
            "app": settings.app_name,
            "env": settings.app_env,
            "dependencies": {},
        }
        is_healthy = True

        # Check PostgreSQL
        try:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            health["dependencies"]["postgres"] = "healthy"
        except Exception as e:
            health["dependencies"]["postgres"] = f"unhealthy: {str(e)}"
            is_healthy = False

        # Check Redis
        try:
            await cache._client.ping()
            health["dependencies"]["redis"] = "healthy"
        except Exception as e:
            health["dependencies"]["redis"] = f"unhealthy: {str(e)}"
            is_healthy = False

        if not is_healthy:
            health["status"] = "unhealthy"
            from fastapi.responses import JSONResponse

            return JSONResponse(status_code=503, content=health)

        return health

    return app


app = create_app()
