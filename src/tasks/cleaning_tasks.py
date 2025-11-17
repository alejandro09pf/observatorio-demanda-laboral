"""
Celery Tasks for Data Cleaning
Worker: Clean raw jobs and store in cleaned_jobs table
"""
import logging
import subprocess
import os
from pathlib import Path
from celery import Task
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def clean_jobs_task(
    self: Task,
    batch_size: int = 1000,
    portal: str = None,
    country: str = None
) -> dict:
    """
    Clean raw jobs and store in cleaned_jobs table.

    Calls the clean_raw_jobs.py script to:
    1. Fetch unprocessed raw_jobs
    2. Clean and normalize text fields
    3. Save to cleaned_jobs table

    Args:
        batch_size: Number of jobs to process per batch
        portal: Optional portal filter
        country: Optional country filter

    Returns:
        dict: Cleaning results with statistics
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Starting data cleaning...',
                'progress': 0
            }
        )

        logger.info(f"🧹 Celery Worker: Starting cleaning task (batch_size={batch_size})")

        # Build command to call cleaning script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "clean_raw_jobs.py"

        cmd = ["python", str(script_path), "--batch-size", str(batch_size)]

        if portal:
            cmd.extend(["--portal", portal])
        if country:
            cmd.extend(["--country", country])

        # Update task state: Running
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Running cleaning script...',
                'progress': 50
            }
        )

        # Run cleaning script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour max
            env=os.environ.copy()
        )

        if result.returncode != 0:
            logger.error(f"❌ Cleaning script failed: {result.stderr}")
            raise Exception(f"Cleaning script failed: {result.stderr}")

        logger.info(f"✅ Cleaning completed successfully")
        logger.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars

        return {
            'status': 'success',
            'batch_size': batch_size,
            'portal': portal,
            'country': country,
            'task_id': self.request.id,
            'output': result.stdout[-200:]  # Return summary
        }

    except subprocess.TimeoutExpired:
        logger.error("❌ Cleaning timeout (>1 hour)")
        raise self.retry(countdown=600)  # Retry after 10 minutes

    except Exception as exc:
        logger.error(f"❌ Cleaning error: {exc}")
        raise self.retry(exc=exc, countdown=300)  # Retry after 5 minutes
