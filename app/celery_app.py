from celery import Celery
from app.config import settings

celery_app = Celery(
    "payment_processor",
    broker=settings.redis_url,
    backend=settings.redis_url
)

# celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,  # acknowledge task after it completes
    worker_prefetch_multiplier=1,  # fetch one task at a time
)
