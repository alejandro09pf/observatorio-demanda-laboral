#!/usr/bin/env python3
"""
PHASE 0 - Step 0.1: Generate embeddings for all skills in esco_skills table.

This script:
1. Loads all active skills from esco_skills (14,174 expected)
2. Generates 768D embeddings using multilingual-e5-base model
3. Stores embeddings in skill_embeddings table
4. Shows progress and statistics

Model: intfloat/multilingual-e5-base
Embedding dimension: 768
Batch size: 32 (adjustable)
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple

import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings


def load_skills_to_embed() -> List[Tuple[str, str, str]]:
    """
    Load all active skills from esco_skills.

    Returns:
        List of tuples: (skill_uri, preferred_label_en, preferred_label_es)
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT skill_uri, preferred_label_en, preferred_label_es
        FROM esco_skills
        WHERE is_active = TRUE
        ORDER BY skill_uri
    """)

    skills = cursor.fetchall()
    cursor.close()
    conn.close()

    return skills


def generate_embeddings(
    skills: List[Tuple[str, str, str]],
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 32,
    test_mode: bool = False,
    test_limit: int = 100
) -> Tuple[List[str], np.ndarray]:
    """
    Generate embeddings for skills using multilingual-e5-base.

    Args:
        skills: List of (skill_uri, label_en, label_es) tuples
        model_name: HuggingFace model identifier
        batch_size: Number of skills to process at once
        test_mode: If True, only process first test_limit skills
        test_limit: Number of skills to process in test mode

    Returns:
        Tuple of (skill_texts, embeddings_array)
    """
    print(f"\n{'='*70}")
    print(f"LOADING MODEL: {model_name}")
    print(f"{'='*70}")

    # Load model
    model = SentenceTransformer(model_name)

    # Prepare texts for embedding
    # Use Spanish label (ESCO skills only have Spanish labels populated)
    skill_texts = []
    for skill_uri, label_en, label_es in skills:
        # Use Spanish label (label_en is empty for ESCO skills)
        # For O*NET and manual skills, both are the same (tech terms don't translate)
        skill_text = label_es if label_es else label_en
        skill_texts.append(skill_text)

    # Apply test mode limit if enabled
    if test_mode:
        skill_texts = skill_texts[:test_limit]
        print(f"\n⚠️  TEST MODE: Processing only {test_limit} skills")

    print(f"\n📊 Skills to embed: {len(skill_texts):,}")
    print(f"   Batch size: {batch_size}")
    print(f"   Expected batches: {(len(skill_texts) + batch_size - 1) // batch_size}")
    print()

    # Generate embeddings with progress bar
    print("🚀 Generating embeddings...")
    start_time = time.time()

    embeddings = model.encode(
        skill_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalization for cosine similarity
    )

    elapsed = time.time() - start_time

    print(f"\n✅ Embeddings generated!")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Dtype: {embeddings.dtype}")
    print(f"   Time: {elapsed:.2f}s ({len(skill_texts)/elapsed:.1f} skills/sec)")
    print(f"\n🔍 Debug: First 5 skill texts:")
    for i, text in enumerate(skill_texts[:5]):
        print(f"   [{i}] {text}")

    return skill_texts, embeddings


def save_embeddings_to_db(
    skill_texts: List[str],
    embeddings: np.ndarray,
    model_name: str = "intfloat/multilingual-e5-base",
    model_version: str = "v1.0"
) -> int:
    """
    Save embeddings to skill_embeddings table.

    Args:
        skill_texts: List of skill text labels
        embeddings: Numpy array of embeddings (N x 768)
        model_name: Model identifier
        model_version: Model version string

    Returns:
        Number of embeddings inserted
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print(f"\n{'='*70}")
    print(f"SAVING EMBEDDINGS TO DATABASE")
    print(f"{'='*70}")
    print(f"   Total embeddings: {len(skill_texts):,}")
    print(f"\n🔍 Debug: First 3 skill texts to save:")
    for i, text in enumerate(skill_texts[:3]):
        print(f"   [{i}] '{text}' (len={len(text) if text else 0})")
    print()

    inserted = 0
    skipped = 0
    errors = 0

    # Use tqdm for progress
    for skill_text, embedding in tqdm(
        zip(skill_texts, embeddings),
        total=len(skill_texts),
        desc="Inserting embeddings"
    ):
        try:
            # Convert numpy array to Python list of floats
            embedding_list = embedding.astype(np.float32).tolist()

            cursor.execute("""
                INSERT INTO skill_embeddings (
                    skill_text, embedding, model_name, model_version
                ) VALUES (%s, %s, %s, %s)
                ON CONFLICT (skill_text) DO UPDATE SET
                    embedding = EXCLUDED.embedding,
                    model_name = EXCLUDED.model_name,
                    model_version = EXCLUDED.model_version,
                    created_at = CURRENT_TIMESTAMP
            """, (skill_text, embedding_list, model_name, model_version))

            if cursor.rowcount > 0:
                inserted += 1
            else:
                skipped += 1

            # Commit every 100 records
            if inserted % 100 == 0:
                conn.commit()

        except Exception as e:
            errors += 1
            print(f"\n❌ Error with '{skill_text}': {e}")
            continue

    # Final commit
    conn.commit()

    # Verify count
    cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
    total_in_db = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print(f"\n{'='*70}")
    print(f"✅ EMBEDDINGS SAVED")
    print(f"{'='*70}")
    print(f"   Inserted:  {inserted:,}")
    print(f"   Skipped:   {skipped:,}")
    print(f"   Errors:    {errors:,}")
    print(f"   Total in DB: {total_in_db:,}")
    print()

    return inserted


def main():
    """Main execution function."""

    # Parse command line arguments
    test_mode = "--test" in sys.argv
    test_limit = 100

    # Check for custom test limit
    for arg in sys.argv:
        if arg.startswith("--limit="):
            test_limit = int(arg.split("=")[1])

    print("="*70)
    print("PHASE 0 - STEP 0.1: GENERATE SKILL EMBEDDINGS")
    print("="*70)
    print(f"Model: intfloat/multilingual-e5-base")
    print(f"Embedding dimension: 768")
    print(f"Mode: {'TEST' if test_mode else 'PRODUCTION'}")
    if test_mode:
        print(f"Test limit: {test_limit}")
    print()

    # Step 1: Load skills
    print("📂 Loading skills from database...")
    skills = load_skills_to_embed()
    print(f"   Loaded: {len(skills):,} skills")

    # Step 2: Generate embeddings
    skill_texts, embeddings = generate_embeddings(
        skills,
        batch_size=32,
        test_mode=test_mode,
        test_limit=test_limit
    )

    # Step 3: Save to database
    inserted = save_embeddings_to_db(
        skill_texts,
        embeddings,
        model_name="intfloat/multilingual-e5-base",
        model_version="v1.0"
    )

    # Final summary
    print("="*70)
    print("✅ PHASE 0 - STEP 0.1 COMPLETE")
    print("="*70)
    print(f"   Total skills embedded: {inserted:,}")
    print(f"   Embedding dimension: {embeddings.shape[1]}")
    print(f"   Model: intfloat/multilingual-e5-base")
    print()

    if test_mode:
        print("⚠️  This was a TEST RUN. To process all skills, run:")
        print("   python scripts/phase0_generate_embeddings.py")
    else:
        print("🎯 Next step: Build FAISS index (TODO-0.2)")
        print("   python scripts/phase0_build_faiss_index.py")
    print()


if __name__ == '__main__':
    main()
