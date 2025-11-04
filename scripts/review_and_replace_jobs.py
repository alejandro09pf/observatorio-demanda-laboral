#!/usr/bin/env python3
"""
Interactive job review and replacement script.

Shows each of the 300 selected jobs one by one.
User can:
- Accept (keep the job)
- Reject and automatically replace with best available candidate
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from config.settings import get_settings
import re

def is_job_acceptable(title, desc, req, role):
    """Quick heuristic check if job looks acceptable."""
    title_lower = title.lower()
    combined = (title + " " + desc + " " + req).lower()

    # Red flags
    red_flags = [
        'manager' in title_lower and 'engineering' in title_lower,
        'director' in title_lower,
        'gerente' in title_lower,
        'bi engineer' in title_lower,
        'business intelligence' in title_lower,
        'mechanical' in title_lower,
        'chemical' in title_lower,
        'civil engineer' in title_lower,
        role == 'other'
    ]

    if any(red_flags):
        return False, "Contains red flag keywords"

    # Check if it's actually a tech role
    tech_keywords = ['python', 'java', 'javascript', 'react', 'angular', 'node',
                     'aws', 'docker', 'kubernetes', 'sql', 'api', 'backend',
                     'frontend', 'fullstack', 'devops', 'mobile', 'ios', 'android']

    tech_count = sum(1 for kw in tech_keywords if kw in combined)

    if tech_count < 2:
        return False, f"Only {tech_count} tech keywords found"

    # Check description length
    total_len = len(desc) + len(req)
    if total_len < 800:
        return False, f"Too short ({total_len} chars)"

    return True, "Looks good"


def find_replacement(cursor, country, language, role, excluded_ids):
    """Find best replacement job matching the criteria."""
    cursor.execute("""
        SELECT job_id, title, description, requirements, LENGTH(description) + LENGTH(requirements)
        FROM raw_jobs
        WHERE country = %s
          AND language = %s
          AND is_usable = TRUE
          AND is_gold_standard = FALSE
          AND job_id NOT IN (SELECT unnest(%s::uuid[]))
          AND (LENGTH(description) + LENGTH(requirements)) > 1000
          -- Tech role keywords
          AND (
              title ILIKE '%%developer%%' OR title ILIKE '%%engineer%%'
              OR title ILIKE '%%desarrollador%%' OR title ILIKE '%%programador%%'
          )
          -- Exclude non-tech
          AND title NOT ILIKE '%%manager%%'
          AND title NOT ILIKE '%%director%%'
          AND title NOT ILIKE '%%gerente%%'
          AND title NOT ILIKE '%%bi engineer%%'
          AND title NOT ILIKE '%%mechanical%%'
          AND title NOT ILIKE '%%chemical%%'
          AND title NOT ILIKE '%%civil engineer%%'
        ORDER BY LENGTH(description) + LENGTH(requirements) DESC
        LIMIT 10
    """, (country, language, excluded_ids))

    candidates = cursor.fetchall()
    return candidates if candidates else []


def review_jobs():
    """Main review loop."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Get all 300 selected jobs
    cursor.execute("""
        SELECT job_id, title, country, language, gold_standard_role_type,
               description, requirements
        FROM raw_jobs
        WHERE is_gold_standard = TRUE
        ORDER BY country, language, gold_standard_role_type, title
    """)

    jobs = cursor.fetchall()
    total = len(jobs)

    print(f"\\n{'='*80}")
    print(f"REVIEWING {total} GOLD STANDARD JOBS")
    print(f"{'='*80}\\n")

    replaced_count = 0
    excluded_ids = []

    for i, (job_id, title, country, lang, role, desc, req) in enumerate(jobs, 1):
        print(f"\\n{'='*80}")
        print(f"JOB {i}/{total}")
        print(f"{'='*80}")
        print(f"Country: {country}, Language: {lang}, Role: {role}")
        print(f"Title: {title}")
        print(f"Length: {len(desc) + len(req)} chars")

        # Quick auto-check
        acceptable, reason = is_job_acceptable(title, desc, req, role)

        if acceptable:
            print(f"\\n✅ AUTO-ACCEPT: {reason}")
            excluded_ids.append(str(job_id))
            continue

        # Show details for manual review
        print(f"\\n⚠️  FLAGGED: {reason}")
        print(f"\\nDescription preview (first 400 chars):")
        print(desc[:400])
        if len(desc) > 400:
            print(f"[... {len(desc) - 400} more chars ...]")

        print(f"\\nRequirements preview (first 300 chars):")
        print(req[:300])
        if len(req) > 300:
            print(f"[... {len(req) - 300} more chars ...]")

        # Decision
        print(f"\\n[A]ccept this job  |  [R]eplace with better candidate  |  [Q]uit")
        choice = input("Your choice: ").strip().lower()

        if choice == 'q':
            print("\\nExiting review...")
            break
        elif choice == 'r':
            print(f"\\nSearching for replacement ({country} {lang})...")

            # Find replacement
            candidates = find_replacement(cursor, country, lang, role, excluded_ids + [str(job_id)])

            if not candidates:
                print("❌ No suitable replacement found. Keeping original.")
                excluded_ids.append(str(job_id))
                continue

            print(f"\\nFound {len(candidates)} replacement candidates:")
            for idx, (cand_id, cand_title, cand_desc, cand_req, cand_len) in enumerate(candidates, 1):
                print(f"{idx}. {cand_title[:70]} ({cand_len} chars)")

            print(f"\\nSelect replacement (1-{len(candidates)}) or [C]ancel:")
            repl_choice = input("Your choice: ").strip()

            if repl_choice.lower() == 'c':
                print("Cancelled. Keeping original.")
                excluded_ids.append(str(job_id))
                continue

            try:
                repl_idx = int(repl_choice) - 1
                if 0 <= repl_idx < len(candidates):
                    new_id, new_title, _, _, _ = candidates[repl_idx]

                    # Swap in database
                    cursor.execute("""
                        UPDATE raw_jobs
                        SET is_gold_standard = FALSE,
                            gold_standard_role_type = NULL,
                            gold_standard_seniority = NULL
                        WHERE job_id = %s
                    """, (job_id,))

                    cursor.execute("""
                        UPDATE raw_jobs
                        SET is_gold_standard = TRUE,
                            gold_standard_role_type = %s,
                            gold_standard_seniority = %s
                        WHERE job_id = %s
                    """, (role, 'mid', new_id))  # Default to mid seniority for replacements

                    conn.commit()

                    print(f"✅ REPLACED: '{title[:50]}...' → '{new_title[:50]}...'")
                    excluded_ids.append(str(new_id))
                    replaced_count += 1
                else:
                    print("Invalid selection. Keeping original.")
                    excluded_ids.append(str(job_id))
            except ValueError:
                print("Invalid input. Keeping original.")
                excluded_ids.append(str(job_id))
        else:  # Accept
            print("✅ Accepted")
            excluded_ids.append(str(job_id))

    cursor.close()
    conn.close()

    print(f"\\n{'='*80}")
    print(f"REVIEW COMPLETE")
    print(f"{'='*80}")
    print(f"Reviewed: {i}/{total} jobs")
    print(f"Replaced: {replaced_count} jobs")
    print(f"{'='*80}\\n")


if __name__ == "__main__":
    review_jobs()
