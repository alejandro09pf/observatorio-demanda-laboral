#!/usr/bin/env python3
"""
Import Alejandro's 33K job ads from CSV to database.

Checks for duplicates and only imports new jobs.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import csv
import psycopg2
from datetime import datetime
from config.settings import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def import_jobs_from_csv(csv_path: str):
    """Import jobs from CSV, skipping duplicates."""

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Get existing job_ids to skip duplicates
    logger.info("Loading existing job_ids from database...")
    cursor.execute("SELECT job_id FROM raw_jobs")
    existing_ids = {row[0] for row in cursor.fetchall()}
    logger.info(f"Found {len(existing_ids)} existing jobs in database")

    # Read CSV and import
    imported = 0
    skipped = 0
    errors = 0

    logger.info(f"Reading CSV from {csv_path}...")

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for idx, row in enumerate(reader, 1):
            job_id = row['job_id']

            # Skip if already exists
            if job_id in existing_ids:
                skipped += 1
                if skipped % 1000 == 0:
                    logger.info(f"  Skipped {skipped} duplicates...")
                continue

            try:
                # Parse dates
                posted_date = row['posted_date'] if row['posted_date'] else None
                scraped_at = row['scraped_at'] if row['scraped_at'] else datetime.now()

                # Insert into raw_jobs
                cursor.execute("""
                    INSERT INTO raw_jobs (
                        job_id, portal, country, url, title, company, location,
                        description, requirements, salary_raw, contract_type,
                        remote_type, posted_date, scraped_at, content_hash,
                        is_usable, extraction_status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        TRUE, 'pending'
                    )
                """, (
                    job_id, row['portal'], row['country'], row['url'], row['title'],
                    row['company'], row['location'], row['description'],
                    row['requirements'], row['salary_raw'], row['contract_type'],
                    row['remote_type'], posted_date, scraped_at, row['content_hash']
                ))

                imported += 1

                if imported % 1000 == 0:
                    conn.commit()
                    logger.info(f"  Imported {imported} new jobs...")

            except Exception as e:
                logger.error(f"Error importing job {job_id}: {e}")
                errors += 1
                if errors > 100:
                    logger.error("Too many errors, stopping import")
                    break

    # Final commit
    conn.commit()
    cursor.close()
    conn.close()

    logger.info("\n" + "="*60)
    logger.info(f"IMPORT COMPLETE")
    logger.info(f"  Imported: {imported} new jobs")
    logger.info(f"  Skipped:  {skipped} duplicates")
    logger.info(f"  Errors:   {errors}")
    logger.info("="*60)

    return {'imported': imported, 'skipped': skipped, 'errors': errors}


if __name__ == "__main__":
    csv_file = "ofertas_completas_33k.csv"

    if not Path(csv_file).exists():
        logger.error(f"CSV file not found: {csv_file}")
        sys.exit(1)

    results = import_jobs_from_csv(csv_file)

    if results['errors'] > 0:
        sys.exit(1)
