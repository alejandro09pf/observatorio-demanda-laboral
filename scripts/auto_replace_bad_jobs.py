#!/usr/bin/env python3
"""
Automatically replace bad jobs with better candidates.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from config.settings import get_settings
from collections import Counter

settings = get_settings()
db_url = settings.database_url
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgres://')

conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# 1. Identify jobs to remove
print("Step 1: Identifying bad jobs...")

bad_job_ids = []

# Duplicates
cursor.execute("""
    SELECT job_id, title, country, language
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
      AND (
          title ILIKE '%Desarrollador Fullstack / Certificados CEO%'
          OR title ILIKE '%ingeniero de sistemas junior%'
      )
""")
duplicates = cursor.fetchall()
bad_job_ids.extend([j[0] for j in duplicates])

# Manufacturing/hardware
manufacturing_patterns = [
    '%cajero%', '%manufactura%', '%molde%', '%equipment engineer%',
    '%seguridad e higiene%', '%aircraft maintenance%', '%ame engineer%'
]

for pattern in manufacturing_patterns:
    cursor.execute("""
        SELECT job_id FROM raw_jobs
        WHERE is_gold_standard = TRUE AND title ILIKE %s
    """, (pattern,))
    bad_job_ids.extend([r[0] for r in cursor.fetchall()])

# Non-tech
cursor.execute("""
    SELECT job_id FROM raw_jobs
    WHERE is_gold_standard = TRUE
      AND (
          title ILIKE '%Ingeniero AEI%'
          OR title ILIKE '%proyectista%'
          OR title ILIKE '%PROFESIONAL INGENIERO(A) CLIENTE%'
          OR title ILIKE '%Instructor%'
          OR title ILIKE '%ingeniero de producto%'
          OR title ILIKE '%ingeniero de proyectos%'
      )
""")
bad_job_ids.extend([r[0] for r in cursor.fetchall()])

# Deduplicate
bad_job_ids = list(set(bad_job_ids))

print(f"Found {len(bad_job_ids)} bad jobs to replace\n")

# 2. Get country/language distribution of bad jobs
# Convert UUIDs to strings for PostgreSQL array casting
bad_job_ids_str = [str(job_id) for job_id in bad_job_ids]
cursor.execute("""
    SELECT country, language, COUNT(*)
    FROM raw_jobs
    WHERE job_id = ANY(%s::uuid[])
    GROUP BY country, language
""", (bad_job_ids_str,))

# Build dict manually: {(country, lang): count}
replacements_needed = {}
for country, lang, count in cursor.fetchall():
    replacements_needed[(country, lang)] = count
print("Replacements needed by country/language:")
for (country, lang), count in replacements_needed.items():
    print(f"  {country} {lang}: {count} jobs")

# 3. Find replacement candidates
print("\nStep 2: Finding replacement candidates...")

replacements = []

for (country, lang), count in replacements_needed.items():
    cursor.execute("""
        SELECT job_id, title, description, requirements,
               LENGTH(description) + LENGTH(requirements) as total_len
        FROM raw_jobs
        WHERE country = %s
          AND language = %s
          AND is_usable = TRUE
          AND is_gold_standard = FALSE
          AND (LENGTH(description) + LENGTH(requirements)) > 1200
          -- Tech keywords
          AND (
              title ILIKE '%%developer%%' OR title ILIKE '%%engineer%%'
              OR title ILIKE '%%desarrollador%%' OR title ILIKE '%%programador%%'
              OR title ILIKE '%%devops%%' OR title ILIKE '%%backend%%'
              OR title ILIKE '%%frontend%%' OR title ILIKE '%%fullstack%%'
          )
          -- Exclude bad patterns
          AND title NOT ILIKE '%%manager%%'
          AND title NOT ILIKE '%%director%%'
          AND title NOT ILIKE '%%gerente%%'
          AND title NOT ILIKE '%%cajero%%'
          AND title NOT ILIKE '%%manufactura%%'
          AND title NOT ILIKE '%%molde%%'
          AND title NOT ILIKE '%%equipment%%'
          AND title NOT ILIKE '%%instructor%%'
          AND title NOT ILIKE '%%bi engineer%%'
        ORDER BY total_len DESC
        LIMIT %s
    """, (country, lang, count + 5))  # Get a few extra as backup

    candidates = cursor.fetchall()

    print(f"  Found {len(candidates)} candidates for {country} {lang} (need {count})")

    for job_id, title, desc, req, total_len in candidates[:count]:
        replacements.append({
            'job_id': job_id,
            'title': title,
            'country': country,
            'language': lang,
            'length': total_len
        })

print(f"\nTotal replacements ready: {len(replacements)}")

# 4. Execute replacement
print("\nStep 3: Executing replacement...")

# Remove bad jobs from gold standard
cursor.execute("""
    UPDATE raw_jobs
    SET is_gold_standard = FALSE,
        gold_standard_role_type = NULL,
        gold_standard_seniority = NULL
    WHERE job_id = ANY(%s::uuid[])
""", (bad_job_ids_str,))

print(f"  Removed {len(bad_job_ids)} bad jobs from gold standard")

# Add replacements (with default role classification)
for repl in replacements:
    # Simple role classification based on title
    title_lower = repl['title'].lower()

    if 'backend' in title_lower or 'back-end' in title_lower:
        role = 'backend'
    elif 'frontend' in title_lower or 'front-end' in title_lower:
        role = 'frontend'
    elif 'fullstack' in title_lower or 'full-stack' in title_lower or 'full stack' in title_lower:
        role = 'fullstack'
    elif 'mobile' in title_lower or 'ios' in title_lower or 'android' in title_lower:
        role = 'mobile'
    elif 'devops' in title_lower or 'sre' in title_lower:
        role = 'devops'
    elif 'data' in title_lower or 'ml' in title_lower or 'machine learning' in title_lower:
        role = 'data_science'
    elif 'qa' in title_lower or 'test' in title_lower:
        role = 'qa'
    elif 'security' in title_lower or 'cybersecurity' in title_lower:
        role = 'security'
    else:
        role = 'backend'  # Default

    # Simple seniority
    if 'senior' in title_lower or 'sr.' in title_lower or 'lead' in title_lower:
        seniority = 'senior'
    elif 'junior' in title_lower or 'jr.' in title_lower:
        seniority = 'junior'
    else:
        seniority = 'mid'

    cursor.execute("""
        UPDATE raw_jobs
        SET is_gold_standard = TRUE,
            gold_standard_role_type = %s,
            gold_standard_seniority = %s
        WHERE job_id = %s
    """, (role, seniority, repl['job_id']))

print(f"  Added {len(replacements)} replacement jobs to gold standard")

conn.commit()

# 5. Verify
cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE")
total = cursor.fetchone()[0]

print(f"\n{'='*80}")
print(f"REPLACEMENT COMPLETE")
print(f"{'='*80}")
print(f"Total gold standard jobs: {total}")
print(f"Expected: 300")

if total == 300:
    print("✅ Perfect count!")
else:
    print(f"⚠️  Count mismatch: {total} vs 300")

# Show distribution
cursor.execute("""
    SELECT country, language, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY country, language
    ORDER BY country, language
""")

print("\nDistribution by country/language:")
for country, lang, count in cursor.fetchall():
    print(f"  {country} {lang}: {count}")

cursor.close()
conn.close()

print("\n✅ Done!")
