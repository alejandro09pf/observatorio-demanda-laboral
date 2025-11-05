"""
ETL Cleaning Script for Raw Job Postings

This script implements the ETL cleaning strategy documented in:
docs/ETL_STRATEGY_AND_DECISIONS.md

Features:
1. Junk detection and filtering (is_usable flag)
2. HTML tag removal and text normalization
3. Combined text generation (title + description + requirements)
4. Metadata statistics (word count, character count)
5. Storage in cleaned_jobs table

Usage:
    python scripts/clean_raw_jobs.py [--batch-size 1000] [--portal hiring_cafe] [--country CO]
"""

import re
import html
import hashlib
import argparse
import psycopg2
from datetime import datetime
from typing import Optional, Dict, Tuple

# Database connection parameters
DB_PARAMS = {
    'host': '127.0.0.1',
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456',
}

# ============================================================================
# JUNK DETECTION PATTERNS
# ============================================================================

JUNK_PATTERNS = [
    r'^test$',                      # Exact "test"
    r'^demo$',                      # Exact "demo"
    r'^\d{3}_cand',                 # "002_Cand1" pattern
    r'^(colombia|mexico|argentina)\s+(credo\s+)?test\s+\d+$',  # "Colombia Test 7"
]

def is_junk_job(title: str, description: str) -> Tuple[bool, Optional[str]]:
    """
    Detect if a job is junk/test data.

    Returns:
        (is_junk: bool, reason: str)
    """
    # Empty or extremely short description (very conservative threshold)
    if not description or len(description.strip()) < 50:
        return True, "Empty or extremely short description"

    # Check title patterns (case-insensitive)
    title_lower = title.lower().strip()

    for pattern in JUNK_PATTERNS:
        if re.match(pattern, title_lower):
            return True, f"Test job pattern: {pattern}"

    return False, None


# ============================================================================
# TEXT CLEANING FUNCTIONS
# ============================================================================

def remove_html_tags(text: str) -> str:
    """Remove all HTML tags and decode HTML entities."""
    if not text:
        return ""

    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', text)

    # Decode HTML entities (&nbsp; → space, &amp; → &, etc.)
    text = html.unescape(text)

    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace (multiple spaces → single space, trim)."""
    if not text:
        return ""

    # Replace multiple whitespace (including newlines, tabs) with single space
    text = re.sub(r'\s+', ' ', text)

    # Trim leading/trailing whitespace
    text = text.strip()

    return text


def remove_excessive_punctuation(text: str) -> str:
    """Remove excessive punctuation (!!!, ???, etc.)."""
    if not text:
        return ""

    # Replace multiple exclamation/question marks with single one
    text = re.sub(r'([!?]){2,}', r'\1', text)

    return text


def remove_emojis(text: str) -> str:
    """Remove emojis and other Unicode symbols."""
    if not text:
        return ""

    # Remove emojis (Unicode ranges)
    text = re.sub(r'[\U00010000-\U0010ffff]', '', text, flags=re.UNICODE)

    # Remove other common emoji ranges
    text = re.sub(r'[\u2600-\u26FF\u2700-\u27BF]', '', text)

    return text


def clean_title(title: str) -> str:
    """
    Clean job title:
    1. Remove HTML tags
    2. Remove emojis
    3. Remove excessive punctuation
    4. Normalize whitespace
    5. Keep original case (helps NER)
    """
    if not title:
        return ""

    text = title
    text = remove_html_tags(text)
    text = remove_emojis(text)
    text = remove_excessive_punctuation(text)
    text = normalize_whitespace(text)

    return text


def clean_description_or_requirements(text: str) -> str:
    """
    Clean description or requirements:
    1. Remove HTML tags
    2. Normalize whitespace
    3. Keep accents, case, meaningful punctuation
    """
    if not text:
        return ""

    text = remove_html_tags(text)
    text = normalize_whitespace(text)

    return text


def create_combined_text(title: str, description: str, requirements: str) -> str:
    """
    Create combined text for extraction.
    Format: title\ndescription\nrequirements
    """
    parts = []

    if title:
        parts.append(title)
    if description:
        parts.append(description)
    if requirements:
        parts.append(requirements)

    return "\n".join(parts)


def calculate_statistics(text: str) -> Dict[str, int]:
    """Calculate word count and character count."""
    if not text:
        return {'word_count': 0, 'char_count': 0}

    words = text.split()
    return {
        'word_count': len(words),
        'char_count': len(text)
    }


# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def connect_db():
    """Connect to PostgreSQL database."""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None


def fetch_raw_jobs(cursor, batch_size: int = 1000, portal: Optional[str] = None,
                   country: Optional[str] = None):
    """
    Fetch raw jobs that need cleaning.

    Only fetches jobs that:
    - Don't have a cleaned_jobs record yet
    - Have title and description
    """
    query = """
        SELECT r.job_id, r.title, r.description, r.requirements
        FROM raw_jobs r
        LEFT JOIN cleaned_jobs c ON r.job_id = c.job_id
        WHERE c.job_id IS NULL  -- Not yet cleaned
          AND r.is_usable = TRUE  -- Only usable jobs
          AND r.is_duplicate = FALSE  -- Exclude semantic duplicates
          AND r.title IS NOT NULL
          AND r.description IS NOT NULL
    """

    params = []

    if portal:
        query += " AND r.portal = %s"
        params.append(portal)

    if country:
        query += " AND r.country = %s"
        params.append(country)

    query += " ORDER BY r.scraped_at DESC LIMIT %s"
    params.append(batch_size)

    cursor.execute(query, params)
    return cursor.fetchall()


def mark_as_junk(cursor, job_id: str, reason: str):
    """Mark a job as unusable (junk)."""
    cursor.execute("""
        UPDATE raw_jobs
        SET is_usable = FALSE,
            unusable_reason = %s
        WHERE job_id = %s
    """, (reason, job_id))


def insert_cleaned_job(cursor, job_id: str, title_cleaned: str,
                      description_cleaned: str, requirements_cleaned: str,
                      combined_text: str, combined_word_count: int,
                      combined_char_count: int):
    """Insert cleaned job into cleaned_jobs table."""
    cursor.execute("""
        INSERT INTO cleaned_jobs (
            job_id,
            title_cleaned,
            description_cleaned,
            requirements_cleaned,
            combined_text,
            cleaning_method,
            cleaned_at,
            combined_word_count,
            combined_char_count
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (job_id) DO UPDATE SET
            title_cleaned = EXCLUDED.title_cleaned,
            description_cleaned = EXCLUDED.description_cleaned,
            requirements_cleaned = EXCLUDED.requirements_cleaned,
            combined_text = EXCLUDED.combined_text,
            cleaning_method = EXCLUDED.cleaning_method,
            cleaned_at = EXCLUDED.cleaned_at,
            combined_word_count = EXCLUDED.combined_word_count,
            combined_char_count = EXCLUDED.combined_char_count
    """, (
        job_id,
        title_cleaned,
        description_cleaned,
        requirements_cleaned,
        combined_text,
        'html_strip',
        datetime.now(),
        combined_word_count,
        combined_char_count
    ))


# ============================================================================
# MAIN ETL PROCESS
# ============================================================================

def clean_raw_jobs(batch_size: int = 1000, portal: Optional[str] = None,
                   country: Optional[str] = None):
    """
    Main ETL cleaning process.

    For each job:
    1. Check if junk → mark is_usable=FALSE if junk
    2. Clean title → title_cleaned
    3. Clean description → description_cleaned
    4. Clean requirements → requirements_cleaned
    5. Combine → combined_text
    6. Calculate statistics
    7. INSERT INTO cleaned_jobs
    """
    conn = connect_db()
    if not conn:
        return

    cursor = conn.cursor()

    print("\n" + "="*80)
    print("ETL CLEANING PROCESS")
    print("="*80 + "\n")

    # Statistics for THIS RUN ONLY
    total_processed = 0
    junk_count = 0
    cleaned_count = 0
    batch_num = 0

    while True:
        # Fetch batch
        jobs = fetch_raw_jobs(cursor, batch_size, portal, country)

        if not jobs:
            print("✅ No more jobs to clean!")
            break

        batch_num += 1
        batch_junk = 0
        batch_cleaned = 0

        print(f"📦 Batch {batch_num}: Processing {len(jobs)} jobs...")

        for job_id, title, description, requirements in jobs:
            total_processed += 1

            # Step 1: Check if junk
            is_junk, junk_reason = is_junk_job(title, description)

            if is_junk:
                mark_as_junk(cursor, job_id, junk_reason)
                junk_count += 1
                batch_junk += 1
                continue  # Don't clean junk jobs

            # Step 2-4: Clean individual fields
            title_cleaned = clean_title(title)
            description_cleaned = clean_description_or_requirements(description)
            requirements_cleaned = clean_description_or_requirements(requirements or "")

            # Step 5: Create combined text
            combined_text = create_combined_text(
                title_cleaned,
                description_cleaned,
                requirements_cleaned
            )

            # Step 6: Calculate statistics
            stats = calculate_statistics(combined_text)

            # Step 7: Insert into cleaned_jobs
            insert_cleaned_job(
                cursor,
                job_id,
                title_cleaned,
                description_cleaned,
                requirements_cleaned,
                combined_text,
                stats['word_count'],
                stats['char_count']
            )

            cleaned_count += 1
            batch_cleaned += 1

        # Commit batch
        conn.commit()
        print(f"   ✅ Cleaned: {batch_cleaned} | 🗑️  Junk: {batch_junk} | Total so far: {cleaned_count} cleaned, {junk_count} junk\n")

    # Final statistics
    print("\n" + "="*80)
    print("ETL CLEANING SUMMARY (THIS RUN)")
    print("="*80)
    print(f"Total jobs processed:     {total_processed:,}")
    print(f"✅ Cleaned jobs:          {cleaned_count:,}")
    print(f"🗑️  Junk jobs flagged:     {junk_count:,}")
    if total_processed > 0:
        print(f"📊 Usable percentage:     {(cleaned_count/total_processed*100):.2f}%")
    print("="*80 + "\n")

    # Show cleaning stats from database
    cursor.execute("SELECT * FROM get_cleaning_stats()")
    stats = cursor.fetchall()

    print("DATABASE STATISTICS:")
    print("-" * 60)
    for metric, value in stats:
        print(f"{metric:<25} {value:>10,}")
    print("-" * 60 + "\n")

    conn.close()


# ============================================================================
# CLI
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Clean raw job postings and populate cleaned_jobs table"
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=1000,
        help='Number of jobs to process per batch (default: 1000)'
    )
    parser.add_argument(
        '--portal',
        type=str,
        help='Filter by portal (e.g., hiring_cafe, bumeran)'
    )
    parser.add_argument(
        '--country',
        type=str,
        help='Filter by country (e.g., CO, MX, AR)'
    )

    args = parser.parse_args()

    print("\n🧹 Starting ETL cleaning process...")

    if args.portal:
        print(f"   Portal filter: {args.portal}")
    if args.country:
        print(f"   Country filter: {args.country}")

    print(f"   Batch size: {args.batch_size}\n")

    clean_raw_jobs(
        batch_size=args.batch_size,
        portal=args.portal,
        country=args.country
    )

    print("✅ ETL cleaning complete!\n")


if __name__ == "__main__":
    main()
