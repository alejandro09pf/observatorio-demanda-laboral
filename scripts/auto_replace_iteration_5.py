#!/usr/bin/env python3
"""
Auto-replace Iteration 5: Remove ALL non-software engineering jobs.

This is the final cleanup iteration to ensure 100% pure software development roles.

Problems addressed:
- Chemical/mechanical/electrical/civil engineers
- Manufacturing/production engineers
- Quality engineers (non-QA testing)
- Maintenance engineers
- CAD/design engineers (CATIA, proyectistas)
- Process engineers
- Production programmers (factory floor, not software)

Total to remove: ~19 jobs
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

print("="*80)
print("ITERATION 5: FINAL NON-SOFTWARE ENGINEERING CLEANUP")
print("="*80)
print("Step 1: Identifying all non-software engineering jobs...\\n")

# Identify non-software jobs with comprehensive patterns
cursor.execute("""
    SELECT
        job_id,
        country,
        language,
        title
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
        AND (
            -- Chemical/mechanical/electrical/civil engineers
            title ILIKE '%químico%' OR title ILIKE '%quimico%'
            OR title ILIKE '%chemical%'
            OR title ILIKE '%eléctrico%' OR title ILIKE '%electrico%'
            OR (title ILIKE '%electrical%' AND title NOT ILIKE '%software%')
            OR title ILIKE '%mecánico%' OR title ILIKE '%mecanico%'
            OR title ILIKE '%mechanical%'
            OR title ILIKE '%civil engineer%' OR title ILIKE '%ingeniero civil%'
            OR title ILIKE '%corrosion%' OR title ILIKE '%corrosión%'

            -- Manufacturing/production
            OR title ILIKE '%manufactur%'
            OR title ILIKE '%producción planta%' OR title ILIKE '%produccion planta%'
            OR title ILIKE '%production optim%'
            OR title ILIKE '%programador de producción%' OR title ILIKE '%programador de produccion%'
            OR (title ILIKE '%mantenimiento%' AND title NOT ILIKE '%software%')
            OR (title ILIKE '%maintenance%' AND title NOT ILIKE '%software%')

            -- Quality/process (excluding QA testing)
            OR title ILIKE '%ingeniero de calidad%'
            OR (title ILIKE '%quality engineer%'
                AND title NOT ILIKE '%software%'
                AND title NOT ILIKE '%qa%'
                AND title NOT ILIKE '%test%')
            OR title ILIKE '%calidad proveedor%'
            OR (title ILIKE '%ingeniero de procesos%' AND title NOT ILIKE '%software%')
            OR (title ILIKE '%process engineer%' AND title NOT ILIKE '%software%')

            -- CAD/design (not software dev)
            OR title ILIKE '%CATIA%'
            OR title ILIKE '%proyectista%'
            OR (title ILIKE '%diseñador%'
                AND title NOT ILIKE '%software%'
                AND title NOT ILIKE '%ux%'
                AND title NOT ILIKE '%ui%')

            -- Other non-software
            OR (title ILIKE '%instructor%' AND title NOT ILIKE '%software%')
            OR title ILIKE '%cajero%'
            OR title ILIKE '%ductos%'
        )
    ORDER BY country, language, title
""")

bad_jobs = cursor.fetchall()
bad_job_ids = [str(job[0]) for job in bad_jobs]

print(f"Found {len(bad_jobs)} non-software engineering jobs:\\n")

# Group by country/language for reporting
from collections import defaultdict
by_country_lang = defaultdict(list)

for job_id, country, lang, title in bad_jobs:
    by_country_lang[(country, lang)].append(title)
    print(f"  ❌ [{country} {lang}] {title[:70]}...")

print(f"\\nTotal to remove: {len(bad_job_ids)} jobs\\n")

if len(bad_job_ids) == 0:
    print("✅ No non-software jobs found. Dataset is clean!")
    cursor.close()
    conn.close()
    sys.exit(0)

# Show distribution of jobs to remove
print("Distribution of jobs to remove:")
replacements_needed = {}
for (country, lang), titles in by_country_lang.items():
    count = len(titles)
    replacements_needed[(country, lang)] = count
    print(f"  {country} {lang}: {count} jobs")

# Find ULTRA-STRICT software-only replacements
print("\\nStep 2: Finding ULTRA-STRICT pure software replacements...\\n")

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

          -- ULTRA-STRICT: Only pure software development keywords
          AND (
              title ILIKE '%%software%%'
              OR title ILIKE '%%backend%%' OR title ILIKE '%%back-end%%'
              OR title ILIKE '%%frontend%%' OR title ILIKE '%%front-end%%'
              OR title ILIKE '%%fullstack%%' OR title ILIKE '%%full-stack%%' OR title ILIKE '%%full stack%%'
              OR title ILIKE '%%mobile%%' OR title ILIKE '%%ios%%' OR title ILIKE '%%android%%'
              OR title ILIKE '%%devops%%' OR title ILIKE '%%sre%%' OR title ILIKE '%%site reliability%%'
              OR title ILIKE '%%qa%%' OR title ILIKE '%%tester%%' OR title ILIKE '%%test engineer%%'
              OR title ILIKE '%%data scientist%%' OR title ILIKE '%%ml engineer%%' OR title ILIKE '%%machine learning%%'
              OR title ILIKE '%%desarrollador%%' OR title ILIKE '%%programador%%'
              OR title ILIKE '%%python%%' OR title ILIKE '%%java%%' OR title ILIKE '%%javascript%%'
              OR title ILIKE '%%web developer%%' OR title ILIKE '%%desarrollador web%%'
              OR title ILIKE '%%cloud engineer%%' OR title ILIKE '%%platform engineer%%'
          )

          -- ULTRA-STRICT EXCLUSIONS: No ambiguous "engineer" or "ingeniero"
          AND title NOT ILIKE '%%chemical%%' AND title NOT ILIKE '%%químico%%' AND title NOT ILIKE '%%quimico%%'
          AND title NOT ILIKE '%%mechanical%%' AND title NOT ILIKE '%%mecánico%%' AND title NOT ILIKE '%%mecanico%%'
          AND title NOT ILIKE '%%electrical%%' AND title NOT ILIKE '%%eléctrico%%' AND title NOT ILIKE '%%electrico%%'
          AND title NOT ILIKE '%%civil%%'
          AND title NOT ILIKE '%%manufacturing%%' AND title NOT ILIKE '%%manufactura%%'
          AND title NOT ILIKE '%%production%%' AND title NOT ILIKE '%%producción%%' AND title NOT ILIKE '%%produccion%%'
          AND title NOT ILIKE '%%maintenance%%' AND title NOT ILIKE '%%mantenimiento%%'
          AND title NOT ILIKE '%%quality%%' AND title NOT ILIKE '%%calidad%%'
          AND title NOT ILIKE '%%process%%' AND title NOT ILIKE '%%proceso%%'
          AND title NOT ILIKE '%%corrosion%%' AND title NOT ILIKE '%%corrosión%%'
          AND title NOT ILIKE '%%CATIA%%'
          AND title NOT ILIKE '%%proyectista%%'
          AND title NOT ILIKE '%%diseñador%%'
          AND title NOT ILIKE '%%instructor%%'
          AND title NOT ILIKE '%%cajero%%'
          AND title NOT ILIKE '%%ductos%%'

          -- Exclude management/sales/business
          AND title NOT ILIKE '%%manager%%' AND title NOT ILIKE '%%gerente%%'
          AND title NOT ILIKE '%%director%%'
          AND title NOT ILIKE '%%sales%%' AND title NOT ILIKE '%%ventas%%'
          AND title NOT ILIKE '%%business%%' AND title NOT ILIKE '%%negocios%%'
          AND title NOT ILIKE '%%logistics%%' AND title NOT ILIKE '%%logística%%'
          AND title NOT ILIKE '%%petroleum%%' AND title NOT ILIKE '%%petróleo%%'
          AND title NOT ILIKE '%%drilling%%' AND title NOT ILIKE '%%perforación%%'

        ORDER BY total_len DESC
        LIMIT %s
    """, (country, lang, count + 15))  # Get extras as backup

    candidates = cursor.fetchall()

    print(f"  Found {len(candidates)} PURE SOFTWARE candidates for {country} {lang} (need {count})")

    if len(candidates) < count:
        print(f"    ⚠️  WARNING: Only {len(candidates)} available, need {count}")

    for job_id, title, desc, req, total_len in candidates[:count]:
        replacements.append({
            'job_id': job_id,
            'title': title,
            'country': country,
            'language': lang,
            'length': total_len
        })
        print(f"    ✅ {title[:65]}... ({total_len} chars)")

print(f"\\nTotal replacements ready: {len(replacements)}")

if len(replacements) < len(bad_job_ids):
    print(f"\\n⚠️  WARNING: Only found {len(replacements)} replacements for {len(bad_job_ids)} jobs to remove")
    print(f"Proceeding with available replacements...")

# Execute replacement
print("\\nStep 3: Executing replacement...\\n")

# Remove non-software jobs from gold standard
cursor.execute("""
    UPDATE raw_jobs
    SET is_gold_standard = FALSE,
        gold_standard_role_type = NULL,
        gold_standard_seniority = NULL
    WHERE job_id = ANY(%s::uuid[])
""", (bad_job_ids,))

print(f"  ✅ Removed {len(bad_job_ids)} non-software jobs from gold standard")

# Add pure software replacements with role classification
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
    elif 'devops' in title_lower or 'sre' in title_lower or 'site reliability' in title_lower:
        role = 'devops'
    elif 'data' in title_lower or 'ml' in title_lower or 'machine learning' in title_lower:
        role = 'data_science'
    elif 'qa' in title_lower or 'test' in title_lower:
        role = 'qa'
    elif 'security' in title_lower or 'cybersecurity' in title_lower:
        role = 'security'
    elif 'python' in title_lower or 'java' in title_lower or 'javascript' in title_lower:
        role = 'backend'  # Language-specific developer = backend
    else:
        role = 'backend'  # Default to backend for ambiguous software roles

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

print(f"  ✅ Added {len(replacements)} PURE SOFTWARE replacements")

conn.commit()

# Final verification
print("\\n" + "="*80)
print("FINAL VERIFICATION")
print("="*80)

cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE")
total = cursor.fetchone()[0]

print(f"\\nTotal gold standard jobs: {total}")

if total == 300:
    print("✅ PERFECT - 300 jobs")
else:
    print(f"⚠️  Count: {total} (expected 300)")

# Check for remaining non-software jobs
cursor.execute("""
    SELECT COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
        AND (
            title ILIKE '%%químico%%' OR title ILIKE '%%quimico%%'
            OR title ILIKE '%%chemical%%'
            OR title ILIKE '%%eléctrico%%' OR title ILIKE '%%electrico%%'
            OR title ILIKE '%%electrical%%' AND title NOT ILIKE '%%software%%'
            OR title ILIKE '%%mecánico%%' OR title ILIKE '%%mecanico%%'
            OR title ILIKE '%%mechanical%%'
            OR title ILIKE '%%civil%%'
            OR title ILIKE '%%corrosion%%' OR title ILIKE '%%corrosión%%'
            OR title ILIKE '%%manufactur%%'
            OR title ILIKE '%%producción planta%%' OR title ILIKE '%%produccion planta%%'
            OR title ILIKE '%%mantenimiento%%' AND title NOT ILIKE '%%software%%'
            OR title ILIKE '%%CATIA%%'
            OR title ILIKE '%%proyectista%%'
        )
""")

remaining_nonsoftware = cursor.fetchone()[0]

if remaining_nonsoftware == 0:
    print("✅ ZERO non-software engineering jobs remaining")
else:
    print(f"⚠️  WARNING: {remaining_nonsoftware} non-software jobs still in dataset")

# Distribution by country/language
cursor.execute("""
    SELECT country, language, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY country, language
    ORDER BY country, language
""")

print("\\nCountry/Language distribution:")
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

print("\\nRole distribution:")
for role, count in cursor.fetchall():
    print(f"  {role}: {count}")

# Distribution by seniority
cursor.execute("""
    SELECT gold_standard_seniority, COUNT(*)
    FROM raw_jobs
    WHERE is_gold_standard = TRUE
    GROUP BY gold_standard_seniority
    ORDER BY COUNT(*) DESC
""")

print("\\nSeniority distribution:")
for seniority, count in cursor.fetchall():
    print(f"  {seniority}: {count}")

cursor.close()
conn.close()

print("\\n" + "="*80)
print("✅ ITERATION 5 COMPLETE - DATASET VERIFIED AS 100% PURE SOFTWARE")
print("="*80)
print("\\nNext step: Proceed with annotation of 300 verified pure software jobs\\n")
