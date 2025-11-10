#!/usr/bin/env python3
"""
Generate embeddings for ALL skills in extracted_skills table.

This script generates embeddings for all unique skill_text values in extracted_skills
that don't already have embeddings in skill_embeddings table.
"""

import sys
import os
import logging
import argparse
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.config import get_settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768


def get_db_connection():
    """Get database connection."""
    settings = get_settings()
    db_url = settings.database_url

    # Parse postgresql URL
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


def get_missing_skills():
    """Get all skills from extracted_skills that don't have embeddings."""
    conn = get_db_connection()
    cursor = conn.cursor()

    logger.info("Fetching skills without embeddings from extracted_skills...")

    cursor.execute("""
        SELECT DISTINCT skill_text
        FROM extracted_skills es
        WHERE NOT EXISTS (
            SELECT 1
            FROM skill_embeddings se
            WHERE se.skill_text = es.skill_text
        )
        ORDER BY skill_text
    """)

    skills = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    logger.info(f"Found {len(skills):,} skills without embeddings")
    return skills


def generate_embeddings(skills, batch_size=256):
    """Generate embeddings for skills."""
    logger.info(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    logger.info(f"Generating embeddings for {len(skills):,} skills (batch_size={batch_size})...")

    all_embeddings = []

    for i in tqdm(range(0, len(skills), batch_size), desc="Batches"):
        batch = skills[i:i + batch_size]
        # Normalize skill texts for embedding
        normalized = [f"query: {text}" for text in batch]
        embeddings = model.encode(normalized, show_progress_bar=False)
        all_embeddings.append(embeddings)

    all_embeddings = np.vstack(all_embeddings)
    logger.info(f"Generated embeddings shape: {all_embeddings.shape}")

    return all_embeddings


def save_embeddings(skills, embeddings):
    """Save embeddings to skill_embeddings table."""
    conn = get_db_connection()
    cursor = conn.cursor()

    logger.info(f"Saving {len(skills):,} embeddings to database...")

    for skill_text, embedding in tqdm(zip(skills, embeddings), total=len(skills), desc="Inserting"):
        cursor.execute("""
            INSERT INTO skill_embeddings (skill_text, embedding, model_name)
            VALUES (%s, %s, %s)
            ON CONFLICT (skill_text) DO NOTHING
        """, (skill_text, embedding.tolist(), MODEL_NAME))

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("✅ Embeddings saved successfully!")


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for extracted_skills")
    parser.add_argument('--batch-size', type=int, default=256, help='Batch size for embedding generation')
    args = parser.parse_args()

    logger.info("="*80)
    logger.info("EXTRACTED SKILLS EMBEDDINGS GENERATOR")
    logger.info("="*80)
    logger.info(f"Model: {MODEL_NAME}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("")

    # Get missing skills
    skills = get_missing_skills()

    if len(skills) == 0:
        logger.info("✅ All skills already have embeddings!")
        return

    # Generate embeddings
    embeddings = generate_embeddings(skills, batch_size=args.batch_size)

    # Save to database
    save_embeddings(skills, embeddings)

    logger.info("")
    logger.info("="*80)
    logger.info("✅ COMPLETE")
    logger.info("="*80)


if __name__ == '__main__':
    main()
