#!/usr/bin/env python3
"""
Generate embeddings for missing ESCO skills from new Pipeline A extraction (NER+REGEX).

This script generates embeddings ONLY for ESCO-matched skills from extracted_skills
that don't already have embeddings in skill_embeddings table.

Usage:
    python scripts/generate_missing_esco_30k_embeddings.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import psycopg2
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from src.config.settings import get_settings


def get_missing_esco_skills():
    """
    Get ESCO skills from extracted_skills (NER+REGEX) that don't have embeddings.

    Returns:
        List of (skill_text, frequency) tuples
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print("="*80)
    print("FINDING MISSING ESCO SKILLS (NER+REGEX)")
    print("="*80)

    query = """
        SELECT es.skill_text, COUNT(*) as frequency
        FROM extracted_skills es
        WHERE es.esco_uri IS NOT NULL
          AND es.skill_type = 'hard'
          AND es.extraction_method IN ('ner', 'regex')
          AND NOT EXISTS (
              SELECT 1 FROM skill_embeddings se
              WHERE LOWER(TRIM(se.skill_text)) = LOWER(TRIM(es.skill_text))
          )
        GROUP BY es.skill_text
        ORDER BY frequency DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    print(f"\n✅ Found {len(results)} ESCO skills without embeddings")
    if results:
        print("\nSkills to process:")
        for skill, freq in results:
            print(f"   - {skill[:60]:60s} ({freq:,} mentions)")

    return results


def generate_and_save_embeddings(skills_with_freq):
    """
    Generate embeddings for skills and save to database.

    Args:
        skills_with_freq: List of (skill_text, frequency) tuples
    """
    if not skills_with_freq:
        print("\n✅ No missing embeddings to generate")
        return

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    print("\n" + "="*80)
    print("GENERATING EMBEDDINGS")
    print("="*80)

    # Load model
    model_name = "intfloat/multilingual-e5-base"
    print(f"\nLoading model: {model_name}")
    model = SentenceTransformer(model_name)

    # Extract just skill texts
    skills = [skill for skill, freq in skills_with_freq]

    # Generate embeddings
    print(f"\nGenerating embeddings for {len(skills)} skills...")
    embeddings = model.encode(
        skills,
        batch_size=128,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    print(f"\n✅ Embeddings generated: {embeddings.shape}")

    # Save to database
    print("\n" + "="*80)
    print("SAVING TO DATABASE")
    print("="*80)

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    inserted = 0
    updated = 0
    errors = 0

    for skill, embedding in tqdm(zip(skills, embeddings), total=len(skills), desc="Saving"):
        try:
            embedding_list = embedding.astype(np.float32).tolist()

            # Check if exists (shouldn't, but just in case)
            cursor.execute("""
                SELECT skill_text FROM skill_embeddings
                WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            """, (skill,))

            exists = cursor.fetchone()

            if exists:
                cursor.execute("""
                    UPDATE skill_embeddings
                    SET embedding = %s,
                        model_name = %s,
                        model_version = %s,
                        created_at = CURRENT_TIMESTAMP
                    WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
                """, (embedding_list, model_name, 'v1.0', skill))
                updated += 1
            else:
                cursor.execute("""
                    INSERT INTO skill_embeddings (
                        skill_text, embedding, model_name, model_version
                    ) VALUES (%s, %s, %s, %s)
                """, (skill, embedding_list, model_name, 'v1.0'))
                inserted += 1

        except Exception as e:
            errors += 1
            print(f"\n❌ Error with '{skill}': {e}")
            continue

    conn.commit()

    # Get new total
    cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
    total_in_db = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    print("\n" + "="*80)
    print("RESULTS")
    print("="*80)
    print(f"   Inserted:    {inserted:,}")
    print(f"   Updated:     {updated:,}")
    print(f"   Errors:      {errors:,}")
    print(f"   Total in DB: {total_in_db:,}")
    print()


def main():
    """Main execution."""
    print("\n" + "="*80)
    print("MISSING ESCO 30k EMBEDDINGS GENERATOR")
    print("="*80)
    print("Model: intfloat/multilingual-e5-base")
    print("Source: extracted_skills (NER + REGEX methods)")
    print("="*80)
    print()

    # Step 1: Find missing skills
    skills = get_missing_esco_skills()

    # Step 2: Generate and save embeddings
    generate_and_save_embeddings(skills)

    print("="*80)
    print("✅ PROCESS COMPLETE")
    print("="*80)
    print("\n🎯 Next step: Re-run clustering ESCO 30k")
    print("   python scripts/clustering_esco_30k_final.py")
    print()


if __name__ == '__main__':
    main()
