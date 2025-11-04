#!/usr/bin/env python3
"""
Auto-replace final 12 non-tech jobs identified in final review (Iteration 4b).
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

# Títulos exactos de los 12 jobs a remover
bad_job_titles = [
    "Puestos vacantes Ingenieros Senior. Distintas especialidades (2341)",
    "Puestos vacantes Ingeniero Ssr. (2703)",
    "SSR. PRODUCTION ENGINEER (Neuquén, Argentina)",
    "JDE Developer",
    "Engineering Sales Specialist",
    "LIDER DE INGENIERÍA Y CIENCIAS DISCIPLINARIAS - GEOCIENCIAS Y PETRÓLEO - RTS -LEAD ENGINEER, DISCIPLINARY ENGINEERING AND SCIENCE - GEOSCIENCE & PETROLEUM - RTS",
    "Pre Sales Engineer",
    "Sales Representative  Product Developer",
    "Desarrollador de Negocios SR - Cartagena (Basic Industries & Downstream)",
    "Senior Fullstack Developer ",  # Note: has trailing space
    "Logistics Engineering Trainee",
    "Technician II, RD Engineering (Juarez Chihuahua, Chihuahua, Mexico)"
]

print("Step 1: Identifying jobs to remove...")
print(f"Target: {len(bad_job_titles)} jobs\n")

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
        print(f"  Found: [{country} {lang}] {title[:60]}...")
    else:
        print(f"  NOT FOUND: {title[:60]}...")

print(f"\nTotal to remove: {len(bad_job_ids)} jobs\n")

if len(bad_job_ids) == 0:
    print("No jobs to remove. Exiting.")
    cursor.close()
    conn.close()
    sys.exit(0)

# Get country/language distribution of bad jobs
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

print("Replacements needed by country/language:")
for (country, lang), count in replacements_needed.items():
    print(f"  {country} {lang}: {count} jobs")

# Find replacement candidates
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
          -- Pure tech keywords
          AND (
              title ILIKE '%%developer%%' OR title ILIKE '%%engineer%%'
              OR title ILIKE '%%desarrollador%%' OR title ILIKE '%%programador%%'
              OR title ILIKE '%%devops%%' OR title ILIKE '%%backend%%'
              OR title ILIKE '%%frontend%%' OR title ILIKE '%%fullstack%%'
              OR title ILIKE '%%qa%%' OR title ILIKE '%%tester%%'
              OR title ILIKE '%%data scientist%%' OR title ILIKE '%%ml engineer%%'
          )
          -- Exclude non-tech patterns
          AND title NOT ILIKE '%%manager%%'
          AND title NOT ILIKE '%%director%%'
          AND title NOT ILIKE '%%gerente%%'
          AND title NOT ILIKE '%%sales%%'
          AND title NOT ILIKE '%%ventas%%'
          AND title NOT ILIKE '%%pre sales%%'
          AND title NOT ILIKE '%%preventa%%'
          AND title NOT ILIKE '%%business%%'
          AND title NOT ILIKE '%%negocios%%'
          AND title NOT ILIKE '%%logistics%%'
          AND title NOT ILIKE '%%logistica%%'
          AND title NOT ILIKE '%%production engineer%%'
          AND title NOT ILIKE '%%petroleum%%'
          AND title NOT ILIKE '%%petróleo%%'
          AND title NOT ILIKE '%%geoscience%%'
          AND title NOT ILIKE '%%mechanical%%'
          AND title NOT ILIKE '%%trainee%%'
          AND title NOT ILIKE '%%bi engineer%%'
          AND title NOT ILIKE '%%jde%%'
        ORDER BY total_len DESC
        LIMIT %s
    """, (country, lang, count + 10))  # Get extras as backup

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

if len(replacements) < len(bad_job_ids):
    print(f"\n⚠️  WARNING: Only found {len(replacements)} replacements for {len(bad_job_ids)} jobs to remove")
    print("Proceeding with available replacements...")

# Execute replacement
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
    elif 'security' in title_lower or 'cybersecurity' in title_lower:
        role = 'security'
    else:
        role = 'backend'  # Default

    # Seniority classification
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

# Verify
cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE")
total = cursor.fetchone()[0]

print(f"\n{'='*80}")
print(f"REPLACEMENT COMPLETE (Iteration 4b)")
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

# Show role distribution
cursor.execute("""
    SELECT gold_standard_role_type, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY gold_standard_role_type
    ORDER BY COUNT(*) DESC
""")

print("\nDistribution by role:")
for role, count in cursor.fetchall():
    print(f"  {role}: {count}")

cursor.close()
conn.close()

print("\n✅ Done!")
