#!/usr/bin/env python3
"""Clean the 12 gold standard jobs that are missing from cleaned_jobs"""

import re
import html
import psycopg2

DB_PARAMS = {
    'host': '127.0.0.1',
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456',
}

def remove_html_tags(text: str) -> str:
    """Remove all HTML tags and decode HTML entities."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    return text

def normalize_whitespace(text: str) -> str:
    """Normalize whitespace"""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    return text

def clean_job_text(text: str) -> str:
    """Clean job text: remove HTML, normalize whitespace"""
    text = remove_html_tags(text)
    text = normalize_whitespace(text)
    return text

# Connect
conn = psycopg2.connect(**DB_PARAMS)
cursor = conn.cursor()

# Get uncleaned gold standard jobs
cursor.execute("""
    SELECT r.job_id, r.title, r.description, r.requirements
    FROM raw_jobs r
    LEFT JOIN cleaned_jobs c ON r.job_id = c.job_id
    WHERE r.is_gold_standard = TRUE
      AND c.job_id IS NULL
""")

jobs = cursor.fetchall()
print(f"Limpiando {len(jobs)} gold standard jobs...\n")

for job_id, title, description, requirements in jobs:
    # Clean
    title_cleaned = clean_job_text(title) if title else ""
    desc_cleaned = clean_job_text(description) if description else ""
    req_cleaned = clean_job_text(requirements) if requirements else ""

    combined = f"{title_cleaned}\n{desc_cleaned}\n{req_cleaned}".strip()
    word_count = len(combined.split())

    # Insert
    cursor.execute("""
        INSERT INTO cleaned_jobs (
            job_id, title_cleaned, description_cleaned,
            requirements_cleaned, combined_text, combined_word_count
        ) VALUES (%s, %s, %s, %s, %s, %s)
    """, (job_id, title_cleaned, desc_cleaned, req_cleaned, combined, word_count))

    # Note: raw_jobs doesn't have cleaning_status column

    print(f"✅ {title[:60]}... ({word_count} palabras)")

conn.commit()
print(f"\n✅ {len(jobs)} jobs limpiados!")

# Verify
cursor.execute("""
    SELECT COUNT(*)
    FROM raw_jobs r
    LEFT JOIN cleaned_jobs c ON r.job_id = c.job_id
    WHERE r.is_gold_standard = TRUE
      AND c.job_id IS NULL
""")

remaining = cursor.fetchone()[0]
print(f"Remaining uncleaned: {remaining}")

cursor.close()
conn.close()
