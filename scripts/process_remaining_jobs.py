#!/usr/bin/env python3
"""
Process remaining 4,008 jobs that were skipped due to timestamp indeterminism.
Uses parallel workers with job_id ordering to ensure deterministic assignment.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from extractor.pipeline import ExtractionPipeline
import psycopg2
from config.settings import get_settings
import logging
import time
import statistics

# Setup logging - simpler approach without worker_id in format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

def main():
    if len(sys.argv) < 3:
        print("Usage: python process_remaining_jobs.py <worker_id> <total_workers>")
        sys.exit(1)

    worker_id = int(sys.argv[1])
    total_workers = int(sys.argv[2])

    # Create logger
    logger = logging.getLogger(__name__)

    logger.info(f"Worker {worker_id + 1}/{total_workers}: Starting for remaining jobs")

    settings = get_settings()
    db_url = settings.database_url.replace('postgresql://', 'postgres://')

    # Get pending jobs ordered by job_id (deterministic)
    with psycopg2.connect(db_url) as conn:
        cursor = conn.cursor()

        # Count total pending
        cursor.execute("""
            SELECT COUNT(*)
            FROM raw_jobs
            WHERE is_usable = TRUE
              AND (is_gold_standard = FALSE OR is_gold_standard IS NULL)
              AND extraction_status = 'pending'
        """)
        total_pending = cursor.fetchone()[0]

        if total_pending == 0:
            logger.info("No pending jobs found")
            return

        logger.info(f"Total pending jobs: {total_pending}")

        # Calculate range for this worker
        jobs_per_worker = total_pending // total_workers
        remainder = total_pending % total_workers

        if worker_id < remainder:
            start_offset = worker_id * (jobs_per_worker + 1)
            worker_limit = jobs_per_worker + 1
        else:
            start_offset = (remainder * (jobs_per_worker + 1)) + \
                         ((worker_id - remainder) * jobs_per_worker)
            worker_limit = jobs_per_worker

        logger.info(f"Worker {worker_id + 1} assigned: {worker_limit} jobs (offset {start_offset})")

        # Fetch this worker's jobs using OFFSET and LIMIT with job_id ordering
        cursor.execute("""
            SELECT r.job_id, r.title, c.combined_text, r.portal, r.country
            FROM raw_jobs r
            INNER JOIN cleaned_jobs c ON r.job_id = c.job_id
            WHERE r.is_usable = TRUE
              AND r.extraction_status = 'pending'
              AND (r.is_gold_standard = FALSE OR r.is_gold_standard IS NULL)
            ORDER BY r.job_id
            LIMIT %s OFFSET %s
        """, (worker_limit, start_offset))

        jobs = cursor.fetchall()
        logger.info(f"Fetched {len(jobs)} jobs for processing")

    # Initialize pipeline
    pipeline = ExtractionPipeline()

    # Process jobs
    total_start = time.time()
    job_times = []
    success_count = 0
    error_count = 0
    total_skills = 0
    esco_matches = 0

    for idx, job_data in enumerate(jobs, 1):
        job_id, title, combined_text, portal, country = job_data

        try:
            job_start = time.time()

            # Mark as processing
            with psycopg2.connect(db_url) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE raw_jobs
                    SET extraction_status = 'processing',
                        extraction_attempts = extraction_attempts + 1
                    WHERE job_id = %s
                """, (job_id,))
                conn.commit()

            # Extract skills
            job_dict = {
                'job_id': job_id,
                'title': title,
                'description': '',
                'requirements': '',
                'combined_text': combined_text,
                'portal': portal,
                'country': country
            }

            extracted_skills = pipeline.extract_skills_from_job(job_dict)

            # Save to DB
            with psycopg2.connect(db_url) as conn:
                cursor = conn.cursor()

                # Save skills
                for skill in extracted_skills:
                    cursor.execute("""
                        INSERT INTO extracted_skills (
                            job_id, skill_text, extraction_method, confidence_score,
                            esco_uri, skill_type, source_section,
                            span_start, span_end
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        job_id,
                        skill.skill_text,
                        skill.extraction_method,
                        skill.original_confidence,
                        skill.esco_match.esco_skill_uri if skill.esco_match else None,
                        skill.skill_type,
                        'unknown',  # source_section - we don't track this in Pipeline A
                        skill.context_position[0] if skill.context_position else None,
                        skill.context_position[1] if skill.context_position else None
                    ))

                # Mark as completed
                cursor.execute("""
                    UPDATE raw_jobs
                    SET extraction_status = 'completed',
                        extraction_completed_at = NOW()
                    WHERE job_id = %s
                """, (job_id,))

                conn.commit()

            job_time = time.time() - job_start
            job_times.append(job_time)
            success_count += 1
            total_skills += len(extracted_skills)
            esco_matches += sum(1 for s in extracted_skills if s.esco_match)

            if idx % 10 == 0:
                avg_time = statistics.mean(job_times)
                logger.info(f"✅ Worker {worker_id + 1}: {idx}/{len(jobs)} jobs | Avg: {avg_time:.2f}s/job | Skills: {total_skills}")

        except Exception as e:
            error_count += 1
            logger.error(f"❌ Error processing job {job_id}: {e}")

            # Mark as pending again
            try:
                with psycopg2.connect(db_url) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE raw_jobs
                        SET extraction_status = 'pending'
                        WHERE job_id = %s
                    """, (job_id,))
                    conn.commit()
            except:
                pass

    # Final summary
    total_time = time.time() - total_start
    avg_time = statistics.mean(job_times) if job_times else 0
    median_time = statistics.median(job_times) if job_times else 0

    logger.info("")
    logger.info("=" * 80)
    logger.info(f"🎉 WORKER {worker_id + 1} COMPLETED")
    logger.info("=" * 80)
    logger.info(f"Jobs processed: {success_count} success, {error_count} errors")
    logger.info(f"Total skills: {total_skills}")
    logger.info(f"ESCO matches: {esco_matches}")
    logger.info(f"ESCO coverage: {(esco_matches / total_skills * 100) if total_skills > 0 else 0:.1f}%")
    logger.info(f"Total time: {total_time / 60:.2f} min ({total_time / 3600:.2f} hours)")
    logger.info(f"Avg time/job: {avg_time:.2f}s")
    logger.info("=" * 80)
    logger.info("")
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"WORKER {worker_id + 1} FINISHED")
    logger.info("=" * 80)
    logger.info(f"✅ Successfully processed {success_count} jobs")
    logger.info(f"❌ Errors: {error_count}")
    logger.info(f"📊 Total skills: {total_skills}")
    logger.info(f"🗺️  ESCO matches: {esco_matches}")
    logger.info("")
    logger.info(f"⏱️  TIMING:")
    logger.info(f"  Total: {total_time / 60:.2f} min ({total_time / 3600:.2f} hours)")
    logger.info(f"  Avg/job: {avg_time:.2f}s")
    logger.info(f"  Median: {median_time:.2f}s")
    logger.info("=" * 80)
    logger.info("")

if __name__ == '__main__':
    main()
