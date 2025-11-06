#!/usr/bin/env python3
"""
Process all 30,660 usable jobs with Pipeline A.
Direct script that bypasses automation system.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from extractor.pipeline import ExtractionPipeline
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

logger = logging.getLogger(__name__)

def main():
    """Process all 30,660 jobs with Pipeline A."""
    logger.info("=" * 80)
    logger.info("PIPELINE A - SCALE PROCESSING (30,660 jobs)")
    logger.info("=" * 80)
    logger.info("")

    # Initialize pipeline
    logger.info("[1/2] Initializing Pipeline A (NER + Regex + ESCO)...")
    pipeline = ExtractionPipeline()
    logger.info("  ✅ Pipeline initialized")
    logger.info("")

    # Process batch
    logger.info("[2/2] Processing all extraction-ready jobs...")
    logger.info("  Batch size: 30660 (all usable jobs)")
    logger.info("")

    results = pipeline.process_batch(batch_size=30660)

    # Final summary
    logger.info("")
    logger.info("=" * 80)
    logger.info("PROCESSING COMPLETE")
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
        logger.info(f"  Total: {timing['total_time_hours']:.2f} hours")
        logger.info(f"  Avg/job: {timing['avg_time_per_job']:.2f}s")

    logger.info("=" * 80)
    logger.info("")

    return 0

if __name__ == "__main__":
    sys.exit(main())
