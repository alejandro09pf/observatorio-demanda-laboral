#!/usr/bin/env python3
"""
Auto-replace final 5 non-tech jobs (Iteration 4c - Final cleanup).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from config.settings import get_settings

settings = get_settings()
db_url = settings.database_url
if db_url.startswith('postgresql://'):
    db_url = db_url.replace('postgresql://', 'postgres://')

conn = psycopg2.connect(db_url)
cursor = conn.cursor()

# Títulos exactos de los 5 jobs finales a remover
bad_job_titles = [
    "Engineer.Drilling Sol.III",
    "Ingeniero(a) de Ventas (O&G) (51437)",
    "Sales Engineer",
    "Ingeniero de Ventas Externas (Tampico) (Naucalpan de Juárez, Estado de Mexico, MX, 54030)",
    "Postsales Engineer Tier 1"
]

print("ITERATION 4c: FINAL CLEANUP")
print("="*80)
print("Step 1: Identifying final 5 non-tech jobs to remove...\n")

bad_job_ids = []

for title in bad_job_titles:
    cursor.execute("""
        SELECT job_id, country, language
        FROM raw_jobs
        WHERE is_gold_standard = TRUE
          AND title = %s
    """, (title,))

    result = cursor.fetchone()
    if result:
        job_id, country, lang = result
        bad_job_ids.append(str(job_id))
        print(f"  ❌ [{country} {lang}] {title[:65]}...")
    else:
        print(f"  NOT FOUND: {title[:65]}...")

print(f"\nTotal to remove: {len(bad_job_ids)} jobs\n")

if len(bad_job_ids) == 0:
    print("No jobs to remove. Exiting.")
    cursor.close()
    conn.close()
    sys.exit(0)

# Get distribution
bad_job_ids_str = bad_job_ids
cursor.execute("""
    SELECT country, language, COUNT(*)
    FROM raw_jobs
    WHERE job_id = ANY(%s::uuid[])
    GROUP BY country, language
""", (bad_job_ids_str,))

replacements_needed = {}
for country, lang, count in cursor.fetchall():
    replacements_needed[(country, lang)] = count

print("Replacements needed:")
for (country, lang), count in replacements_needed.items():
    print(f"  {country} {lang}: {count} jobs")

# Find replacements
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
          -- Pure tech keywords (excluding Salesforce to avoid false positives)
          AND (
              title ILIKE '%%backend%%' OR title ILIKE '%%frontend%%'
              OR title ILIKE '%%fullstack%%' OR title ILIKE '%%full stack%%'
              OR title ILIKE '%%mobile%%' OR title ILIKE '%%ios%%' OR title ILIKE '%%android%%'
              OR title ILIKE '%%devops%%' OR title ILIKE '%%sre%%'
              OR title ILIKE '%%qa%%' OR title ILIKE '%%tester%%' OR title ILIKE '%%test engineer%%'
              OR title ILIKE '%%data scientist%%' OR title ILIKE '%%ml engineer%%'
              OR title ILIKE '%%python%%' OR title ILIKE '%%java%%' OR title ILIKE '%%javascript%%'
          )
          -- Strict exclusions
          AND title NOT ILIKE '%%sales%%'
          AND title NOT ILIKE '%%ventas%%'
          AND title NOT ILIKE '%%manager%%'
          AND title NOT ILIKE '%%director%%'
          AND title NOT ILIKE '%%gerente%%'
          AND title NOT ILIKE '%%business%%'
          AND title NOT ILIKE '%%logistics%%'
          AND title NOT ILIKE '%%drilling%%'
          AND title NOT ILIKE '%%petroleum%%'
          AND title NOT ILIKE '%%petróleo%%'
        ORDER BY total_len DESC
        LIMIT %s
    """, (country, lang, count + 10))

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

# Execute replacement
print("\nStep 3: Executing final replacement...")

cursor.execute("""
    UPDATE raw_jobs
    SET is_gold_standard = FALSE,
        gold_standard_role_type = NULL,
        gold_standard_seniority = NULL
    WHERE job_id = ANY(%s::uuid[])
""", (bad_job_ids_str,))

print(f"  ✅ Removed {len(bad_job_ids)} non-tech jobs")

# Add replacements
for repl in replacements:
    title_lower = repl['title'].lower()

    # Role classification
    if 'backend' in title_lower:
        role = 'backend'
    elif 'frontend' in title_lower or 'front-end' in title_lower:
        role = 'frontend'
    elif 'fullstack' in title_lower or 'full-stack' in title_lower:
        role = 'fullstack'
    elif 'mobile' in title_lower or 'ios' in title_lower or 'android' in title_lower:
        role = 'mobile'
    elif 'devops' in title_lower or 'sre' in title_lower:
        role = 'devops'
    elif 'data' in title_lower or 'ml' in title_lower:
        role = 'data_science'
    elif 'qa' in title_lower or 'test' in title_lower:
        role = 'qa'
    elif 'security' in title_lower:
        role = 'security'
    else:
        role = 'backend'

    # Seniority
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

print(f"  ✅ Added {len(replacements)} pure tech replacements")

conn.commit()

# Final verification
cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE")
total = cursor.fetchone()[0]

print(f"\n{'='*80}")
print(f"FINAL REPLACEMENT COMPLETE (Iteration 4c)")
print(f"{'='*80}")
print(f"Total gold standard jobs: {total}")

if total == 300:
    print("✅ PERFECT - 300 jobs")
else:
    print(f"⚠️  Count: {total} (expected 300)")

# Distribution
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

print(f"\n{'='*80}")
print("✅ DATASET FINAL - LISTO PARA ANOTACIÓN")
print(f"{'='*80}\n")
