"""
Parallel extraction pipeline V2 with FIXED RANGE distribution.
Each worker gets a fixed range of jobs (e.g., 1-3000, 3001-6000, etc.)
"""

from typing import List, Dict, Any
import logging
import psycopg2
import time
import statistics
from .pipeline import ExtractionPipeline, ExtractedSkillResult

logger = logging.getLogger(__name__)


class ParallelExtractionPipelineV2(ExtractionPipeline):
    """Parallel-safe extraction pipeline using fixed range distribution."""

    def __init__(self, worker_id: int = 0, total_workers: int = 1):
        """
        Initialize parallel pipeline with fixed range assignment.

        Args:
            worker_id: ID of this worker (0-based)
            total_workers: Total number of parallel workers
        """
        super().__init__()
        self.worker_id = worker_id
        self.total_workers = total_workers
        logger.info(f"🔧 Worker {worker_id + 1}/{total_workers} initialized (V2 - Fixed Ranges)")

    def process_batch_parallel(self, max_jobs: int = None) -> Dict[str, Any]:
        """
        Process jobs in parallel using fixed range assignment.

        Args:
            max_jobs: Maximum total jobs to process for THIS worker (None = all assigned to this worker)

        Returns:
            Dictionary with processing results and timing metrics
        """
        logger.info(f"🚀 Worker {self.worker_id + 1}: Starting parallel processing (Fixed Ranges V2)")
        logger.info(f"   Max jobs for this worker: {max_jobs or 'all assigned'}")

        # Initialize metrics
        total_start_time = time.time()
        job_times = []
        results = {
            'worker_id': self.worker_id,
            'processed': 0,
            'success': 0,
            'errors': 0,
            'total_skills': 0,
            'esco_matches': 0
        }

        try:
            jobs_processed = 0

            # Get all jobs assigned to this worker (by range)
            all_worker_jobs = self._get_worker_jobs(max_jobs)

            if not all_worker_jobs:
                logger.info(f"✅ Worker {self.worker_id + 1}: No jobs assigned to this worker")
                return results

            logger.info(f"📦 Worker {self.worker_id + 1}: Assigned {len(all_worker_jobs)} jobs total")

            # Process in small batches for better commit granularity
            batch_size = 10
            for i in range(0, len(all_worker_jobs), batch_size):
                batch = all_worker_jobs[i:i+batch_size]

                with psycopg2.connect(self.db_url) as conn:
                    cursor = conn.cursor()

                    for job_data in batch:
                        try:
                            job_start_time = time.time()

                            # Mark as processing
                            cursor.execute("""
                                UPDATE raw_jobs
                                SET extraction_status = 'processing',
                                    extraction_attempts = extraction_attempts + 1
                                WHERE job_id = %s
                            """, (job_data[0],))

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

                            # Log progress every 10 jobs
                            if results['success'] % 10 == 0:
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

    def _get_worker_jobs(self, max_jobs: int = None) -> List[tuple]:
        """
        Get jobs assigned to this worker using fixed range partitioning.

        Strategy: Divide all pending jobs into N equal ranges, one per worker.
        Worker 0 gets jobs 1 to N, Worker 1 gets jobs N+1 to 2N, etc.
        """
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # First, get total count of pending jobs
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM raw_jobs r
                    INNER JOIN cleaned_jobs c ON r.job_id = c.job_id
                    WHERE r.is_usable = TRUE
                      AND r.extraction_status = 'pending'
                      AND (r.is_gold_standard = FALSE OR r.is_gold_standard IS NULL)
                      AND c.title_cleaned IS NOT NULL
                """)

                total_pending = cursor.fetchone()[0]

                if total_pending == 0:
                    return []

                # Calculate range for this worker
                jobs_per_worker = total_pending // self.total_workers
                remainder = total_pending % self.total_workers

                # Distribute remainder across first workers
                if self.worker_id < remainder:
                    start_offset = self.worker_id * (jobs_per_worker + 1)
                    worker_limit = jobs_per_worker + 1
                else:
                    start_offset = (remainder * (jobs_per_worker + 1)) + \
                                 ((self.worker_id - remainder) * jobs_per_worker)
                    worker_limit = jobs_per_worker

                # Apply max_jobs limit if specified
                if max_jobs:
                    worker_limit = min(worker_limit, max_jobs)

                logger.info(f"📍 Worker {self.worker_id + 1}: Range = {start_offset} to {start_offset + worker_limit - 1} (of {total_pending} total)")

                # Fetch this worker's jobs
                cursor.execute("""
                    SELECT
                        r.job_id,
                        c.title_cleaned,
                        c.description_cleaned,
                        c.requirements_cleaned,
                        c.combined_text,
                        r.portal,
                        r.country,
                        c.combined_word_count
                    FROM raw_jobs r
                    INNER JOIN cleaned_jobs c ON r.job_id = c.job_id
                    WHERE r.is_usable = TRUE
                      AND r.extraction_status = 'pending'
                      AND (r.is_gold_standard = FALSE OR r.is_gold_standard IS NULL)
                      AND c.title_cleaned IS NOT NULL
                    ORDER BY r.scraped_at ASC
                    LIMIT %s OFFSET %s
                """, (worker_limit, start_offset))

                jobs = cursor.fetchall()
                return jobs

        except Exception as e:
            logger.error(f"❌ Worker {self.worker_id + 1}: Error fetching jobs: {e}")
            return []
