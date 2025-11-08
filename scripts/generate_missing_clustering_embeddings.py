#!/usr/bin/env python3
"""
Generate Missing Embeddings for Clustering Analysis

Generates embeddings for skills that are missing from skill_embeddings table
for the following datasets:
1. gold_standard_annotations (manual annotations)
2. enhanced_skills Pre-ESCO (Pipeline B emergent skills)
3. enhanced_skills Post-ESCO (Pipeline B ESCO-matched skills)

This ensures we have complete coverage for clustering analysis.
"""

import sys
import logging
from datetime import datetime
from typing import List, Set
import psycopg2
from sentence_transformers import SentenceTransformer
import numpy as np
from tqdm import tqdm

# Add src to path
sys.path.append('.')
from src.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Get database connection from settings."""
    settings = get_settings()
    db_url = settings.database_url

    # Parse connection string
    # Format: postgresql://user:pass@host:port/dbname
    parts = db_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_port_db = parts[1].split('/')
    host_port = host_port_db[0].split(':')

    return psycopg2.connect(
        dbname=host_port_db[1],
        user=user_pass[0],
        password=user_pass[1],
        host=host_port[0],
        port=host_port[1]
    )

def get_missing_skills() -> tuple[List[str], List[str], List[str]]:
    """
    Get skills missing embeddings for each dataset.

    Returns:
        Tuple of (manual_skills, pipeb_pre_skills, pipeb_post_skills)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    logger.info("=" * 80)
    logger.info("IDENTIFYING MISSING EMBEDDINGS")
    logger.info("=" * 80)

    # 1. Manual annotations
    logger.info("\n1. gold_standard_annotations (Manual)")
    cur.execute("""
        SELECT DISTINCT skill_text
        FROM gold_standard_annotations
        WHERE skill_type = 'hard'
          AND NOT EXISTS (
              SELECT 1 FROM skill_embeddings se
              WHERE LOWER(TRIM(se.skill_text)) = LOWER(TRIM(gold_standard_annotations.skill_text))
          )
        ORDER BY skill_text
    """)
    manual_missing = [row[0] for row in cur.fetchall()]
    logger.info(f"   Missing: {len(manual_missing)} skills")

    # 2. Pipeline B Pre-ESCO
    logger.info("\n2. enhanced_skills Pre-ESCO (Pipeline B)")
    cur.execute("""
        SELECT DISTINCT normalized_skill
        FROM enhanced_skills
        WHERE skill_type = 'hard'
          AND (esco_concept_uri IS NULL OR esco_concept_uri = '')
          AND NOT EXISTS (
              SELECT 1 FROM skill_embeddings se
              WHERE LOWER(TRIM(se.skill_text)) = LOWER(TRIM(enhanced_skills.normalized_skill))
          )
        ORDER BY normalized_skill
    """)
    pipeb_pre_missing = [row[0] for row in cur.fetchall()]
    logger.info(f"   Missing: {len(pipeb_pre_missing)} skills")

    # 3. Pipeline B Post-ESCO
    logger.info("\n3. enhanced_skills Post-ESCO (Pipeline B)")
    cur.execute("""
        SELECT DISTINCT normalized_skill
        FROM enhanced_skills
        WHERE skill_type = 'hard'
          AND esco_concept_uri IS NOT NULL AND esco_concept_uri != ''
          AND NOT EXISTS (
              SELECT 1 FROM skill_embeddings se
              WHERE LOWER(TRIM(se.skill_text)) = LOWER(TRIM(enhanced_skills.normalized_skill))
          )
        ORDER BY normalized_skill
    """)
    pipeb_post_missing = [row[0] for row in cur.fetchall()]
    logger.info(f"   Missing: {len(pipeb_post_missing)} skills")

    total_missing = len(manual_missing) + len(pipeb_pre_missing) + len(pipeb_post_missing)
    logger.info(f"\n   TOTAL MISSING: {total_missing} skills")

    conn.close()
    return manual_missing, pipeb_pre_missing, pipeb_post_missing

def generate_embeddings(skills: List[str], model: SentenceTransformer) -> np.ndarray:
    """Generate embeddings for a list of skills."""
    if not skills:
        return np.array([])

    logger.info(f"\n🚀 Generating embeddings for {len(skills)} skills...")

    # Normalize with "query: " prefix for e5 models
    normalized_skills = [f"query: {skill}" for skill in skills]

    # Generate embeddings
    embeddings = model.encode(
        normalized_skills,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32
    )

    logger.info(f"   ✅ Generated embeddings shape: {embeddings.shape}")
    return embeddings

def save_embeddings(skills: List[str], embeddings: np.ndarray) -> int:
    """Save embeddings to database."""
    if len(skills) == 0:
        return 0

    conn = get_db_connection()
    cur = conn.cursor()

    logger.info(f"\n💾 Saving {len(skills)} embeddings to database...")

    saved_count = 0
    for skill, embedding in tqdm(zip(skills, embeddings), total=len(skills), desc="Inserting"):
        try:
            cur.execute("""
                INSERT INTO skill_embeddings (skill_text, embedding, model_name, model_version, created_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (skill_text) DO NOTHING
            """, (skill, embedding.tolist(), 'intfloat/multilingual-e5-base', 'base', datetime.now()))
            saved_count += 1
        except Exception as e:
            logger.warning(f"   Failed to insert '{skill}': {e}")
            continue

    conn.commit()
    conn.close()

    logger.info(f"   ✅ Saved {saved_count} embeddings")
    return saved_count

def main():
    logger.info("=" * 80)
    logger.info("GENERATING MISSING EMBEDDINGS FOR CLUSTERING")
    logger.info("=" * 80)
    logger.info(f"Start time: {datetime.now()}")

    # Get missing skills
    manual_missing, pipeb_pre_missing, pipeb_post_missing = get_missing_skills()

    total_missing = len(manual_missing) + len(pipeb_pre_missing) + len(pipeb_post_missing)

    if total_missing == 0:
        logger.info("\n✅ No missing embeddings! All skills already have embeddings.")
        return

    # Combine all missing skills (remove duplicates)
    all_missing = list(set(manual_missing + pipeb_pre_missing + pipeb_post_missing))
    logger.info(f"\n📊 Unique skills to embed: {len(all_missing)}")

    # Load model
    logger.info("\n" + "=" * 80)
    logger.info("LOADING EMBEDDING MODEL")
    logger.info("=" * 80)
    model_name = "intfloat/multilingual-e5-base"
    logger.info(f"   Model: {model_name}")

    model = SentenceTransformer(model_name)
    logger.info(f"   ✅ Model loaded")

    # Generate embeddings
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING EMBEDDINGS")
    logger.info("=" * 80)

    embeddings = generate_embeddings(all_missing, model)

    # Save to database
    logger.info("\n" + "=" * 80)
    logger.info("SAVING TO DATABASE")
    logger.info("=" * 80)

    saved_count = save_embeddings(all_missing, embeddings)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ COMPLETE")
    logger.info("=" * 80)
    logger.info(f"   Skills processed: {len(all_missing)}")
    logger.info(f"   Embeddings saved: {saved_count}")
    logger.info(f"   End time: {datetime.now()}")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
