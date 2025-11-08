#!/usr/bin/env python3
"""
Script para ejecutar Pipeline A.1 (TF-IDF + NP Chunking) sobre gold standard
y persistir las skills extraídas en la base de datos.

Uso:
    python scripts/persist_pipeline_a1_skills.py

Las skills se guardarán en extracted_skills con:
- extraction_method = 'pipeline-a1-tfidf-np'
- source_section = 'combined_text'
- skill_type = 'hard' (por defecto)
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.evaluation.dual_comparator import DualPipelineComparator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    """
    Ejecuta Pipeline A.1 sobre gold standard y persiste skills en DB.
    """
    logger.info("=" * 80)
    logger.info("PIPELINE A.1 - PERSISTENCE TO DATABASE")
    logger.info("=" * 80)
    logger.info("")

    # Initialize comparator (uses settings from config)
    comparator = DualPipelineComparator()

    # Run Pipeline A.1 with persistence
    logger.info("Step 1: Running Pipeline A.1 (TF-IDF + NP Chunking) on gold standard...")
    logger.info("")

    pipeline_data = comparator.load_pipeline_a1(
        job_ids=None,  # Process all gold standard jobs
        persist_to_db=True  # ← PERSIST TO DATABASE
    )

    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ PIPELINE A.1 SKILLS PERSISTED SUCCESSFULLY")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Jobs processed: {len(pipeline_data.skills_by_job)}")
    logger.info(f"Total skills: {pipeline_data.total_skills}")
    logger.info(f"Unique skills: {pipeline_data.unique_skills}")
    logger.info("")
    logger.info("Skills saved to: extracted_skills table")
    logger.info("Extraction method: pipeline-a1-tfidf-np")
    logger.info("")
    logger.info("Query to verify:")
    logger.info("  SELECT COUNT(*) FROM extracted_skills WHERE extraction_method = 'pipeline-a1-tfidf-np';")
    logger.info("")


if __name__ == '__main__':
    main()
