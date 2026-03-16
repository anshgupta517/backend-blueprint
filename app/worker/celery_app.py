# app/worker/celery_app.py
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "my_backend",
    broker=settings.redis_url,      # Redis as message queue
    backend=settings.redis_url,     # Redis as result store
    include=[
        "app.worker.tasks.email",   # Register task modules here
    ],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Retry behaviour — if broker is temporarily unreachable
    broker_connection_retry_on_startup=True,

    # Task result expiry — clean up results after 1 hour
    result_expires=3600,

    # Routing — all tasks go to the default queue for now
    task_default_queue="default",

    # Prevent tasks from running too long
    task_soft_time_limit=300,   # 5 min — raises SoftTimeLimitExceeded
    task_time_limit=360,        # 6 min — hard kill
)