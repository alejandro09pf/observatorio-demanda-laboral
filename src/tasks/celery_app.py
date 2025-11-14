"""
Celery Application Configuration
Event-Driven Task Queue for Labor Observatory
"""
import os
import logging
from celery import Celery
from celery.schedules import crontab
from celery.signals import worker_ready

logger = logging.getLogger(__name__)

# Get Redis URL from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# Create Celery app
celery_app = Celery(
    "labor_observatory",
    broker=f"{REDIS_URL}/0",  # Redis DB 0 for message broker
    backend=f"{REDIS_URL}/1",  # Redis DB 1 for result backend
    include=[
        "src.tasks.scraping_tasks",
        "src.tasks.extraction_tasks",
        "src.tasks.enhancement_tasks",
        "src.tasks.clustering_tasks",
        "src.tasks.llm_tasks",
    ]
)

# Celery Configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Timezone
    timezone="America/Bogota",
    enable_utc=True,

    # Task execution
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit

    # Worker configuration
    worker_prefetch_multiplier=1,  # Take one task at a time
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)

    # Result backend
    result_expires=86400,  # Results expire after 24 hours
    result_backend_transport_options={
        'master_name': 'mymaster'
    },

    # Task routes (optional - para separar queues)
    # TODO: Uncomment when using specialized queues
    # task_routes={
    #     'src.tasks.scraping_tasks.*': {'queue': 'scraping'},
    #     'src.tasks.extraction_tasks.*': {'queue': 'extraction'},
    #     'src.tasks.clustering_tasks.*': {'queue': 'clustering'},
    # },

    # Retry policy
    task_acks_late=True,  # Acknowledge task after completion, not before
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
)

# Celery Beat Schedule (Cron jobs)
# Automated scheduled tasks
celery_app.conf.beat_schedule = {
    # Daily scraping at 2 AM (Colombia time)
    'scraping-daily-co': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=0),
        'args': ('computrabajo', 'CO', 100, 5)
    },
    # Daily scraping at 2:15 AM (Mexico)
    'scraping-daily-mx': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=15),
        'args': ('linkedin', 'MX', 100, 5)
    },
    # Process pending extractions every 30 minutes
    'process-pending-extractions': {
        'task': 'src.tasks.extraction_tasks.process_pending_extractions',
        'schedule': crontab(minute='*/30'),
        'args': (50,)  # Process 50 jobs per batch
    },
    # Process pending enhancements every hour
    'process-pending-enhancements': {
        'task': 'src.tasks.enhancement_tasks.process_pending_enhancements',
        'schedule': crontab(minute=0),  # Every hour
        'args': (100,)  # Process 100 jobs per batch
    },
    # Weekly clustering on Sunday at 3 AM
    'weekly-clustering': {
        'task': 'src.tasks.clustering_tasks.run_clustering_task',
        'schedule': crontab(day_of_week=0, hour=3),
        'args': ('pipeline_b_300_post', 50, None)  # 50 clusters, all countries
    },
}


# Event Listeners Setup
@worker_ready.connect
def on_worker_ready(sender=None, conf=None, **kwargs):
    """
    Start event listeners when Celery worker is ready.
    This enables auto-triggering of tasks based on Redis Pub/Sub events.
    """
    logger.info("🎧 Celery worker ready, starting event listeners...")

    try:
        from src.events.handlers import start_event_listeners
        start_event_listeners()
        logger.info("✅ Event listeners started successfully")
    except Exception as exc:
        logger.error(f"❌ Failed to start event listeners: {exc}")


if __name__ == '__main__':
    celery_app.start()
