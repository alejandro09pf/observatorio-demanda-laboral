"""
Parallel extraction pipeline with SKIP LOCKED support.
Each worker processes a strategic range to minimize collisions.
"""

from typing import List, Dict, Any
import logging
import psycopg2
import time
import statistics
from .pipeline import ExtractionPipeline, ExtractedSkillResult

logger = logging.getLogger(__name__)


class ParallelExtractionPipeline(ExtractionPipeline):
    """Parallel-safe extraction pipeline using SELECT FOR UPDATE SKIP LOCKED."""

    def __init__(self, worker_id: int = 0, total_workers: int = 1):
        """
        Initialize parallel pipeline.

        Args:
            worker_id: ID of this worker (0-based)
            total_workers: Total number of parallel workers
        """
        super().__init__()
        self.worker_id = worker_id
        self.total_workers = total_workers
        logger.info(f"🔧 Worker {worker_id + 1}/{total_workers} initialized")

    def process_batch_parallel(self, batch_size: int = 100, max_jobs: int = None) -> Dict[str, Any]:
        """
        Process jobs in parallel-safe mode using SKIP LOCKED.

        Args:
            batch_size: Number of jobs to fetch per iteration (smaller batches for parallelism)
            max_jobs: Maximum total jobs to process (None = unlimited)

        Returns:
            Dictionary with processing results and timing metrics
        """
        logger.info(f"🚀 Worker {self.worker_id + 1}: Starting parallel batch processing")
        logger.info(f"   Batch size: {batch_size}, Max jobs: {max_jobs or 'unlimited'}")

        # Initialize metrics
        total_start_time = time.time()
        job_times = []
        results = {
            'worker_id': self.worker_id,
            'processed': 0,
            'success': 0,
            'errors': 0,
            'total_skills': 0,
            'esco_matches': 0,
            'job_details': []
        }

        try:
            jobs_processed = 0

            while True:
                # Check if we've reached max_jobs limit
                if max_jobs and jobs_processed >= max_jobs:
                    logger.info(f"✅ Worker {self.worker_id + 1}: Reached max_jobs limit ({max_jobs})")
                    break

                # Fetch next batch using SKIP LOCKED
                batch_jobs = self._fetch_next_batch_locked(batch_size)

                if not batch_jobs:
                    logger.info(f"✅ Worker {self.worker_id + 1}: No more pending jobs")
                    break

                logger.info(f"📦 Worker {self.worker_id + 1}: Processing batch of {len(batch_jobs)} jobs")

                # Process each job in the batch
                with psycopg2.connect(self.db_url) as conn:
                    cursor = conn.cursor()

                    for job_data in batch_jobs:
                        try:
                            job_start_time = time.time()

                            # Extract skills
                            job_dict = {
                                'job_id': job_data[0],
                                'title': job_data[1],
                                'description': job_data[2],
                                'requirements': job_data[3],
                                'combined_text': job_data[4],
                                'portal': job_data[5],
                                'country': job_data[6],
                                'word_count': job_data[7]
                            }

                            extracted_skills = self.extract_skills_from_job(job_dict)

                            # Save to database
                            self._save_extracted_skills(cursor, job_data[0], extracted_skills)

                            # Mark as completed
                            cursor.execute("""
                                UPDATE raw_jobs
                                SET extraction_status = 'completed',
                                    extraction_completed_at = NOW()
                                WHERE job_id = %s
                            """, (job_data[0],))

                            # Update metrics
                            job_time = time.time() - job_start_time
                            job_times.append(job_time)

                            results['success'] += 1
                            results['total_skills'] += len(extracted_skills)
                            results['esco_matches'] += sum(1 for s in extracted_skills if s.esco_match)

                            jobs_processed += 1

                            # Log progress every 50 jobs
                            if results['success'] % 50 == 0:
                                avg_time = statistics.mean(job_times)
                                logger.info(f"✅ Worker {self.worker_id + 1}: {results['success']} jobs | "
                                          f"Avg: {avg_time:.2f}s/job | "
                                          f"Skills: {results['total_skills']}")

                        except Exception as e:
                            logger.error(f"❌ Worker {self.worker_id + 1}: Error processing job {job_data[0]}: {e}")

                            # Mark as failed
                            cursor.execute("""
                                UPDATE raw_jobs
                                SET extraction_status = 'failed',
                                    extraction_error = %s
                                WHERE job_id = %s
                            """, (str(e), job_data[0]))

                            results['errors'] += 1

                    conn.commit()

            # Calculate final timing statistics
            total_time = time.time() - total_start_time
            results['processed'] = results['success'] + results['errors']

            if job_times:
                results['timing'] = {
                    'total_time_seconds': total_time,
                    'total_time_minutes': total_time / 60,
                    'total_time_hours': total_time / 3600,
                    'avg_time_per_job': statistics.mean(job_times),
                    'median_time_per_job': statistics.median(job_times),
                    'min_time_per_job': min(job_times),
                    'max_time_per_job': max(job_times),
                    'std_dev_time': statistics.stdev(job_times) if len(job_times) > 1 else 0
                }

            # Log final summary
            logger.info("")
            logger.info("=" * 80)
            logger.info(f"🎉 WORKER {self.worker_id + 1} COMPLETED")
            logger.info("=" * 80)
            logger.info(f"Jobs processed: {results['success']} success, {results['errors']} errors")
            logger.info(f"Total skills: {results['total_skills']}")
            logger.info(f"ESCO matches: {results['esco_matches']}")
            if results['total_skills'] > 0:
                logger.info(f"ESCO coverage: {results['esco_matches']/results['total_skills']*100:.1f}%")

            if job_times:
                logger.info(f"Total time: {total_time/60:.2f} min ({total_time/3600:.2f} hours)")
                logger.info(f"Avg time/job: {statistics.mean(job_times):.2f}s")

            logger.info("=" * 80)
            logger.info("")

            return results

        except Exception as e:
            logger.error(f"❌ Worker {self.worker_id + 1}: Batch processing failed: {e}")
            return {'error': str(e), 'worker_id': self.worker_id}

    def _fetch_next_batch_locked(self, batch_size: int) -> List[tuple]:
        """
        Fetch next batch of jobs using UPDATE...RETURNING with SKIP LOCKED.
        This atomically claims jobs for this worker, ensuring no two workers process the same job.

        Strategy: Combined approach
        1. Use modulo partitioning for strategic distribution
        2. Use SKIP LOCKED to handle any collisions gracefully
        """
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Atomic claim: UPDATE pending jobs to processing and return them
                # Use modulo on job_id hash for distribution across workers
                cursor.execute("""
                    UPDATE raw_jobs r
                    SET extraction_status = 'processing',
                        extraction_attempts = extraction_attempts + 1
                    WHERE r.job_id IN (
                        SELECT r2.job_id
                        FROM raw_jobs r2
                        INNER JOIN cleaned_jobs c ON r2.job_id = c.job_id
                        WHERE r2.is_usable = TRUE
                          AND r2.extraction_status = 'pending'
                          AND c.title_cleaned IS NOT NULL
                          AND (hashtext(r2.job_id::text) %% %s) = %s
                        ORDER BY r2.scraped_at ASC
                        LIMIT %s
                        FOR UPDATE OF r2 SKIP LOCKED
                    )
                    RETURNING
                        r.job_id,
                        (SELECT c2.title_cleaned FROM cleaned_jobs c2 WHERE c2.job_id = r.job_id),
                        (SELECT c2.description_cleaned FROM cleaned_jobs c2 WHERE c2.job_id = r.job_id),
                        (SELECT c2.requirements_cleaned FROM cleaned_jobs c2 WHERE c2.job_id = r.job_id),
                        (SELECT c2.combined_text FROM cleaned_jobs c2 WHERE c2.job_id = r.job_id),
                        r.portal,
                        r.country,
                        (SELECT c2.combined_word_count FROM cleaned_jobs c2 WHERE c2.job_id = r.job_id)
                """, (self.total_workers, self.worker_id, batch_size))

                jobs = cursor.fetchall()
                conn.commit()

                return jobs

        except Exception as e:
            logger.error(f"❌ Worker {self.worker_id + 1}: Error fetching batch: {e}")
            return []
