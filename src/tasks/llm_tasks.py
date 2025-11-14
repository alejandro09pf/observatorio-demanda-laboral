"""
Celery Tasks for LLM Pipeline B
Process jobs using LLM for direct skill extraction (alternative to NER+Regex)
"""
import logging
import psycopg2
import os
from datetime import datetime
from celery import Task
from src.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def process_jobs_llm_task(
    self: Task,
    limit: int,
    model_name: str = "gemma-3-4b-instruct",
    country: str = None
) -> dict:
    """
    Process jobs using LLM Pipeline B (direct extraction).

    This task:
    1. Loads N pending/unprocessed jobs from database
    2. Runs LLM Pipeline B to extract skills directly
    3. Saves results to enhanced_skills table
    4. Generates embeddings automatically

    Args:
        limit: Number of jobs to process
        model_name: LLM model to use (from model_registry)
        country: Optional country filter (e.g., 'CO', 'MX')

    Returns:
        dict: Processing results with statistics
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Initializing Pipeline B with {model_name}...',
                'progress': 0,
                'jobs_total': limit
            }
        )

        logger.info(
            f"🤖 Celery Worker: Starting LLM Pipeline B - "
            f"{limit} jobs, model={model_name}, country={country}"
        )

        # Import Pipeline B
        from src.llm_processor.pipeline import LLMExtractionPipeline

        # Initialize LLM pipeline
        pipeline = LLMExtractionPipeline(model_name=model_name)

        logger.info(f"   ✅ LLM Pipeline initialized: {pipeline.llm.model_name}")

        # Update task state: Loading jobs
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Loading jobs from database...',
                'progress': 5,
                'jobs_total': limit
            }
        )

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Get pending jobs (not yet processed with Pipeline B)
        query = """
            SELECT
                job_id,
                title,
                description,
                requirements,
                country,
                scraped_at
            FROM raw_jobs
            WHERE is_processed = false
        """

        params = []
        if country:
            query += " AND country = %s"
            params.append(country)

        query += " ORDER BY scraped_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()

        if not rows:
            conn.close()
            logger.warning("No pending jobs found for Pipeline B")
            return {
                'status': 'success',
                'message': 'No pending jobs to process',
                'jobs_processed': 0
            }

        logger.info(f"📊 Loaded {len(rows)} jobs for LLM processing")

        # Process jobs one by one
        jobs_processed = 0
        total_skills_extracted = 0

        for i, row in enumerate(rows, 1):
            job_id = str(row[0])
            title = row[1] or ''
            description = row[2] or ''
            requirements = row[3] or ''
            job_country = row[4]

            # Update progress
            progress = int(5 + (i / len(rows)) * 90)
            self.update_state(
                state='PROGRESS',
                meta={
                    'current': f'Processing job {i}/{len(rows)}: {title[:50]}...',
                    'progress': progress,
                    'jobs_processed': i - 1,
                    'jobs_total': len(rows)
                }
            )

            try:
                # Prepare job data for Pipeline B
                job_data = {
                    'job_id': job_id,
                    'title': title,
                    'description': description,
                    'requirements': requirements,
                    'country': job_country
                }

                # Extract skills using LLM Pipeline B
                # This automatically saves to enhanced_skills table
                skills = pipeline.extract_skills_from_job(job_data)

                total_skills_extracted += len(skills)
                jobs_processed += 1

                logger.info(
                    f"   [{i}/{len(rows)}] Job {job_id}: "
                    f"extracted {len(skills)} skills with LLM"
                )

            except Exception as job_error:
                logger.error(f"   ❌ Failed to process job {job_id}: {job_error}")
                # Continue with next job
                continue

        conn.close()

        # Final summary
        logger.info(
            f"✅ Pipeline B completed: "
            f"{jobs_processed}/{len(rows)} jobs processed, "
            f"{total_skills_extracted} total skills extracted"
        )

        return {
            'status': 'success',
            'jobs_processed': jobs_processed,
            'jobs_total': len(rows),
            'skills_extracted': total_skills_extracted,
            'model_used': model_name,
            'country_filter': country,
            'task_id': self.request.id,
            'progress': 100,
            'completed_at': datetime.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"❌ Pipeline B failed: {str(exc)}")

        # Update task state: Failed
        self.update_state(
            state='FAILURE',
            meta={
                'current': f'Pipeline B failed: {str(exc)}',
                'progress': 0,
                'error': str(exc)
            }
        )

        # Retry the task
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


# Example usage:
# from src.tasks.llm_tasks import process_jobs_llm_task
#
# # Process 100 jobs with Gemma
# task = process_jobs_llm_task.delay(limit=100, model_name='gemma-3-4b-instruct')
# result = task.get(timeout=3600)
# print(f"Result: {result}")
