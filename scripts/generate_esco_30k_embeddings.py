#!/usr/bin/env python3
"""
Generate embeddings for ESCO-matched skills from 30k jobs (Pipeline A).

This script generates embeddings for the 1,702 unique ESCO-matched hard skills
extracted from 30k jobs processed with Pipeline A.

Dataset:
- Source: extracted_skills WHERE skill_type='hard' AND esco_uri IS NOT NULL
- Total skills: 1,702 unique
- Already have embeddings: ~352 (20.7%)
- Need embeddings: ~1,350 (79.3%)

Usage:
    python scripts/generate_esco_30k_embeddings.py
"""

import sys
import argparse
from pathlib import Path
from typing import List, Tuple, Dict
import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.config.settings import get_settings


def normalize_skill_text(skill_text: str) -> str:
    """Normalize skill text before generating embeddings."""
    normalized = skill_text.strip()
    normalized = ' '.join(normalized.split())

    replacements = {
        'ci/cd': 'CI/CD',
        'api': 'API',
        'rest api': 'REST API',
        'restful api': 'REST API',
        'graphql': 'GraphQL',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'nodejs': 'Node.js',
        'node.js': 'Node.js',
        'reactjs': 'React',
        'vuejs': 'Vue.js',
        'angularjs': 'Angular',
        'aws': 'AWS',
        'gcp': 'GCP',
        'sql': 'SQL',
        'nosql': 'NoSQL',
        'mongodb': 'MongoDB',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
    }

    normalized_lower = normalized.lower()
    for old, new in replacements.items():
        if normalized_lower == old.lower():
            normalized = new
            break

    return normalized


def load_esco_skills(exclude_existing: bool = True) -> List[Tuple[str, str]]:
    """
    Load unique ESCO-matched skills from extracted_skills.

    Args:
        exclude_existing: If True, exclude skills that already have embeddings

    Returns:
        List of (original_text, normalized_text) tuples
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    if exclude_existing:
        query = """
            SELECT DISTINCT es.skill_text
            FROM extracted_skills es
            LEFT JOIN skill_embeddings se
                ON LOWER(TRIM(es.skill_text)) = LOWER(TRIM(se.skill_text))
            WHERE es.skill_type = 'hard'
              AND es.esco_uri IS NOT NULL
              AND se.skill_text IS NULL
            ORDER BY es.skill_text
        """
    else:
        query = """
            SELECT DISTINCT skill_text
            FROM extracted_skills
            WHERE skill_type = 'hard'
              AND esco_uri IS NOT NULL
            ORDER BY skill_text
        """

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    # Normalize and prepare skills
    skills = []
    seen = set()

    for (original_text,) in results:
        normalized_text = normalize_skill_text(original_text)

        # Avoid duplicates after normalization
        if normalized_text.lower() not in seen:
            skills.append((original_text, normalized_text))
            seen.add(normalized_text.lower())

    return skills


def generate_embeddings(
    skills: List[Tuple[str, str]],
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 128
) -> Tuple[List[str], List[str], np.ndarray]:
    """
    Generate embeddings for normalized skills.

    Args:
        skills: List of (original, normalized) tuples
        model_name: HuggingFace model identifier
        batch_size: Batch size for encoding

    Returns:
        (original_texts, normalized_texts, embeddings)
    """
    print(f"\n{'='*80}")
    print(f"LOADING MODEL: {model_name}")
    print(f"{'='*80}")

    model = SentenceTransformer(model_name)

    original_texts = [s[0] for s in skills]
    normalized_texts = [s[1] for s in skills]

    print(f"\n📊 Skills to embed: {len(normalized_texts):,}")
    print(f"   Batch size: {batch_size}")
    print(f"   Expected batches: {(len(normalized_texts) + batch_size - 1) // batch_size}")

    # Show examples
    print(f"\n🔍 Sample skills (first 10):")
    for i in range(min(10, len(skills))):
        orig = original_texts[i]
        norm = normalized_texts[i]
        if orig != norm:
            print(f"   '{orig}' → '{norm}'")
        else:
            print(f"   '{orig}'")

    if len(skills) > 10:
        print(f"   ... and {len(skills) - 10:,} more")

    print(f"\n🚀 Generating embeddings...")

    embeddings = model.encode(
        normalized_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    print(f"\n✅ Embeddings generated!")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Dtype: {embeddings.dtype}")

    return original_texts, normalized_texts, embeddings


def save_embeddings_to_db(
    original_texts: List[str],
    normalized_texts: List[str],
    embeddings: np.ndarray,
    model_name: str = "intfloat/multilingual-e5-base",
    model_version: str = "v1.0"
) -> Dict[str, int]:
    """
    Save embeddings to skill_embeddings table.

    Returns:
        Stats dict with inserted, updated, errors
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print(f"\n{'='*80}")
    print(f"SAVING EMBEDDINGS TO DATABASE")
    print(f"{'='*80}")
    print(f"   Total embeddings: {len(normalized_texts):,}")
    print()

    inserted = 0
    updated = 0
    errors = 0

    for orig_text, norm_text, embedding in tqdm(
        zip(original_texts, normalized_texts, embeddings),
        total=len(normalized_texts),
        desc="Inserting embeddings"
    ):
        try:
            embedding_list = embedding.astype(np.float32).tolist()

            cursor.execute("""
                SELECT skill_text FROM skill_embeddings
                WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            """, (norm_text,))

            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE skill_embeddings
                    SET embedding = %s,
                        model_name = %s,
                        model_version = %s,
                        created_at = CURRENT_TIMESTAMP
                    WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
                """, (embedding_list, model_name, model_version, norm_text))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO skill_embeddings (
                        skill_text, embedding, model_name, model_version
                    ) VALUES (%s, %s, %s, %s)
                """, (norm_text, embedding_list, model_name, model_version))
                inserted += 1

            if (inserted + updated) % 100 == 0:
                conn.commit()

        except Exception as e:
            errors += 1
            print(f"\n❌ Error with '{orig_text}' → '{norm_text}': {e}")
            continue

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
    total_in_db = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    stats = {
        'inserted': inserted,
        'updated': updated,
        'errors': errors,
        'total_in_db': total_in_db
    }

    print(f"\n{'='*80}")
    print(f"✅ EMBEDDINGS SAVED")
    print(f"{'='*80}")
    print(f"   Inserted:    {inserted:,}")
    print(f"   Updated:     {updated:,}")
    print(f"   Errors:      {errors:,}")
    print(f"   Total in DB: {total_in_db:,}")
    print()

    return stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for ESCO-matched skills from 30k jobs"
    )
    parser.add_argument(
        '--include-existing',
        action='store_true',
        help="Include skills that already have embeddings (will update them)"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=128,
        help="Batch size for encoding (default: 128)"
    )

    args = parser.parse_args()

    print("="*80)
    print("ESCO 30K EMBEDDINGS GENERATOR")
    print("="*80)
    print(f"Include existing: {args.include_existing}")
    print(f"Batch size:       {args.batch_size}")
    print(f"Model:            intfloat/multilingual-e5-base")
    print()

    # Step 1: Load skills
    print("📂 Loading ESCO-matched skills from extracted_skills...")
    skills = load_esco_skills(exclude_existing=not args.include_existing)
    print(f"   Loaded: {len(skills):,} skills")

    if len(skills) == 0:
        print("\n✅ No skills to process (all already have embeddings)")
        return

    # Step 2: Generate embeddings
    original_texts, normalized_texts, embeddings = generate_embeddings(
        skills,
        batch_size=args.batch_size
    )

    # Step 3: Save to database
    stats = save_embeddings_to_db(
        original_texts,
        normalized_texts,
        embeddings
    )

    # Final summary
    print("="*80)
    print("✅ PROCESS COMPLETE")
    print("="*80)
    print(f"   Skills processed: {len(skills):,}")
    print(f"   Inserted:         {stats['inserted']:,}")
    print(f"   Updated:          {stats['updated']:,}")
    print(f"   Errors:           {stats['errors']:,}")
    print(f"   Total in DB:      {stats['total_in_db']:,}")
    print()

    if stats['errors'] > 0:
        print("⚠️  Some errors occurred. Check output above for details.")

    print("🎯 Next step: Run parameter experiments")
    print("   python scripts/experiment_esco_30k_parameters.py")
    print()


if __name__ == '__main__':
    main()
