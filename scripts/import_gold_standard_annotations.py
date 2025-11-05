#!/usr/bin/env python3
"""
Import Gold Standard Annotations from MD file to Database

This script parses ANOTACION_MANUAL_300.md and imports manually annotated skills
into the gold_standard_annotations table for pipeline evaluation.

Usage:
    python scripts/import_gold_standard_annotations.py [--dry-run] [--batch-size N]
"""

import sys
from pathlib import Path
import re
import psycopg2
from psycopg2.extras import execute_batch
import argparse
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from config.settings import get_settings

# Constants
MD_FILE_PATH = Path(__file__).parent.parent / 'data' / 'gold_standard' / 'ANOTACION_MANUAL_300.md'


def parse_annotations_from_md(md_path: Path) -> list[dict]:
    """
    Parse the gold standard MD file and extract all annotations.

    Returns:
        List of dicts with: job_id, hard_skills (list), soft_skills (list), notes
    """

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Pattern to match each job section
    job_pattern = re.compile(
        r'## Job #(\d+)/300\s+'
        r'\*\*Job ID\*\*: `([^`]+)`\s+'
        r'.*?'
        r'### Anotación\s+'
        r'- \[x\] \*\*Es software/tech job válido\*\*\s+'
        r'\*\*Hard Skills\*\*:\s*```\s*(.*?)\s*```\s+'
        r'\*\*Soft Skills\*\*:\s*```\s*(.*?)\s*```\s+'
        r'\*\*Comentarios\*\*:\s*```\s*(.*?)\s*```',
        re.DOTALL
    )

    jobs = []
    for match in job_pattern.finditer(content):
        job_num, job_id, hard_skills_raw, soft_skills_raw, notes = match.groups()

        # Parse hard skills (one per line, trim whitespace)
        hard_skills = [
            skill.strip()
            for skill in hard_skills_raw.strip().split('\n')
            if skill.strip() and not skill.strip().startswith('(PENDIENTE')
        ]

        # Parse soft skills (one per line, trim whitespace)
        soft_skills = [
            skill.strip()
            for skill in soft_skills_raw.strip().split('\n')
            if skill.strip() and not skill.strip().startswith('(PENDIENTE')
        ]

        # Clean notes
        notes_clean = notes.strip() if not notes.strip().startswith('(PENDIENTE') else None

        jobs.append({
            'job_num': int(job_num),
            'job_id': job_id,
            'hard_skills': hard_skills,
            'soft_skills': soft_skills,
            'notes': notes_clean
        })

    return jobs


def validate_job_exists(cursor, job_id: str) -> bool:
    """Check if job_id exists in raw_jobs table"""
    cursor.execute(
        "SELECT EXISTS(SELECT 1 FROM raw_jobs WHERE job_id = %s)",
        (job_id,)
    )
    return cursor.fetchone()[0]


def import_annotations(
    annotations: list[dict],
    db_url: str,
    dry_run: bool = False,
    batch_size: int = 500
):
    """
    Import annotations into gold_standard_annotations table.

    Args:
        annotations: List of parsed annotations
        db_url: Database connection string
        dry_run: If True, only show what would be imported without writing to DB
        batch_size: Number of records to insert in each batch
    """

    # Normalize db_url for psycopg2
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    try:
        # Statistics
        total_jobs = len(annotations)
        total_hard_skills = sum(len(job['hard_skills']) for job in annotations)
        total_soft_skills = sum(len(job['soft_skills']) for job in annotations)
        total_skills = total_hard_skills + total_soft_skills

        print(f"\n{'='*70}")
        print(f"  Gold Standard Annotation Import")
        print(f"{'='*70}")
        print(f"  Total jobs to process: {total_jobs}")
        print(f"  Total hard skills: {total_hard_skills:,}")
        print(f"  Total soft skills: {total_soft_skills:,}")
        print(f"  Total skills: {total_skills:,}")
        print(f"  Mode: {'DRY RUN (no changes)' if dry_run else 'LIVE (will modify database)'}")
        print(f"{'='*70}\n")

        if dry_run:
            print("DRY RUN MODE - Showing first 5 jobs:\n")
            for job in annotations[:5]:
                print(f"Job #{job['job_num']} ({job['job_id'][:8]}...):")
                print(f"  Hard skills ({len(job['hard_skills'])}): {', '.join(job['hard_skills'][:5])}...")
                print(f"  Soft skills ({len(job['soft_skills'])}): {', '.join(job['soft_skills'][:3])}...")
                print(f"  Notes: {job['notes'][:80] if job['notes'] else 'None'}...")
                print()
            return

        # Clear existing annotations (fresh import)
        cursor.execute("DELETE FROM gold_standard_annotations")
        deleted_count = cursor.rowcount
        print(f"✓ Cleared {deleted_count} existing annotations\n")

        # Prepare batch insert
        insert_query = """
            INSERT INTO gold_standard_annotations
            (job_id, skill_text, skill_type, annotator, notes)
            VALUES (%s, %s, %s, %s, %s)
        """

        batch_data = []
        jobs_processed = 0
        jobs_skipped = 0
        skills_inserted = 0

        for job in annotations:
            # Validate job exists
            if not validate_job_exists(cursor, job['job_id']):
                print(f"⚠ Warning: Job #{job['job_num']} ({job['job_id'][:8]}...) not found in raw_jobs - skipping")
                jobs_skipped += 1
                continue

            # Add hard skills
            for skill in job['hard_skills']:
                batch_data.append((
                    job['job_id'],
                    skill,
                    'hard',
                    'manual',
                    job['notes']
                ))

            # Add soft skills
            for skill in job['soft_skills']:
                batch_data.append((
                    job['job_id'],
                    skill,
                    'soft',
                    'manual',
                    job['notes']
                ))

            jobs_processed += 1

            # Insert in batches
            if len(batch_data) >= batch_size:
                execute_batch(cursor, insert_query, batch_data)
                skills_inserted += len(batch_data)
                print(f"  Inserted {len(batch_data)} skills (jobs: {jobs_processed}/{total_jobs})")
                batch_data = []

        # Insert remaining
        if batch_data:
            execute_batch(cursor, insert_query, batch_data)
            skills_inserted += len(batch_data)
            print(f"  Inserted {len(batch_data)} skills (jobs: {jobs_processed}/{total_jobs})")

        # Commit transaction
        conn.commit()

        # Final statistics
        cursor.execute("SELECT COUNT(*) FROM gold_standard_annotations")
        final_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(DISTINCT job_id) FROM gold_standard_annotations")
        unique_jobs = cursor.fetchone()[0]

        cursor.execute("SELECT skill_type, COUNT(*) FROM gold_standard_annotations GROUP BY skill_type")
        skill_type_counts = dict(cursor.fetchall())

        print(f"\n{'='*70}")
        print(f"  Import Complete!")
        print(f"{'='*70}")
        print(f"  Jobs processed: {jobs_processed}")
        print(f"  Jobs skipped: {jobs_skipped}")
        print(f"  Skills inserted: {skills_inserted:,}")
        print(f"  Skills in DB (verified): {final_count:,}")
        print(f"  Unique jobs in DB: {unique_jobs}")
        print(f"  Hard skills: {skill_type_counts.get('hard', 0):,}")
        print(f"  Soft skills: {skill_type_counts.get('soft', 0):,}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description='Import gold standard annotations from MD to database'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be imported without modifying database'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=500,
        help='Number of records to insert per batch (default: 500)'
    )
    parser.add_argument(
        '--md-file',
        type=Path,
        default=MD_FILE_PATH,
        help='Path to ANOTACION_MANUAL_300.md file'
    )

    args = parser.parse_args()

    # Check MD file exists
    if not args.md_file.exists():
        print(f"❌ Error: MD file not found: {args.md_file}")
        sys.exit(1)

    # Parse annotations
    print(f"📖 Parsing annotations from: {args.md_file}")
    annotations = parse_annotations_from_md(args.md_file)
    print(f"✓ Parsed {len(annotations)} jobs with annotations\n")

    if len(annotations) == 0:
        print("❌ No annotations found in MD file")
        sys.exit(1)

    # Get database URL
    settings = get_settings()

    # Import
    import_annotations(
        annotations,
        settings.database_url,
        dry_run=args.dry_run,
        batch_size=args.batch_size
    )


if __name__ == '__main__':
    main()
