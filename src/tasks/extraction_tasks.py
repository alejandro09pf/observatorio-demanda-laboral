"""
Celery Tasks for Skill Extraction
Worker 2: Extract skills from job postings using Pipeline A (NER + Regex + ESCO)
"""
import logging
import psycopg2
import os
from datetime import datetime
from celery import Task, group
from src.tasks.celery_app import celery_app
from src.events import publish_event

# Import Pipeline A (complete extraction with ESCO mapping)
from src.extractor.pipeline import ExtractionPipeline

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_skills_task(
    self: Task,
    job_id: str,
) -> dict:
    """
    Extract skills from a single job posting using Pipeline A (NER + Regex + ESCO).

    This task:
    1. Fetches job data from cleaned_jobs (or fallback to raw_jobs)
    2. Runs Pipeline A: NER + Regex + ESCO mapping
    3. Saves extracted skills to database with ESCO URIs
    4. Updates extraction status

    Args:
        job_id: UUID of the job to process

    Returns:
        dict: Extraction results with statistics

    Raises:
        Exception: If extraction fails after retries
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Starting Pipeline A extraction for job {job_id}...',
                'progress': 0,
                'job_id': job_id
            }
        )

        logger.info(f"🔍 Celery Worker: Starting Pipeline A extraction - job {job_id}")

        # Initialize Pipeline A
        pipeline = ExtractionPipeline()

        # Update task state: Fetching job
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Fetching job data from database...',
                'progress': 10,
                'job_id': job_id
            }
        )

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Get job data (prefer cleaned_jobs, fallback to raw_jobs)
        cursor.execute("""
            SELECT
                rj.job_id,
                rj.title,
                rj.description,
                rj.requirements,
                rj.portal,
                rj.country,
                cj.combined_text
            FROM raw_jobs rj
            LEFT JOIN cleaned_jobs cj ON rj.job_id = cj.job_id
            WHERE rj.job_id = %s
        """, (job_id,))

        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            raise ValueError(f"Job {job_id} not found in database")

        title = row[1] or ''
        description = row[2] or ''
        requirements = row[3] or ''
        portal = row[4]
        country = row[5]
        combined_text = row[6]

        cursor.close()

        # Prepare job data for Pipeline A
        job_data = {
            'job_id': job_id,
            'title': title,
            'description': description,
            'requirements': requirements,
            'portal': portal,
            'country': country,
            'combined_text': combined_text
        }

        # Update task state: Running Pipeline A
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Running Pipeline A (NER + Regex + ESCO)...',
                'progress': 30,
                'job_id': job_id
            }
        )

        # Run Pipeline A extraction (NER + Regex + ESCO mapping)
        extraction_results = pipeline.extract_skills_from_job(job_data)

        logger.info(f"   Pipeline A extracted {len(extraction_results)} skills")

        # Update task state: Saving results
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Saving {len(extraction_results)} skills to database...',
                'progress': 70,
                'job_id': job_id,
                'skills_found': len(extraction_results)
            }
        )

        # Save results to database
        cursor = conn.cursor()
        skills_saved = 0

        for result in extraction_results:
            # Extract ESCO URI if match exists
            esco_uri = result.esco_match.esco_uri if result.esco_match else None

            cursor.execute("""
                INSERT INTO extracted_skills
                (job_id, skill_text, extraction_method, skill_type, confidence_score, esco_uri)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (job_id, skill_text) DO UPDATE SET
                    esco_uri = EXCLUDED.esco_uri
            """, (
                job_id,
                result.skill_text,
                result.extraction_method,
                result.skill_type,
                result.final_confidence,
                esco_uri
            ))
            if cursor.rowcount > 0:
                skills_saved += 1

        conn.commit()
        cursor.close()

        # Update extraction status in raw_jobs
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE raw_jobs
            SET extraction_status = 'completed',
                extraction_completed_at = %s,
                extraction_attempts = extraction_attempts + 1
            WHERE job_id = %s
        """, (datetime.now(), job_id))
        conn.commit()
        cursor.close()
        conn.close()

        logger.info(
            f"✅ Celery Worker: Extraction completed - "
            f"{skills_saved} skills extracted from job {job_id}"
        )

        # Emit event to Redis Pub/Sub for auto-triggering enhancement
        if skills_saved > 0:
            try:
                publish_event('skills_extracted', {
                    'job_id': job_id,
                    'skills_count': skills_saved,
                    'task_id': self.request.id
                })
                logger.info(f"📢 Event published: skills_extracted for job {job_id}")
            except Exception as exc:
                logger.error(f"Failed to publish skills_extracted event: {exc}")

        # Return results
        return {
            'status': 'success',
            'job_id': job_id,
            'skills_extracted': skills_saved,
            'task_id': self.request.id,
            'progress': 100,
            'completed_at': datetime.now().isoformat()
        }

    except Exception as exc:
        # Log the error
        logger.error(f"❌ Celery Worker: Extraction failed - job {job_id}: {str(exc)}")

        # Update extraction status to failed
        try:
            conn = psycopg2.connect(os.getenv('DATABASE_URL'))
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE raw_jobs
                SET extraction_status = 'failed',
                    extraction_error = %s,
                    extraction_attempts = extraction_attempts + 1
                WHERE job_id = %s
            """, (str(exc), job_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as db_error:
            logger.error(f"Failed to update extraction status: {db_error}")

        # Update task state: Failed
        self.update_state(
            state='FAILURE',
            meta={
                'current': f'Extraction failed: {str(exc)}',
                'progress': 0,
                'job_id': job_id,
                'error': str(exc)
            }
        )

        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task
def extract_skills_batch(job_ids: list[str], batch_size: int = 10) -> dict:
    """
    Extract skills from multiple jobs in parallel using Celery group.

    This demonstrates distributed batch processing pattern.

    Args:
        job_ids: List of job UUIDs to process
        batch_size: Number of jobs to process concurrently

    Returns:
        dict: Aggregated results from all extractions
    """
    logger.info(f"📦 Starting batch extraction for {len(job_ids)} jobs")

    # Create a group of parallel extraction tasks
    job = group(
        extract_skills_task.s(job_id)
        for job_id in job_ids
    )

    # Execute tasks in parallel
    result = job.apply_async()

    # Wait for all tasks to complete
    results = result.get(timeout=3600)  # 1 hour timeout

    # Aggregate results
    total_skills = sum(r.get('skills_extracted', 0) for r in results if r)
    successful = sum(1 for r in results if r and r.get('status') == 'success')

    logger.info(
        f"✅ Batch extraction completed: "
        f"{successful}/{len(job_ids)} jobs, {total_skills} total skills"
    )

    return {
        'status': 'success',
        'total_jobs': len(job_ids),
        'successful': successful,
        'failed': len(job_ids) - successful,
        'total_skills_extracted': total_skills,
        'results': results
    }


@celery_app.task(bind=True)
def process_pending_extractions(
    self: Task,
    limit: int = 100,
    country: str = None
) -> dict:
    """
    Process all jobs pending extraction.

    This task queries the database for jobs with extraction_status='pending'
    and enqueues extraction tasks for them.

    Args:
        limit: Maximum number of jobs to process
        country: Optional country filter (e.g., 'CO', 'MX')

    Returns:
        dict: Summary of enqueued tasks
    """
    try:
        logger.info(f"🔍 Searching for pending extraction jobs (limit={limit})")

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Querying database for pending jobs...',
                'progress': 10
            }
        )

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        query = """
            SELECT job_id
            FROM raw_jobs
            WHERE extraction_status = 'pending'
              AND is_processed = false
        """
        params = []

        if country:
            query += " AND country = %s"
            params.append(country)

        query += " ORDER BY scraped_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        job_ids = [str(row[0]) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        logger.info(f"📊 Found {len(job_ids)} pending extraction jobs")

        if not job_ids:
            return {
                'status': 'success',
                'message': 'No pending extraction jobs found',
                'jobs_enqueued': 0
            }

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Enqueueing {len(job_ids)} extraction tasks...',
                'progress': 50
            }
        )

        # Enqueue extraction tasks
        task_ids = []
        for job_id in job_ids:
            task = extract_skills_task.delay(job_id)
            task_ids.append(task.id)

        logger.info(f"📮 Enqueued {len(task_ids)} extraction tasks")

        return {
            'status': 'success',
            'message': f'{len(task_ids)} extraction tasks enqueued',
            'jobs_enqueued': len(task_ids),
            'task_ids': task_ids,
            'country_filter': country
        }

    except Exception as exc:
        logger.error(f"❌ Failed to process pending extractions: {str(exc)}")
        raise exc


# Example usage:
# from src.tasks.extraction_tasks import extract_skills_task, process_pending_extractions
#
# # Extract skills from a single job
# task = extract_skills_task.delay('job-uuid-here')
# print(f"Task ID: {task.id}")
#
# # Process all pending extractions
# task = process_pending_extractions.delay(limit=50, country='CO')
# result = task.get(timeout=3600)
# print(f"Result: {result}")
