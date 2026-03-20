# app/events/registry.py
from app.events.bus import event_bus
from app.events.definitions import (
    UserRegistered,
    UserDeactivated,
    UserLoggedIn,
    PasswordChanged,
)
from app.events.handlers import (
    on_user_registered_send_email,
    on_user_registered_track_metrics,
    on_user_registered_invalidate_cache,
    on_user_deactivated_invalidate_cache,
    on_user_logged_in_track,
    on_password_changed_notify,
)


def register_all_handlers() -> None:
    """
    Called once at app startup.
    Maps every event type to its handlers.
    Adding a new reaction to an event = add one line here.
    """
    # UserRegistered → three independent reactions
    event_bus.subscribe(UserRegistered, on_user_registered_send_email)
    event_bus.subscribe(UserRegistered, on_user_registered_track_metrics)
    event_bus.subscribe(UserRegistered, on_user_registered_invalidate_cache)

    # UserDeactivated → cache cleanup
    event_bus.subscribe(UserDeactivated, on_user_deactivated_invalidate_cache)

    # UserLoggedIn → metrics
    event_bus.subscribe(UserLoggedIn, on_user_logged_in_track)

    # PasswordChanged → security notification
    event_bus.subscribe(PasswordChanged, on_password_changed_notify)
