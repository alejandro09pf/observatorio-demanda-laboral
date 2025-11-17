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
        "src.tasks.cleaning_tasks",
        "src.tasks.extraction_tasks",
        "src.tasks.embeddings_tasks",
        "src.tasks.clustering_tasks",
        "src.tasks.backup_tasks",
        "src.tasks.llm_tasks",  # Optional - for manual Pipeline B processing
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
    # ===== SCRAPING SCHEDULES =====
    # Daily scraping distributed across 7 portals and 3 countries (2:00-4:00 AM)

    # 2:00 AM - Computrabajo CO
    'scraping-computrabajo-co': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=0),
        'args': ('computrabajo', 'CO', 100, 5)
    },
    # 2:15 AM - Bumeran MX
    'scraping-bumeran-mx': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=15),
        'args': ('bumeran', 'MX', 100, 5)
    },
    # 2:30 AM - Elempleo CO
    'scraping-elempleo-co': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=30),
        'args': ('elempleo', 'CO', 100, 5)
    },
    # 2:45 AM - Hiring Cafe AR
    'scraping-hiring-cafe-ar': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=2, minute=45),
        'args': ('hiring_cafe', 'AR', 100, 5)
    },
    # 3:00 AM - Magneto CO
    'scraping-magneto-co': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=3, minute=0),
        'args': ('magneto', 'CO', 100, 5)
    },
    # 3:15 AM - Occmundial MX
    'scraping-occmundial-mx': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=3, minute=15),
        'args': ('occmundial', 'MX', 100, 5)
    },
    # 3:30 AM - Zonajobs AR
    'scraping-zonajobs-ar': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour=3, minute=30),
        'args': ('zonajobs', 'AR', 100, 5)
    },

    # ===== DATA PROCESSING PIPELINE =====
    # Sequential pipeline: Cleaning → Extraction → Embeddings

    # 4:30 AM - Clean scraped jobs (raw_jobs → cleaned_jobs)
    'daily-cleaning': {
        'task': 'src.tasks.cleaning_tasks.clean_jobs_task',
        'schedule': crontab(hour=4, minute=30),
        'args': (1000,)  # Batch size
    },

    # 5:30 AM - Extract skills with Pipeline A (NER + Regex + ESCO)
    'daily-extraction-pipeline-a': {
        'task': 'src.tasks.extraction_tasks.process_pending_extractions',
        'schedule': crontab(hour=5, minute=30),
        'args': (500,)  # Process up to 500 pending jobs
    },

    # 7:00 AM - Generate embeddings for new extracted skills
    'daily-embeddings-generation': {
        'task': 'src.tasks.embeddings_tasks.generate_embeddings_task',
        'schedule': crontab(hour=7, minute=0),
        'args': (256,)  # Batch size for E5 model
    },

    # ===== CLUSTERING SCHEDULES =====
    # Weekly clustering on Sunday at 2:00 AM (2 configurations: PRE and POST ESCO)

    # Sunday 2:00 AM - Pipeline A 30k PRE-ESCO (all extracted skills)
    'weekly-clustering-pipeline-a-pre-esco': {
        'task': 'src.tasks.clustering_tasks.run_clustering_task',
        'schedule': crontab(day_of_week=0, hour=2, minute=0),
        'args': ('pipeline_a_30k_pre', 50, None)
    },

    # Sunday 2:30 AM - Pipeline A 30k POST-ESCO (only skills with ESCO mapping)
    'weekly-clustering-pipeline-a-post-esco': {
        'task': 'src.tasks.clustering_tasks.run_clustering_task',
        'schedule': crontab(day_of_week=0, hour=2, minute=30),
        'args': ('pipeline_a_30k_post', 50, None)
    },

    # ===== MAINTENANCE SCHEDULES =====
    # Daily database backup at 1:00 AM (before scraping starts)
    'daily-database-backup': {
        'task': 'src.tasks.backup_tasks.backup_database_task',
        'schedule': crontab(hour=1, minute=0),
        'args': ()
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
