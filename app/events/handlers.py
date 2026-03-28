# app/events/handlers.py
from app.events.definitions import (
    UserRegistered,
    UserDeactivated,
    UserLoggedIn,
    PasswordChanged,
)
from app.core.logging import logger
from app.core.cache import cache
from app.core.cache_keys import UserCacheKeys
from app.core.config import settings


async def on_user_registered_send_email(event: UserRegistered) -> None:
    """Send welcome email via Celery background task."""
    if event.via_google:
        # Could send a different "welcome, you signed in with Google" email
        logger.info(
            f"Google signup — skipping standard welcome email for {event.email}"
        )
        return

    if not settings.enable_email:
        logger.info(
            f"Email disabled — skipping welcome email for {event.email}"
        )
        return

    from app.worker.tasks.email import send_welcome_email

    send_welcome_email.delay(
        user_email=event.email,
        user_name=event.name,
    )
    logger.info(f"Welcome email queued for {event.email}")


async def on_user_registered_track_metrics(event: UserRegistered) -> None:
    """Increment Prometheus registration counter."""
    try:
        from app.core.metrics import user_registrations_total

        user_registrations_total.inc()
    except Exception:
        pass  # metrics are optional — never break registration over this


async def on_user_registered_invalidate_cache(event: UserRegistered) -> None:
    """Invalidate user list cache — new user means lists are stale."""
    await cache.delete_pattern(UserCacheKeys.all_pattern())
    logger.info("User list cache invalidated after registration")


async def on_user_deactivated_invalidate_cache(event: UserDeactivated) -> None:
    """Clear this user's cache entries on deactivation."""
    await cache.delete(UserCacheKeys.single(event.user_id))
    await cache.delete(UserCacheKeys.by_email(event.email))
    await cache.delete_pattern(UserCacheKeys.all_pattern())


async def on_user_logged_in_track(event: UserLoggedIn) -> None:
    """Track login metrics."""
    try:
        from app.core.metrics import login_attempts_total

        login_attempts_total.labels(status="success").inc()
    except Exception:
        pass


async def on_password_changed_notify(event: PasswordChanged) -> None:
    """
    Send a security notification email.
    """
    logger.info(f"Password changed for user_id={event.user_id}")
