#!/usr/bin/env python3
"""
Select 300 Gold Standard Jobs for Manual Annotation

Distribution:
- 250 Spanish (100 CO, 100 MX, 50 AR)
- 50 English (17 CO, 17 MX, 16 AR)
- Roles: Backend 80, Fullstack 60, Frontend 50, Data 40, DevOps 40, Mobile 15, QA 10, Other 5
- Seniority: Junior 90, Mid 90, Senior 120
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
import re
from collections import defaultdict
import json
from config.settings import get_settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Language detection patterns
SPANISH_PATTERNS = [
    r'\b(experiencia|años|requisitos|habilidades|conocimientos|desarrollo|ingeniero|empresa)\b',
    r'\b(buscamos|ofrecemos|ubicación|necesario|deseables|técnicas)\b'
]

ENGLISH_PATTERNS = [
    r'\b(experience|years|requirements|skills|knowledge|development|engineer|company)\b',
    r'\b(looking|offer|location|required|desirable|technical|responsibilities)\b'
]

def detect_language(text):
    """Detect if text is Spanish, English, or Mixed."""
    text_lower = text.lower()[:2000]  # Check first 2000 chars

    spanish_matches = sum(len(re.findall(pattern, text_lower, re.IGNORECASE))
                          for pattern in SPANISH_PATTERNS)
    english_matches = sum(len(re.findall(pattern, text_lower, re.IGNORECASE))
                          for pattern in ENGLISH_PATTERNS)

    if spanish_matches > english_matches * 2:
        return 'es'
    elif english_matches > spanish_matches * 2:
        return 'en'
    else:
        return 'mixed'

def calculate_quality_score(job):
    """Calculate quality score for a job (0-100)."""
    score = 50  # Base score

    title, desc, req = job[2], job[3], job[4]

    # Length score (0-20 points)
    total_len = len(desc) + len(req)
    if total_len > 3000:
        score += 20
    elif total_len > 2000:
        score += 15
    elif total_len > 1000:
        score += 10

    # Has requirements section (10 points)
    if len(req) > 100:
        score += 10

    # Title quality (10 points)
    tech_keywords = ['developer', 'engineer', 'desarrollador', 'ingeniero',
                     'programador', 'devops', 'data', 'scientist', 'analyst']
    if any(kw in title.lower() for kw in tech_keywords):
        score += 10

    # Technical skills mentioned (0-10 points)
    skills = ['python', 'java', 'javascript', 'react', 'angular', 'node',
              'aws', 'azure', 'docker', 'kubernetes', 'sql', 'mongodb']
    combined_text = (title + desc + req).lower()
    skills_count = sum(1 for skill in skills if skill in combined_text)
    score += min(skills_count, 10)

    # Penalty for HTML/JS noise (0-10 points penalty)
    noise_patterns = ['window.', 'function()', 'getElementById', '<div', '<script']
    noise_count = sum(1 for pattern in noise_patterns if pattern in desc)
    score -= min(noise_count * 2, 10)

    return max(0, min(100, score))

def classify_role(title, description):
    """Classify job role based on title and description."""
    title_lower = title.lower()
    text = (title + ' ' + description).lower()

    # Priority order matters
    # MOBILE: Very strict - must be in title or explicit mobile developer mention
    mobile_title_keywords = [r'\bmobile\b', r'\bios\b', r'\bandroid\b',
                             r'flutter', r'react native', r'móvil', r'movil']
    mobile_in_title = any(re.search(pattern, title_lower) for pattern in mobile_title_keywords)

    mobile_explicit = any(phrase in text for phrase in [
        'mobile developer', 'mobile engineer', 'desarrollador móvil',
        'desarrollador movil', 'ingeniero móvil', 'ingeniero movil',
        'ios developer', 'ios engineer', 'android developer', 'android engineer',
        'flutter developer', 'react native developer'
    ])

    if mobile_in_title or mobile_explicit:
        return 'mobile'
    elif any(kw in text for kw in ['qa', 'test', 'quality assurance', 'automation test']):
        return 'qa'
    elif any(kw in text for kw in ['security', 'cybersecurity', 'infosec', 'architect']):
        return 'security'
    elif any(kw in text for kw in ['data scien', 'machine learning', 'ml engineer', 'data analyst', 'big data']):
        return 'data_science'
    elif any(kw in text for kw in ['devops', 'sre', 'site reliability', 'platform engineer', 'cloud engineer', 'infrastructure']):
        return 'devops'
    elif any(kw in text for kw in ['frontend', 'front-end', 'front end']) or \
         (any(kw in text for kw in ['react', 'angular', 'vue', 'css', 'html']) and 'backend' not in text):
        return 'frontend'
    elif any(kw in text for kw in ['backend', 'back-end', 'back end', 'api', 'microservices', 'server']):
        return 'backend'
    elif any(kw in text for kw in ['full stack', 'fullstack', 'full-stack']):
        return 'fullstack'
    else:
        return 'other'

def classify_seniority(title, description):
    """Classify seniority level."""
    text = (title + ' ' + description).lower()

    if any(kw in text for kw in ['senior', 'sr.', 'lead', 'staff', 'principal', 'architect']):
        return 'senior'
    elif any(kw in text for kw in ['junior', 'jr.', 'trainee', 'entry', 'graduate']):
        return 'junior'
    else:
        return 'mid'

def select_gold_standard_jobs():
    """Main selection function."""

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    logger.info("="*60)
    logger.info("GOLD STANDARD SELECTION - PHASE 1: Language Detection")
    logger.info("="*60)

    # PHASE 1: Detect language for all jobs
    logger.info("Detecting language for all jobs (this may take a few minutes)...")
    cursor.execute("""
        SELECT job_id, title, description, requirements
        FROM raw_jobs
        WHERE is_usable = TRUE
        AND language IS NULL
    """)

    jobs_to_update = cursor.fetchall()
    logger.info(f"Found {len(jobs_to_update)} jobs without language tag")

    updated = 0
    for job_id, title, desc, req in jobs_to_update:
        combined_text = f"{title} {desc} {req}"
        lang = detect_language(combined_text)

        cursor.execute("""
            UPDATE raw_jobs
            SET language = %s
            WHERE job_id = %s
        """, (lang, job_id))

        updated += 1
        if updated % 5000 == 0:
            conn.commit()
            logger.info(f"  Updated {updated} jobs...")

    conn.commit()
    logger.info(f"✅ Language detection complete: {updated} jobs updated")

    # PHASE 2: Get candidate jobs with STRICT FILTERS
    logger.info("\n" + "="*60)
    logger.info("PHASE 2: Pre-selecting Candidates (STRICT FILTERS)")
    logger.info("="*60)

    cursor.execute("""
        SELECT DISTINCT ON (content_hash)
            job_id,
            country,
            title,
            description,
            requirements,
            portal,
            language,
            content_hash
        FROM raw_jobs
        WHERE
            is_usable = TRUE
            AND (LENGTH(description) + LENGTH(requirements)) > 1000
            -- Include tech roles
            AND (
                title ILIKE '%developer%' OR title ILIKE '%engineer%'
                OR title ILIKE '%desarrollador%' OR title ILIKE '%ingeniero%'
                OR title ILIKE '%programador%' OR title ILIKE '%devops%'
                OR title ILIKE '%data scien%' OR title ILIKE '%scientist%'
                OR title ILIKE '%qa%' OR title ILIKE '%frontend%'
                OR title ILIKE '%backend%' OR title ILIKE '%full%stack%'
                OR title ILIKE '%mobile%'
            )
            -- EXCLUDE non-tech roles
            AND title NOT ILIKE '%manager%'
            AND title NOT ILIKE '%director%'
            AND title NOT ILIKE '%gerente%'
            AND title NOT ILIKE '%coordinator%'
            AND title NOT ILIKE '%coordinador%'
            AND title NOT ILIKE '%business analyst%'
            AND title NOT ILIKE '%analista de negocio%'
            AND title NOT ILIKE '%bi engineer%'
            AND title NOT ILIKE '%business intelligence%'
            AND title NOT ILIKE '%mechanical%'
            AND title NOT ILIKE '%chemical%'
            AND title NOT ILIKE '%civil engineer%'
            AND title NOT ILIKE '%support engineer%'
            AND title NOT ILIKE '%help desk%'
            AND title NOT ILIKE '%scrum master%'
            AND title NOT ILIKE '%product manager%'
            AND title NOT ILIKE '%project manager%'
        ORDER BY content_hash
    """)

    candidates = cursor.fetchall()
    logger.info(f"Found {len(candidates)} candidate jobs (after deduplication)")

    # PHASE 3: Score and classify candidates with additional filters
    logger.info("\nScoring, classifying and filtering candidates...")

    # Blacklist of generic titles
    GENERIC_TITLES = [
        'ingeniero de sistemas', 'ingeniero', 'developer', 'engineer',
        'desarrollador', 'programador', 'software engineer'
    ]

    scored_candidates = []
    filtered_out = {'generic_title': 0, 'other_role': 0}

    for job in candidates:
        job_id, country, title, desc, req, portal, lang, content_hash = job

        # Skip generic titles (unless they have specific context)
        title_lower = title.lower().strip()
        if title_lower in GENERIC_TITLES and len(title.split()) <= 3:
            filtered_out['generic_title'] += 1
            continue

        quality_score = calculate_quality_score(job)
        role = classify_role(title, desc)
        seniority = classify_seniority(title, desc)

        # Skip 'other' roles unless quality score is very high (95+)
        if role == 'other' and quality_score < 95:
            filtered_out['other_role'] += 1
            continue

        scored_candidates.append({
            'job_id': job_id,
            'country': country,
            'language': lang,
            'role': role,
            'seniority': seniority,
            'quality_score': quality_score,
            'title': title,
            'portal': portal,
            'desc_len': len(desc),
            'req_len': len(req)
        })

    # Sort by quality score
    scored_candidates.sort(key=lambda x: x['quality_score'], reverse=True)

    logger.info(f"Candidates scored and classified")
    logger.info(f"  Filtered out: {filtered_out['generic_title']} generic titles, {filtered_out['other_role']} 'other' roles")
    logger.info(f"  Remaining: {len(scored_candidates)} candidates")
    if len(scored_candidates) > 0:
        logger.info(f"  Top quality score: {scored_candidates[0]['quality_score']}")
        logger.info(f"  Median quality score: {scored_candidates[len(scored_candidates)//2]['quality_score']}")

    # PHASE 4: Stratified selection (FLEXIBLE ALGORITHM)
    logger.info("\n" + "="*60)
    logger.info("PHASE 3: Stratified Selection (300 jobs)")
    logger.info("="*60)
    logger.info("Algorithm: Prioritize Language > Country > Role (Seniority flexible)")

    # Target distribution (hierarchical priorities)
    targets = {
        ('CO', 'es'): {'total': 100, 'roles': {
            'backend': 27, 'fullstack': 20, 'frontend': 17, 'data_science': 13,
            'devops': 13, 'mobile': 5, 'qa': 3, 'security': 2
        }},
        ('MX', 'es'): {'total': 100, 'roles': {
            'backend': 27, 'fullstack': 20, 'frontend': 17, 'data_science': 13,
            'devops': 13, 'mobile': 5, 'qa': 3, 'security': 2
        }},
        ('AR', 'es'): {'total': 50, 'roles': {
            'backend': 13, 'fullstack': 10, 'frontend': 8, 'data_science': 7,
            'devops': 7, 'mobile': 3, 'qa': 2, 'security': 0
        }},
        ('CO', 'en'): {'total': 17, 'roles': {
            'backend': 5, 'fullstack': 4, 'frontend': 3, 'data_science': 2,
            'devops': 2, 'mobile': 1, 'qa': 0, 'security': 0
        }},
        ('MX', 'en'): {'total': 17, 'roles': {
            'backend': 5, 'fullstack': 4, 'frontend': 3, 'data_science': 2,
            'devops': 2, 'mobile': 1, 'qa': 0, 'security': 0
        }},
        ('AR', 'en'): {'total': 16, 'roles': {
            'backend': 5, 'fullstack': 3, 'frontend': 3, 'data_science': 2,
            'devops': 2, 'mobile': 1, 'qa': 0, 'security': 0
        }},
    }

    selected = []
    selected_ids = set()

    # Group candidates by (country, language, role) - NO seniority in key
    grouped = defaultdict(list)
    for candidate in scored_candidates:
        key = (candidate['country'], candidate['language'], candidate['role'])
        grouped[key].append(candidate)

    # Select from each (country, language) pair
    for (country, lang), target in targets.items():
        logger.info(f"\nSelecting {country} {lang.upper()} ({target['total']} jobs):")

        # Get all candidates for this (country, language)
        country_lang_candidates = [
            c for c in scored_candidates
            if c['country'] == country and c['language'] == lang
            and c['job_id'] not in selected_ids
        ]

        logger.info(f"  Available candidates: {len(country_lang_candidates)}")

        if len(country_lang_candidates) < target['total']:
            logger.warning(f"  ⚠️  Only {len(country_lang_candidates)} available, need {target['total']}")

        # Try to fill role quotas
        country_selected = 0
        role_counts = {}

        for role, role_target in sorted(target['roles'].items(), key=lambda x: -x[1]):
            if role_target == 0:
                continue

            # Get candidates for this role
            role_candidates = [c for c in country_lang_candidates if c['role'] == role]

            # Select up to role_target (or all available if less)
            to_select = min(role_target, len(role_candidates))

            for i in range(to_select):
                candidate = role_candidates[i]
                selected.append(candidate)
                selected_ids.add(candidate['job_id'])
                country_selected += 1

            if to_select > 0:
                role_counts[role] = to_select
                logger.info(f"  {role:15}: {to_select:2}/{role_target:2} jobs selected")

        # If we haven't reached the country/language target, fill with best remaining
        remaining_needed = target['total'] - country_selected

        if remaining_needed > 0:
            logger.info(f"  Need {remaining_needed} more jobs to reach {target['total']}")

            # Get remaining candidates (any role)
            remaining_candidates = [
                c for c in country_lang_candidates
                if c['job_id'] not in selected_ids
            ]

            # Select best quality remaining
            to_select = min(remaining_needed, len(remaining_candidates))

            for i in range(to_select):
                candidate = remaining_candidates[i]
                selected.append(candidate)
                selected_ids.add(candidate['job_id'])
                country_selected += 1

                role = candidate['role']
                role_counts[role] = role_counts.get(role, 0) + 1

            if to_select > 0:
                logger.info(f"  Added {to_select} jobs from remaining pool (any role)")

        logger.info(f"  ✅ Total selected for {country} {lang.upper()}: {country_selected}/{target['total']}")

    logger.info(f"\n✅ Selected {len(selected)} jobs total")

    # PHASE 5: Save selection
    logger.info("\n" + "="*60)
    logger.info("PHASE 4: Saving Selection")
    logger.info("="*60)

    # Update database
    for job in selected:
        cursor.execute("""
            UPDATE raw_jobs
            SET is_gold_standard = TRUE,
                gold_standard_role_type = %s,
                gold_standard_seniority = %s
            WHERE job_id = %s
        """, (job['role'], job['seniority'], job['job_id']))

    conn.commit()
    logger.info(f"✅ Database updated with gold standard flags")

    # Save to JSON
    output_path = Path("data/gold_standard/selected_jobs.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(selected, f, ensure_ascii=False, indent=2)

    logger.info(f"✅ Selection saved to: {output_path}")

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("SELECTION SUMMARY")
    logger.info("="*60)

    # By country and language
    summary = defaultdict(int)
    for job in selected:
        summary[(job['country'], job['language'])] += 1

    logger.info("\nBy Country & Language:")
    for (country, lang), count in sorted(summary.items()):
        logger.info(f"  {country} {lang.upper()}: {count} jobs")

    # By role
    role_counts = defaultdict(int)
    for job in selected:
        role_counts[job['role']] += 1

    logger.info("\nBy Role:")
    for role, count in sorted(role_counts.items(), key=lambda x: -x[1]):
        logger.info(f"  {role:15}: {count} jobs")

    # By seniority
    sen_counts = defaultdict(int)
    for job in selected:
        sen_counts[job['seniority']] += 1

    logger.info("\nBy Seniority:")
    for sen, count in sorted(sen_counts.items()):
        logger.info(f"  {sen:8}: {count} jobs")

    cursor.close()
    conn.close()

    return selected


if __name__ == "__main__":
    selected = select_gold_standard_jobs()

    print("\n" + "="*60)
    print("✅ GOLD STANDARD SELECTION COMPLETE")
    print("="*60)
    print(f"Total selected: {len(selected)} jobs")
    print("\nNext steps:")
    print("1. Review samples: python scripts/review_gold_standard_samples.py")
    print("2. Start annotation: python scripts/annotate_gold_standard.py")
