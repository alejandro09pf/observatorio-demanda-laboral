#!/usr/bin/env python3
"""
Individual worker script for parallel processing V2 (Fixed Ranges).
Each worker processes a fixed range of jobs.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extractor.parallel_pipeline_v2 import ParallelExtractionPipelineV2
import logging

def main():
    """Process jobs with parallel worker V2."""
    if len(sys.argv) < 3:
        print("Usage: process_parallel_worker_v2.py <worker_id> <total_workers> [max_jobs]")
        sys.exit(1)

    worker_id = int(sys.argv[1])
    total_workers = int(sys.argv[2])
    max_jobs = int(sys.argv[3]) if len(sys.argv) > 3 else None

    # Setup logging for this worker
    logging.basicConfig(
        level=logging.INFO,
        format=f'%(asctime)s - W{worker_id+1} - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    logger = logging.getLogger(__name__)

    logger.info("=" * 80)
    logger.info(f"PARALLEL WORKER {worker_id + 1}/{total_workers} (V2 - Fixed Ranges)")
    logger.info("=" * 80)
    logger.info(f"Worker ID: {worker_id}")
    logger.info(f"Total workers: {total_workers}")
    logger.info(f"Max jobs: {max_jobs or 'all assigned to this worker'}")
    logger.info("")

    # Initialize pipeline for this worker
    logger.info(f"[1/2] Initializing Pipeline A V2 for Worker {worker_id + 1}...")
    pipeline = ParallelExtractionPipelineV2(worker_id=worker_id, total_workers=total_workers)
    logger.info("  ✅ Pipeline initialized")
    logger.info("")

    # Process jobs
    logger.info(f"[2/2] Processing assigned job range...")
    logger.info("")

    results = pipeline.process_batch_parallel(max_jobs=max_jobs)

    # Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"WORKER {worker_id + 1} FINISHED")
    logger.info("=" * 80)

    if 'error' in results:
        logger.error(f"Error: {results['error']}")
        return 1

    logger.info(f"✅ Successfully processed {results['success']} jobs")
    logger.info(f"❌ Errors: {results['errors']}")
    logger.info(f"📊 Total skills: {results['total_skills']}")
    logger.info(f"🗺️  ESCO matches: {results['esco_matches']}")

    if 'timing' in results:
        timing = results['timing']
        logger.info("")
        logger.info("⏱️  TIMING:")
        logger.info(f"  Total: {timing['total_time_minutes']:.2f} min ({timing['total_time_hours']:.2f} hours)")
        logger.info(f"  Avg/job: {timing['avg_time_per_job']:.2f}s")
        logger.info(f"  Median: {timing['median_time_per_job']:.2f}s")

    logger.info("=" * 80)
    logger.info("")

    return 0

if __name__ == "__main__":
    sys.exit(main())
