#!/usr/bin/env python3
"""
Mini-audit: Compare ESCO remapping for 5 sample jobs
Pipeline A vs Pipeline B vs Manual annotations
"""

import sys
import psycopg2
from pathlib import Path
from fuzzywuzzy import fuzz
from typing import List, Dict, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.database import get_database_config

# Jobs to audit
SAMPLE_JOBS = [
    'e4769d6d-1e92-47e1-8395-64d31a2822af',  # Sr Back End Developer
    '0c0c39a9-5b3e-49d1-81b1-645d0ff8acbe',  # Senior DevOps
    '25f22487-ce0c-4117-a480-b648ea28c76a',  # Engineering - Always Hiring
    '39e75f82-c466-4721-9521-cf90a6e7ded1',  # Senior BI Developer
    '88448af3-4e15-4637-b34e-17578f583546',  # GenAI Core - Staff Software Engineer
]

def connect_db():
    db_config = get_database_config()
    return psycopg2.connect(**db_config)

def load_esco_skills(conn):
    """Load ESCO skills for matching"""
    query = "SELECT skill_uri, preferred_label_es FROM esco_skills WHERE preferred_label_es IS NOT NULL"
    cursor = conn.cursor()
    cursor.execute(query)
    esco_skills = {row[0]: row[1] for row in cursor.fetchall()}
    cursor.close()
    return esco_skills

def match_esco_old(skill_text: str, esco_skills: Dict, threshold=0.85) -> Tuple[str, float]:
    """OLD matching: with partial_ratio"""
    skill_text_lower = skill_text.lower().strip()
    best_uri = None
    best_score = 0.0

    for uri, label_es in esco_skills.items():
        label_lower = label_es.lower().strip()

        score_ratio = fuzz.ratio(skill_text_lower, label_lower) / 100.0
        score_partial = fuzz.partial_ratio(skill_text_lower, label_lower) / 100.0

        # OLD logic with partial_ratio
        if len(skill_text) <= 4:
            score = score_ratio
        elif len(label_lower) > len(skill_text) and len(skill_text) <= 6:
            score = max(score_ratio, score_partial)  # PROBLEM
        else:
            score = score_ratio

        if score > best_score:
            best_score = score
            best_uri = uri

    if best_score >= threshold:
        return best_uri, best_score
    return None, 0.0

def match_esco_new(skill_text: str, esco_skills: Dict, threshold=0.85) -> Tuple[str, float]:
    """NEW matching: ratio only"""
    skill_text_lower = skill_text.lower().strip()
    best_uri = None
    best_score = 0.0

    for uri, label_es in esco_skills.items():
        label_lower = label_es.lower().strip()
        score = fuzz.ratio(skill_text_lower, label_lower) / 100.0

        if score > best_score:
            best_score = score
            best_uri = uri

    if best_score >= threshold:
        return best_uri, best_score
    return None, 0.0

def audit_job(conn, job_id: str, esco_skills: Dict):
    """Audit a single job"""
    cursor = conn.cursor()

    # Get job title
    cursor.execute("SELECT title FROM raw_jobs WHERE job_id = %s", (job_id,))
    job_title = cursor.fetchone()[0]

    print(f"\n{'='*80}")
    print(f"JOB: {job_title[:70]}")
    print(f"ID: {job_id}")
    print(f"{'='*80}\n")

    # Get Manual annotations
    cursor.execute("""
        SELECT DISTINCT skill_text, esco_uri
        FROM gold_standard_annotations
        WHERE job_id = %s
        ORDER BY skill_text
    """, (job_id,))
    manual_skills = cursor.fetchall()

    # Get Pipeline A skills
    cursor.execute("""
        SELECT DISTINCT skill_text, esco_uri, extraction_method
        FROM extracted_skills
        WHERE job_id = %s
          AND skill_type = 'hard'
          AND extraction_method IN ('ner', 'regex')
        ORDER BY skill_text
    """, (job_id,))
    pipeline_a_skills = cursor.fetchall()

    # Get Pipeline B skills
    cursor.execute("""
        SELECT DISTINCT normalized_skill, esco_concept_uri, llm_confidence
        FROM enhanced_skills
        WHERE job_id = %s
          AND skill_type = 'hard'
        ORDER BY normalized_skill
    """, (job_id,))
    pipeline_b_skills = cursor.fetchall()

    cursor.close()

    # Audit each source
    print("🔵 MANUAL ANNOTATIONS")
    print("-" * 80)
    audit_skills(manual_skills, esco_skills, "Manual")

    print("\n🟢 PIPELINE A (NER + Regex)")
    print("-" * 80)
    audit_skills_extracted(pipeline_a_skills, esco_skills, "Pipeline A")

    print("\n🟡 PIPELINE B (LLM)")
    print("-" * 80)
    audit_skills_enhanced(pipeline_b_skills, esco_skills, "Pipeline B")

def audit_skills(skills, esco_skills, source_name):
    """Audit manual annotations"""
    changes = {'gained': 0, 'lost': 0, 'same': 0, 'no_match': 0}

    for skill_text, old_esco_uri in skills:
        old_esco_label = esco_skills.get(old_esco_uri, "???") if old_esco_uri else None
        new_esco_uri, new_score = match_esco_new(skill_text, esco_skills)
        new_esco_label = esco_skills.get(new_esco_uri) if new_esco_uri else None

        if old_esco_uri and new_esco_uri and old_esco_uri == new_esco_uri:
            changes['same'] += 1
            status = "✅ SAME"
        elif old_esco_uri and not new_esco_uri:
            changes['lost'] += 1
            status = "🔴 LOST"
            print(f"  {status} | {skill_text:20s} → WAS: {old_esco_label[:40]}")
        elif not old_esco_uri and new_esco_uri:
            changes['gained'] += 1
            status = "🟢 GAIN"
            print(f"  {status} | {skill_text:20s} → NOW: {new_esco_label[:40]} ({new_score:.2f})")
        elif old_esco_uri and new_esco_uri and old_esco_uri != new_esco_uri:
            changes['same'] += 1  # Consider as same for simplicity
            status = "🔄 CHNG"
            print(f"  {status} | {skill_text:20s} → FROM: {old_esco_label[:30]} TO: {new_esco_label[:30]}")
        else:
            changes['no_match'] += 1

    print(f"\n  Summary: Same={changes['same']}, Lost={changes['lost']}, Gained={changes['gained']}, NoMatch={changes['no_match']}")

def audit_skills_extracted(skills, esco_skills, source_name):
    """Audit extracted skills (Pipeline A)"""
    changes = {'gained': 0, 'lost': 0, 'same': 0, 'no_match': 0}

    for skill_text, old_esco_uri, method in skills:
        old_esco_label = esco_skills.get(old_esco_uri, "???") if old_esco_uri else None
        new_esco_uri, new_score = match_esco_new(skill_text, esco_skills)
        new_esco_label = esco_skills.get(new_esco_uri) if new_esco_uri else None

        if old_esco_uri and new_esco_uri and old_esco_uri == new_esco_uri:
            changes['same'] += 1
        elif old_esco_uri and not new_esco_uri:
            changes['lost'] += 1
            print(f"  🔴 LOST | {skill_text:20s} → WAS: {old_esco_label[:40]} ({method})")
        elif not old_esco_uri and new_esco_uri:
            changes['gained'] += 1
            print(f"  🟢 GAIN | {skill_text:20s} → NOW: {new_esco_label[:40]} ({new_score:.2f}, {method})")
        elif old_esco_uri and new_esco_uri and old_esco_uri != new_esco_uri:
            changes['same'] += 1
            print(f"  🔄 CHNG | {skill_text:20s} → FROM: {old_esco_label[:30]} TO: {new_esco_label[:30]} ({method})")
        else:
            changes['no_match'] += 1

    print(f"\n  Summary: Same={changes['same']}, Lost={changes['lost']}, Gained={changes['gained']}, NoMatch={changes['no_match']}")

def audit_skills_enhanced(skills, esco_skills, source_name):
    """Audit enhanced skills (Pipeline B) - already has LLM mapping"""
    print(f"  Pipeline B uses LLM for ESCO mapping (not fuzzy matching)")
    print(f"  Total skills with ESCO: {len([s for s in skills if s[1]])}")
    print(f"  Sample skills:")
    for skill_text, esco_uri, confidence in skills[:5]:
        if esco_uri:
            esco_label = esco_skills.get(esco_uri, "???")
            print(f"    - {skill_text:25s} → {esco_label[:40]} (conf: {confidence:.2f})")

def main():
    conn = connect_db()
    print("✅ Connected to database\n")

    print("Loading ESCO skills...")
    esco_skills = load_esco_skills(conn)
    print(f"✅ Loaded {len(esco_skills)} ESCO skills\n")

    for job_id in SAMPLE_JOBS:
        try:
            audit_job(conn, job_id, esco_skills)
        except Exception as e:
            print(f"❌ Error auditing {job_id}: {e}")

    conn.close()
    print("\n" + "="*80)
    print("✅ AUDIT COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
