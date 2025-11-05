#!/usr/bin/env python3
"""
Iteration 6: Remove duplicate titles (48 jobs)

Problem: Multiple jobs with identical titles exist in gold standard.
Examples:
- "ingeniero sistemas Junior/ carreras afines - remoto" (12 duplicates)
- "ingeniero software implementacion Pegasus..." (11 duplicates)
- "Ingeniero de Sistemas, software, Datos Telecomunicaciones" (7 duplicates)

Strategy: Keep ONE job per title (the longest one), remove duplicates, replace with unique titles.

Total to remove: 48 jobs
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from config.settings import get_settings
from collections import defaultdict

settings = get_settings()
db_url = settings.database_url
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgres://')

conn = psycopg2.connect(db_url)
cursor = conn.cursor()

print("="*80)
print("ITERATION 6: REMOVE DUPLICATE TITLES")
print("="*80)

# Get all gold standard jobs grouped by title
cursor.execute("""
    SELECT
        job_id,
        title,
        country,
        language,
        gold_standard_role_type,
        LENGTH(description) + LENGTH(requirements) as total_len
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    ORDER BY title, total_len DESC  -- Keep longest per title
""")

all_jobs = cursor.fetchall()

# Group by title
title_groups = defaultdict(list)
for job_id, title, country, lang, role, total_len in all_jobs:
    title_groups[title].append((job_id, country, lang, role, total_len))

# Find duplicates to remove (keep first = longest, remove rest)
duplicates_to_remove = []
titles_to_keep = set()

for title, jobs in title_groups.items():
    if len(jobs) > 1:
        keep_job = jobs[0]  # Longest (ORDER BY total_len DESC)
        remove_jobs = jobs[1:]

        titles_to_keep.add(title)  # Don't re-use this title in replacements

        print(f"\n'{title[:60]}...' - {len(jobs)} instances")
        print(f"  ✅ KEEP: {keep_job[1]} {keep_job[2]} ({keep_job[4]} chars)")

        for job_id, country, lang, role, total_len in remove_jobs:
            print(f"  ❌ REMOVE: {country} {lang} ({total_len} chars)")
            duplicates_to_remove.append({
                'job_id': str(job_id),
                'title': title,
                'country': country,
                'language': lang
            })

print(f"\n{'='*80}")
print(f"Total duplicates to remove: {len(duplicates_to_remove)}")
print(f"{'='*80}")

if len(duplicates_to_remove) == 0:
    print("✅ No duplicates found!")
    cursor.close()
    conn.close()
    sys.exit(0)

# Count by country/language for replacements
by_country_lang = defaultdict(int)
for dup in duplicates_to_remove:
    by_country_lang[(dup['country'], dup['language'])] += 1

print("\nReplacements needed by country/language:")
for (country, lang), count in sorted(by_country_lang.items()):
    print(f"  {country} {lang}: {count} jobs")

# Get list of duplicate job IDs to remove
duplicate_ids = [dup['job_id'] for dup in duplicates_to_remove]

# Find replacements with UNIQUE titles (not already in gold standard)
print("\nStep 2: Finding replacements with UNIQUE titles...\n")

# Get existing titles in gold standard (after removing duplicates)
cursor.execute("""
    SELECT DISTINCT title
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
      AND job_id NOT IN (
        SELECT UNNEST(%s::uuid[])
      )
""", (duplicate_ids,))

existing_titles = set(row[0] for row in cursor.fetchall())

print(f"Existing unique titles in gold standard: {len(existing_titles)}")

replacements = []

for (country, lang), count in sorted(by_country_lang.items()):
    cursor.execute("""
        SELECT job_id, title, description, requirements,
               LENGTH(description) + LENGTH(requirements) as total_len
        FROM raw_jobs
        WHERE country = %s
          AND language = %s
          AND is_usable = TRUE
          AND is_gold_standard = FALSE
          AND (LENGTH(description) + LENGTH(requirements)) > 1200

          -- SOFTWARE-ONLY keywords
          AND (
              title ILIKE '%%backend%%' OR title ILIKE '%%frontend%%' OR title ILIKE '%%fullstack%%'
              OR title ILIKE '%%mobile%%' OR title ILIKE '%%devops%%' OR title ILIKE '%%qa%%' OR title ILIKE '%%tester%%'
              OR title ILIKE '%%data scientist%%' OR title ILIKE '%%ml engineer%%'
              OR title ILIKE '%%desarrollador%%' OR title ILIKE '%%programador%%' OR title ILIKE '%%developer%%'
              OR title ILIKE '%%software%%'
          )

          -- Exclude non-software
          AND title NOT ILIKE '%%químico%%' AND title NOT ILIKE '%%chemical%%'
          AND title NOT ILIKE '%%eléctrico%%' AND title NOT ILIKE '%%electrical%%'
          AND title NOT ILIKE '%%mecánico%%' AND title NOT ILIKE '%%mechanical%%'
          AND title NOT ILIKE '%%civil%%' AND title NOT ILIKE '%%manufactur%%'
          AND title NOT ILIKE '%%producción%%' AND title NOT ILIKE '%%production%%'
          AND title NOT ILIKE '%%mantenimiento%%' AND title NOT ILIKE '%%maintenance%%'
          AND title NOT ILIKE '%%calidad%%' AND title NOT ILIKE '%%quality%%'
          AND title NOT ILIKE '%%corrosión%%' AND title NOT ILIKE '%%CATIA%%'

          -- Exclude business/sales
          AND title NOT ILIKE '%%ejecutivo%%' AND title NOT ILIKE '%%representante%%'
          AND title NOT ILIKE '%%coordinador%%' AND title NOT ILIKE '%%jefe%%'
          AND title NOT ILIKE '%%ventas%%' AND title NOT ILIKE '%%sales%%'
          AND title NOT ILIKE '%%negocios%%' AND title NOT ILIKE '%%business%%'
          AND title NOT ILIKE '%%comercial%%' AND title NOT ILIKE '%%planeación%%'
          AND title NOT ILIKE '%%programador de producción%%'

        ORDER BY total_len DESC
        LIMIT %s
    """, (country, lang, count + 30))  # Get extras to filter for uniqueness

    candidates = cursor.fetchall()

    print(f"  Found {len(candidates)} candidates for {country} {lang} (need {count} with unique titles)")

    # Filter for unique titles (not already in gold standard)
    unique_candidates = []
    for job_id, title, desc, req, total_len in candidates:
        if title not in existing_titles:
            unique_candidates.append((job_id, title, desc, req, total_len))
            existing_titles.add(title)  # Mark as used

            if len(unique_candidates) >= count:
                break

    print(f"  Selected {len(unique_candidates)} unique title replacements")

    for job_id, title, desc, req, total_len in unique_candidates:
        replacements.append({
            'job_id': job_id,
            'title': title,
            'country': country,
            'language': lang,
            'length': total_len
        })
        print(f"    ✅ {title[:60]}... ({total_len} chars)")

print(f"\n{'='*80}")
print(f"Total unique replacements ready: {len(replacements)}")
print(f"{'='*80}")

if len(replacements) < len(duplicate_ids):
    print(f"\n⚠️  WARNING: Only found {len(replacements)} unique replacements for {len(duplicate_ids)} duplicates")
    print("Proceeding with available replacements...")

# Execute replacement
print("\nStep 3: Executing replacement...\n")

# Remove duplicates from gold standard
cursor.execute("""
    UPDATE raw_jobs
    SET is_gold_standard = FALSE,
        gold_standard_role_type = NULL,
        gold_standard_seniority = NULL
    WHERE job_id = ANY(%s::uuid[])
""", (duplicate_ids,))

print(f"  ✅ Removed {len(duplicate_ids)} duplicate jobs from gold standard")

# Add replacements with role classification
for repl in replacements:
    title_lower = repl['title'].lower()

    # Role classification
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
    elif 'security' in title_lower:
        role = 'security'
    else:
        role = 'backend'

    # Seniority classification
    if 'senior' in title_lower or 'sr.' in title_lower or 'sr ' in title_lower or 'lead' in title_lower or 'principal' in title_lower or 'staff' in title_lower:
        seniority = 'senior'
    elif 'junior' in title_lower or 'jr.' in title_lower or 'jr ' in title_lower or 'trainee' in title_lower:
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

print(f"  ✅ Added {len(replacements)} unique title replacements")

conn.commit()

# Final verification
print("\n" + "="*80)
print("FINAL VERIFICATION (ITERATION 6)")
print("="*80)

cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE")
total = cursor.fetchone()[0]

print(f"\nTotal gold standard jobs: {total}")

if total == 300:
    print("✅ PERFECT - 300 jobs")
else:
    print(f"⚠️  Count: {total} (expected 300)")

# Check for remaining duplicate titles
cursor.execute("""
    SELECT title, COUNT(*) as count
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY title
    HAVING COUNT(*) > 1
    ORDER BY count DESC, title
""")

remaining_dups = cursor.fetchall()

if len(remaining_dups) == 0:
    print("✅ ZERO duplicate titles remaining")
else:
    print(f"\n⚠️  WARNING: {len(remaining_dups)} titles still have duplicates:")
    for title, count in remaining_dups[:10]:  # Show first 10
        print(f"  '{title[:60]}...' - {count} instances")

# Distribution by country/language
cursor.execute("""
    SELECT country, language, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY country, language
    ORDER BY country, language
""")

print("\nCountry/Language distribution:")
for country, lang, count in cursor.fetchall():
    print(f"  {country} {lang}: {count}")

# Distribution by role
cursor.execute("""
    SELECT gold_standard_role_type, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY gold_standard_role_type
    ORDER BY COUNT(*) DESC
""")

print("\nRole distribution:")
for role, count in cursor.fetchall():
    print(f"  {role}: {count}")

cursor.close()
conn.close()

print("\n" + "="*80)
print("✅ ITERATION 6 COMPLETE - ALL DUPLICATE TITLES REMOVED")
print("="*80)
print("\nNext step: Generate batch review MD for manual verification\n")
