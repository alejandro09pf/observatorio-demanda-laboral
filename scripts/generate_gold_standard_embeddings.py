#!/usr/bin/env python3
"""
Generate embeddings for unique skills from gold_standard_annotations.

This script fills the gap between ESCO/O*NET embeddings and real market skills.
- Gold standard: 1,914 hard skills + 306 soft skills = 2,220 unique skills
- Existing embeddings: ~186 matches (9.7%)
- Missing embeddings: ~2,034 skills (90.3%)

Usage:
    python scripts/generate_gold_standard_embeddings.py --skill-type hard
    python scripts/generate_gold_standard_embeddings.py --skill-type soft
    python scripts/generate_gold_standard_embeddings.py --skill-type both
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
    """
    Normalize skill text before generating embeddings.

    Rules:
    1. Strip whitespace
    2. Normalize to consistent case (keep original for tech terms)
    3. Remove extra spaces
    4. Handle common variations

    Args:
        skill_text: Original skill text

    Returns:
        Normalized skill text
    """
    # Strip whitespace
    normalized = skill_text.strip()

    # Remove extra internal spaces
    normalized = ' '.join(normalized.split())

    # Common normalizations for consistency
    # (Keep most as-is to preserve how they appear in job postings)
    replacements = {
        'ci/cd': 'CI/CD',
        'Ci/Cd': 'CI/CD',
        'api': 'API',
        'rest api': 'REST API',
        'restful api': 'REST API',
        'graphql': 'GraphQL',
        'javascript': 'JavaScript',
        'typescript': 'TypeScript',
        'nodejs': 'Node.js',
        'node.js': 'Node.js',
        'reactjs': 'React',
        'react.js': 'React',
        'vuejs': 'Vue.js',
        'vue.js': 'Vue.js',
        'angularjs': 'Angular',
        'aws': 'AWS',
        'gcp': 'GCP',
        'sql': 'SQL',
        'nosql': 'NoSQL',
        'mongodb': 'MongoDB',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
    }

    # Check lowercase version for replacements
    normalized_lower = normalized.lower()
    for old, new in replacements.items():
        if normalized_lower == old.lower():
            normalized = new
            break

    return normalized


def load_gold_standard_skills(
    skill_type: str = 'both',
    exclude_existing: bool = True
) -> List[Tuple[str, str, str]]:
    """
    Load unique skills from gold_standard_annotations.

    Args:
        skill_type: 'hard', 'soft', or 'both'
        exclude_existing: If True, exclude skills that already have embeddings

    Returns:
        List of (original_text, normalized_text, skill_type) tuples
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Build WHERE clause for skill type
    if skill_type == 'hard':
        type_filter = "gs.skill_type = 'hard'"
    elif skill_type == 'soft':
        type_filter = "gs.skill_type = 'soft'"
    else:  # both
        type_filter = "gs.skill_type IN ('hard', 'soft')"

    # Query to get unique skills
    if exclude_existing:
        query = f"""
            SELECT DISTINCT gs.skill_text, gs.skill_type
            FROM gold_standard_annotations gs
            LEFT JOIN skill_embeddings se
                ON LOWER(TRIM(gs.skill_text)) = LOWER(TRIM(se.skill_text))
            WHERE {type_filter}
              AND se.skill_text IS NULL
            ORDER BY gs.skill_text
        """
    else:
        query = f"""
            SELECT DISTINCT skill_text, skill_type
            FROM gold_standard_annotations
            WHERE {type_filter}
            ORDER BY skill_text
        """

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    # Normalize and prepare skills
    skills = []
    seen = set()

    for original_text, stype in results:
        normalized_text = normalize_skill_text(original_text)

        # Avoid duplicates after normalization
        if normalized_text.lower() not in seen:
            skills.append((original_text, normalized_text, stype))
            seen.add(normalized_text.lower())

    return skills


def generate_embeddings(
    skills: List[Tuple[str, str, str]],
    model_name: str = "intfloat/multilingual-e5-base",
    batch_size: int = 32
) -> Tuple[List[str], List[str], np.ndarray]:
    """
    Generate embeddings for normalized skills.

    Args:
        skills: List of (original, normalized, type) tuples
        model_name: HuggingFace model identifier
        batch_size: Batch size for encoding

    Returns:
        (original_texts, normalized_texts, embeddings)
    """
    print(f"\n{'='*70}")
    print(f"LOADING MODEL: {model_name}")
    print(f"{'='*70}")

    # Load model
    model = SentenceTransformer(model_name)

    # Extract texts
    original_texts = [s[0] for s in skills]
    normalized_texts = [s[1] for s in skills]
    skill_types = [s[2] for s in skills]

    print(f"\n📊 Skills to embed: {len(normalized_texts):,}")
    print(f"   Batch size: {batch_size}")
    print(f"   Expected batches: {(len(normalized_texts) + batch_size - 1) // batch_size}")

    # Show normalization examples
    print(f"\n🔍 Normalization examples:")
    for i in range(min(10, len(skills))):
        orig = original_texts[i]
        norm = normalized_texts[i]
        stype = skill_types[i]
        if orig != norm:
            print(f"   [{stype}] '{orig}' → '{norm}'")
        else:
            print(f"   [{stype}] '{orig}' (no change)")

    if len(skills) > 10:
        print(f"   ... and {len(skills) - 10} more")

    print(f"\n🚀 Generating embeddings...")

    # Generate embeddings with progress bar
    embeddings = model.encode(
        normalized_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True  # L2 normalization for cosine similarity
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
    model_version: str = "v1.0",
    source: str = "gold_standard"
) -> Dict[str, int]:
    """
    Save embeddings to skill_embeddings table.

    Uses normalized_text as skill_text (the canonical form).
    Tracks original_text in metadata if different.

    Args:
        original_texts: Original skill texts
        normalized_texts: Normalized skill texts (used as skill_text)
        embeddings: Numpy array of embeddings
        model_name: Model identifier
        model_version: Model version
        source: Source of skills (for tracking)

    Returns:
        Stats dict with inserted, updated, skipped, errors
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
    print(f"   Total embeddings: {len(normalized_texts):,}")
    print(f"   Source: {source}")
    print()

    inserted = 0
    updated = 0
    skipped = 0
    errors = 0

    for orig_text, norm_text, embedding in tqdm(
        zip(original_texts, normalized_texts, embeddings),
        total=len(normalized_texts),
        desc="Inserting embeddings"
    ):
        try:
            # Convert numpy array to Python list
            embedding_list = embedding.astype(np.float32).tolist()

            # Check if exists
            cursor.execute("""
                SELECT skill_text FROM skill_embeddings
                WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            """, (norm_text,))

            exists = cursor.fetchone()

            if exists:
                # Update existing
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
                # Insert new
                cursor.execute("""
                    INSERT INTO skill_embeddings (
                        skill_text, embedding, model_name, model_version
                    ) VALUES (%s, %s, %s, %s)
                """, (norm_text, embedding_list, model_name, model_version))
                inserted += 1

            # Commit every 100 records
            if (inserted + updated) % 100 == 0:
                conn.commit()

        except Exception as e:
            errors += 1
            print(f"\n❌ Error with '{orig_text}' → '{norm_text}': {e}")
            continue

    # Final commit
    conn.commit()

    # Verify count
    cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
    total_in_db = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    stats = {
        'inserted': inserted,
        'updated': updated,
        'skipped': skipped,
        'errors': errors,
        'total_in_db': total_in_db
    }

    print(f"\n{'='*70}")
    print(f"✅ EMBEDDINGS SAVED")
    print(f"{'='*70}")
    print(f"   Inserted:    {inserted:,}")
    print(f"   Updated:     {updated:,}")
    print(f"   Skipped:     {skipped:,}")
    print(f"   Errors:      {errors:,}")
    print(f"   Total in DB: {total_in_db:,}")
    print()

    return stats


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Generate embeddings for gold standard skills"
    )
    parser.add_argument(
        '--skill-type',
        type=str,
        choices=['hard', 'soft', 'both'],
        default='hard',
        help="Type of skills to process (default: hard)"
    )
    parser.add_argument(
        '--include-existing',
        action='store_true',
        help="Include skills that already have embeddings (will update them)"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help="Batch size for encoding (default: 32)"
    )

    args = parser.parse_args()

    print("="*70)
    print("GOLD STANDARD EMBEDDINGS GENERATOR")
    print("="*70)
    print(f"Skill type:       {args.skill_type}")
    print(f"Include existing: {args.include_existing}")
    print(f"Batch size:       {args.batch_size}")
    print(f"Model:            intfloat/multilingual-e5-base")
    print()

    # Step 1: Load skills
    print("📂 Loading skills from gold_standard_annotations...")
    skills = load_gold_standard_skills(
        skill_type=args.skill_type,
        exclude_existing=not args.include_existing
    )
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
        embeddings,
        source=f"gold_standard_{args.skill_type}"
    )

    # Final summary
    print("="*70)
    print("✅ PROCESS COMPLETE")
    print("="*70)
    print(f"   Skills processed: {len(skills):,}")
    print(f"   Inserted:         {stats['inserted']:,}")
    print(f"   Updated:          {stats['updated']:,}")
    print(f"   Errors:           {stats['errors']:,}")
    print(f"   Total in DB:      {stats['total_in_db']:,}")
    print()

    if stats['errors'] > 0:
        print("⚠️  Some errors occurred. Check output above for details.")

    print("🎯 Next step: Select subset for clustering prototype")
    print("   python scripts/select_clustering_subset.py --limit 400")
    print()


if __name__ == '__main__':
    main()
