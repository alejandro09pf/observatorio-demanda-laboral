"""
Event Handlers for Auto-Triggering Celery Tasks
Listens to Redis Pub/Sub events and enqueues appropriate tasks
"""
import logging
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)


def handle_jobs_scraped(event_data: Dict[str, Any]) -> None:
    """
    Handle 'jobs_scraped' event.
    Auto-triggers extraction tasks for newly scraped jobs.

    Event data format:
        {
            "event": "jobs_scraped",
            "timestamp": "2025-11-13T...",
            "data": {
                "job_ids": ["uuid1", "uuid2", ...],
                "count": 87,
                "country": "CO",
                "spider": "computrabajo"
            }
        }
    """
    try:
        data = event_data.get("data", {})
        job_ids = data.get("job_ids", [])
        count = data.get("count", len(job_ids))
        country = data.get("country", "unknown")

        logger.info(f"🎯 Event: jobs_scraped → {count} jobs from {country}")

        if not job_ids:
            logger.warning("No job_ids in event, skipping extraction")
            return

        # Import here to avoid circular dependency
        from src.tasks.extraction_tasks import extract_skills_task

        # Enqueue extraction task for each job
        task_ids = []
        for job_id in job_ids:
            task = extract_skills_task.delay(job_id)
            task_ids.append(task.id)

        logger.info(f"✅ Auto-triggered {len(task_ids)} extraction tasks")

    except Exception as exc:
        logger.error(f"❌ Error handling jobs_scraped event: {exc}")


def handle_skills_extracted(event_data: Dict[str, Any]) -> None:
    """
    Handle 'skills_extracted' event.
    Auto-triggers enhancement tasks for newly extracted skills.

    Event data format:
        {
            "event": "skills_extracted",
            "timestamp": "2025-11-13T...",
            "data": {
                "job_id": "uuid",
                "skills_count": 32
            }
        }
    """
    try:
        data = event_data.get("data", {})
        job_id = data.get("job_id")
        skills_count = data.get("skills_count", 0)

        logger.info(f"🎯 Event: skills_extracted → {skills_count} skills from job {job_id}")

        if not job_id:
            logger.warning("No job_id in event, skipping enhancement")
            return

        # Import here to avoid circular dependency
        from src.tasks.enhancement_tasks import enhance_job_task

        # Enqueue enhancement task for the job
        task = enhance_job_task.delay(job_id)

        logger.info(f"✅ Auto-triggered enhancement task {task.id} for job {job_id}")

    except Exception as exc:
        logger.error(f"❌ Error handling skills_extracted event: {exc}")


def handle_skills_enhanced(event_data: Dict[str, Any]) -> None:
    """
    Handle 'skills_enhanced' event.
    Optional: Could trigger clustering or other downstream tasks.

    Event data format:
        {
            "event": "skills_enhanced",
            "timestamp": "2025-11-13T...",
            "data": {
                "job_id": "uuid",
                "skills_enhanced": 32
            }
        }
    """
    try:
        data = event_data.get("data", {})
        job_id = data.get("job_id")
        skills_count = data.get("skills_enhanced", 0)

        logger.info(f"🎯 Event: skills_enhanced → {skills_count} skills from job {job_id}")

        # For now, just log - clustering is usually done in batches, not per job
        logger.info("📊 Skills enhanced successfully (no auto-trigger for clustering)")

    except Exception as exc:
        logger.error(f"❌ Error handling skills_enhanced event: {exc}")


def handle_clustering_completed(event_data: Dict[str, Any]) -> None:
    """
    Handle 'clustering_completed' event.
    Optional: Could trigger notifications, dashboard updates, etc.

    Event data format:
        {
            "event": "clustering_completed",
            "timestamp": "2025-11-13T...",
            "data": {
                "analysis_id": "uuid",
                "n_clusters": 50,
                "skills_analyzed": 3542
            }
        }
    """
    try:
        data = event_data.get("data", {})
        analysis_id = data.get("analysis_id")
        n_clusters = data.get("n_clusters", 0)
        skills_count = data.get("skills_analyzed", 0)

        logger.info(
            f"🎯 Event: clustering_completed → {n_clusters} clusters "
            f"from {skills_count} skills (analysis {analysis_id})"
        )

        # For now, just log - could trigger email notification, etc.
        logger.info("📊 Clustering completed successfully")

    except Exception as exc:
        logger.error(f"❌ Error handling clustering_completed event: {exc}")


def start_event_listeners() -> None:
    """
    Start all event listeners in background threads.
    Call this function once when the Celery worker starts.

    This enables auto-triggering of tasks based on events.
    """
    from .event_bus import subscribe_to_event

    # Define event → handler mapping
    event_handlers = {
        "jobs_scraped": handle_jobs_scraped,
        "skills_extracted": handle_skills_extracted,
        "skills_enhanced": handle_skills_enhanced,
        "clustering_completed": handle_clustering_completed,
    }

    # Start a listener thread for each event
    for event_name, handler in event_handlers.items():
        thread = threading.Thread(
            target=subscribe_to_event,
            args=(event_name, handler),
            daemon=True,
            name=f"EventListener-{event_name}"
        )
        thread.start()
        logger.info(f"🎧 Started listener thread for: {event_name}")

    logger.info("✅ All event listeners started")


# Example usage in Celery worker:
# In src/tasks/celery_app.py or worker startup:
#
# from src.events.handlers import start_event_listeners
#
# @worker_ready.connect
# def on_worker_ready(sender=None, conf=None, **kwargs):
#     logger.info("Worker ready, starting event listeners...")
#     start_event_listeners()
