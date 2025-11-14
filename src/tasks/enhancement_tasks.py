"""
Celery Tasks for Skill Enhancement
Worker 3: Enhance extracted skills using LLM and generate embeddings

Compatible with existing schema: processes JOBs, not individual skills
"""
import logging
import psycopg2
import os
import json
import numpy as np
from datetime import datetime
from celery import Task
from sentence_transformers import SentenceTransformer
from src.tasks.celery_app import celery_app
from src.events import publish_event

logger = logging.getLogger(__name__)

# Global embedding model (loaded once per worker)
_embedding_model = None

def get_embedding_model():
    """Get or initialize the embedding model (singleton pattern)."""
    global _embedding_model
    if _embedding_model is None:
        logger.info("Loading E5 embedding model: intfloat/multilingual-e5-base...")
        _embedding_model = SentenceTransformer('intfloat/multilingual-e5-base')
        logger.info("✅ E5 model loaded successfully")
    return _embedding_model


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def enhance_job_task(
    self: Task,
    job_id: str,
) -> dict:
    """
    Enhance all extracted skills for a single job using LLM.

    This task:
    1. Fetches all extracted skills for the job
    2. Calls LLM API to enhance/normalize each skill
    3. Saves enhanced skills to enhanced_skills table
    4. Updates job processing status

    Args:
        job_id: UUID of the job to enhance

    Returns:
        dict: Enhancement results with statistics
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Starting enhancement for job {job_id}...',
                'progress': 0,
                'job_id': job_id
            }
        )

        logger.info(f"🎨 Celery Worker: Starting enhancement task - job {job_id}")

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Update task state: Fetching skills
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Fetching extracted skills...',
                'progress': 10,
                'job_id': job_id
            }
        )

        # Fetch all extracted skills for this job
        cursor.execute("""
            SELECT
                skill_text,
                skill_type,
                extraction_method,
                confidence_score
            FROM extracted_skills
            WHERE job_id = %s
        """, (job_id,))

        skills = cursor.fetchall()

        if not skills:
            cursor.close()
            conn.close()
            logger.warning(f"⚠️ No extracted skills found for job {job_id}")
            return {
                'status': 'success',
                'job_id': job_id,
                'skills_enhanced': 0,
                'message': 'No skills to enhance'
            }

        logger.info(f"📊 Found {len(skills)} skills to enhance for job {job_id}")

        # Update task state: Enhancing
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Enhancing {len(skills)} skills with LLM...',
                'progress': 30,
                'job_id': job_id,
                'skills_count': len(skills)
            }
        )

        # TODO: Call LLM API for enhancement
        # For now, use simple normalization
        enhanced_skills = []
        for skill_text, skill_type, extraction_method, confidence in skills:
            # Simple normalization (replace with actual LLM call)
            normalized = skill_text.strip().title()

            enhanced_skills.append({
                'original_skill_text': skill_text,
                'normalized_skill': normalized,
                'skill_type': skill_type or 'technical',
                'esco_concept_uri': None,  # TODO: Add ESCO matching
                'esco_preferred_label': None,
                'llm_confidence': confidence,
                'llm_reasoning': f'Normalized from extraction method: {extraction_method}',
                'llm_model': 'simple-normalization-v1'
            })

        # Update task state: Saving
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Saving {len(enhanced_skills)} enhanced skills...',
                'progress': 70,
                'job_id': job_id
            }
        )

        # Save enhanced skills to database
        skills_saved = 0
        for skill_data in enhanced_skills:
            cursor.execute("""
                INSERT INTO enhanced_skills
                (job_id, original_skill_text, normalized_skill, skill_type,
                 esco_concept_uri, esco_preferred_label, llm_confidence,
                 llm_reasoning, llm_model)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                job_id,
                skill_data['original_skill_text'],
                skill_data['normalized_skill'],
                skill_data['skill_type'],
                skill_data['esco_concept_uri'],
                skill_data['esco_preferred_label'],
                skill_data['llm_confidence'],
                skill_data['llm_reasoning'],
                skill_data['llm_model']
            ))
            skills_saved += 1

        conn.commit()

        # Generate and save embeddings for enhanced skills
        if skills_saved > 0:
            logger.info(f"   Generating E5 embeddings for {skills_saved} skills...")

            # Get embedding model
            model = get_embedding_model()

            # Collect skill texts for batch embedding
            skill_texts = [skill['normalized_skill'] for skill in enhanced_skills]

            # Generate embeddings in batch (more efficient)
            embeddings = model.encode(
                skill_texts,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True  # L2 normalization for cosine similarity
            )

            logger.info(f"   ✅ Generated {len(embeddings)} embeddings (shape: {embeddings.shape})")

            # Save embeddings to skill_embeddings table
            # First, get the enhancement_ids we just created
            cursor.execute("""
                SELECT enhancement_id, normalized_skill
                FROM enhanced_skills
                WHERE job_id = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (job_id, skills_saved))

            enhancement_rows = cursor.fetchall()
            embeddings_saved = 0

            for (enhancement_id, skill_text), embedding_vector in zip(enhancement_rows, embeddings):
                # Save to skill_embeddings table
                cursor.execute("""
                    INSERT INTO skill_embeddings
                    (enhancement_id, embedding_vector, model_name, model_version)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (enhancement_id) DO UPDATE
                    SET embedding_vector = EXCLUDED.embedding_vector,
                        model_name = EXCLUDED.model_name,
                        model_version = EXCLUDED.model_version
                """, (
                    enhancement_id,
                    embedding_vector.tolist(),
                    'intfloat/multilingual-e5-base',
                    'v1.0'
                ))
                embeddings_saved += 1

            conn.commit()
            logger.info(f"   ✅ Saved {embeddings_saved} embeddings to database")

        # Update job processing status
        cursor.execute("""
            UPDATE raw_jobs
            SET is_processed = true
            WHERE job_id = %s
        """, (job_id,))
        conn.commit()

        cursor.close()
        conn.close()

        logger.info(
            f"✅ Celery Worker: Enhancement completed - "
            f"{skills_saved} skills enhanced + embeddings generated for job {job_id}"
        )

        # Emit event to Redis Pub/Sub
        if skills_saved > 0:
            try:
                publish_event('skills_enhanced', {
                    'job_id': job_id,
                    'skills_enhanced': skills_saved,
                    'task_id': self.request.id
                })
                logger.info(f"📢 Event published: skills_enhanced for job {job_id}")
            except Exception as exc:
                logger.error(f"Failed to publish skills_enhanced event: {exc}")

        return {
            'status': 'success',
            'job_id': job_id,
            'skills_enhanced': skills_saved,
            'task_id': self.request.id,
            'progress': 100,
            'completed_at': datetime.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"❌ Celery Worker: Enhancement failed - job {job_id}: {str(exc)}")

        # Update task state: Failed
        self.update_state(
            state='FAILURE',
            meta={
                'current': f'Enhancement failed: {str(exc)}',
                'progress': 0,
                'job_id': job_id,
                'error': str(exc)
            }
        )

        # Retry the task
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(bind=True)
def process_pending_enhancements(
    self: Task,
    limit: int = 100,
    country: str = None
) -> dict:
    """
    Process all jobs pending enhancement.

    This task queries the database for jobs with extracted skills
    but no enhanced skills, and enqueues enhancement tasks for them.

    Args:
        limit: Maximum number of jobs to process
        country: Optional country filter (e.g., 'CO', 'MX')

    Returns:
        dict: Summary of enqueued tasks
    """
    try:
        logger.info(f"🔍 Searching for jobs pending enhancement (limit={limit})")

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Querying database for jobs needing enhancement...',
                'progress': 10
            }
        )

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Find jobs that have extracted skills but no enhanced skills
        query = """
            SELECT DISTINCT rj.job_id
            FROM raw_jobs rj
            INNER JOIN extracted_skills es ON rj.job_id = es.job_id
            LEFT JOIN enhanced_skills enh ON rj.job_id = enh.job_id
            WHERE enh.enhancement_id IS NULL
              AND rj.is_processed = false
        """
        params = []

        if country:
            query += " AND rj.country = %s"
            params.append(country)

        query += " ORDER BY rj.scraped_at DESC LIMIT %s"
        params.append(limit)

        cursor.execute(query, params)
        job_ids = [str(row[0]) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

        logger.info(f"📊 Found {len(job_ids)} jobs pending enhancement")

        if not job_ids:
            return {
                'status': 'success',
                'message': 'No jobs pending enhancement',
                'jobs_enqueued': 0
            }

        # Update task state
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Enqueueing {len(job_ids)} enhancement tasks...',
                'progress': 50
            }
        )

        # Enqueue enhancement tasks
        task_ids = []
        for job_id in job_ids:
            task = enhance_job_task.delay(job_id)
            task_ids.append(task.id)

        logger.info(f"📮 Enqueued {len(task_ids)} enhancement tasks")

        return {
            'status': 'success',
            'message': f'{len(task_ids)} enhancement tasks enqueued',
            'jobs_enqueued': len(task_ids),
            'task_ids': task_ids,
            'country_filter': country
        }

    except Exception as exc:
        logger.error(f"❌ Failed to process pending enhancements: {str(exc)}")
        raise exc


# Example usage:
# from src.tasks.enhancement_tasks import enhance_job_task, process_pending_enhancements
#
# # Enhance a single job
# task = enhance_job_task.delay('job-uuid-here')
# print(f"Task ID: {task.id}")
#
# # Process all pending enhancements
# task = process_pending_enhancements.delay(limit=50, country='CO')
# result = task.get(timeout=3600)
# print(f"Result: {result}")
