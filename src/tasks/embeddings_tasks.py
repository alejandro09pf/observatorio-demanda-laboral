"""
Celery Tasks for Embeddings Generation
Worker: Generate E5 embeddings for extracted skills
"""
import logging
import subprocess
import os
from pathlib import Path
from celery import Task
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=300)
def generate_embeddings_task(
    self: Task,
    batch_size: int = 256
) -> dict:
    """
    Generate E5 embeddings for extracted skills.

    Calls the generate_all_extracted_skills_embeddings.py script to:
    1. Find skills in extracted_skills without embeddings
    2. Generate embeddings using E5 model (768D)
    3. Save to skill_embeddings table

    Args:
        batch_size: Batch size for embedding generation

    Returns:
        dict: Generation results with statistics
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Starting embeddings generation...',
                'progress': 0
            }
        )

        logger.info(f"🔮 Celery Worker: Starting embeddings generation (batch_size={batch_size})")

        # Build command to call embeddings script
        script_path = Path(__file__).parent.parent.parent / "scripts" / "generate_all_extracted_skills_embeddings.py"

        cmd = ["python", str(script_path), "--batch-size", str(batch_size)]

        # Update task state: Running
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Generating E5 embeddings (intfloat/multilingual-e5-base)...',
                'progress': 50
            }
        )

        # Run embeddings generation script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=7200,  # 2 hours max (puede ser lento con muchos skills)
            env=os.environ.copy()
        )

        if result.returncode != 0:
            logger.error(f"❌ Embeddings generation failed: {result.stderr}")
            raise Exception(f"Embeddings generation failed: {result.stderr}")

        logger.info(f"✅ Embeddings generation completed successfully")
        logger.info(f"Output: {result.stdout[-500:]}")  # Last 500 chars

        return {
            'status': 'success',
            'batch_size': batch_size,
            'model': 'intfloat/multilingual-e5-base',
            'dimensions': 768,
            'task_id': self.request.id,
            'output': result.stdout[-200:]  # Return summary
        }

    except subprocess.TimeoutExpired:
        logger.error("❌ Embeddings generation timeout (>2 hours)")
        raise self.retry(countdown=1800)  # Retry after 30 minutes

    except Exception as exc:
        logger.error(f"❌ Embeddings generation error: {exc}")
        raise self.retry(exc=exc, countdown=600)  # Retry after 10 minutes
