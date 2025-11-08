#!/usr/bin/env python3
"""
Map Gold Standard Annotations to ESCO
Uses the same ESCOMatcher3Layers used by Pipeline A and B for consistent comparison
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import psycopg2
import logging
from typing import List, Tuple
from extractor.esco_matcher_3layers import ESCOMatcher3Layers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456'
}

def get_unique_skills() -> List[Tuple[str, str]]:
    """Get unique skills from gold_standard_annotations grouped by skill_type"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT DISTINCT skill_text, skill_type
        FROM gold_standard_annotations
        ORDER BY skill_text
    """)

    skills = cur.fetchall()
    cur.close()
    conn.close()

    return skills

def update_esco_mapping(skill_text: str, esco_uri: str, esco_label: str, method: str, score: float):
    """Update ESCO mapping for all occurrences of a skill"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        UPDATE gold_standard_annotations
        SET esco_concept_uri = %s,
            esco_preferred_label = %s,
            esco_match_method = %s,
            esco_match_score = %s
        WHERE skill_text = %s
    """, (esco_uri, esco_label, method, score, skill_text))

    updated = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()

    return updated

def main():
    logger.info("="*80)
    logger.info("MAPPING GOLD STANDARD ANNOTATIONS TO ESCO")
    logger.info("="*80)

    # Initialize ESCO matcher (same as pipelines)
    logger.info("\n1. Initializing ESCOMatcher3Layers...")
    matcher = ESCOMatcher3Layers()

    # Get unique skills
    logger.info("\n2. Fetching unique skills from gold_standard_annotations...")
    unique_skills = get_unique_skills()
    logger.info(f"   Found {len(unique_skills)} unique skills")

    # Separate by type for reporting
    hard_skills = [s for s in unique_skills if s[1] == 'hard']
    soft_skills = [s for s in unique_skills if s[1] == 'soft']

    logger.info(f"   - Hard skills: {len(hard_skills)}")
    logger.info(f"   - Soft skills: {len(soft_skills)}")

    # Batch match all skills
    logger.info("\n3. Matching skills to ESCO (this may take a few minutes)...")
    skill_texts = [s[0] for s in unique_skills]
    matches = matcher.batch_match_skills(skill_texts)

    # Get stats
    stats = matcher.get_matching_stats(matches)

    logger.info("\n4. Matching Results:")
    logger.info(f"   Total skills:      {stats['total_skills']}")
    logger.info(f"   Matched to ESCO:   {stats['matched']} ({stats['match_rate']*100:.1f}%)")
    logger.info(f"   Emergent (no map): {stats['emergent_skills']} ({stats['emergent_rate']*100:.1f}%)")
    logger.info(f"\n   By method:")
    logger.info(f"   - Exact matches:    {stats['by_method']['exact']}")
    logger.info(f"   - Fuzzy matches:    {stats['by_method']['fuzzy']}")
    logger.info(f"   - Semantic matches: {stats['by_method']['semantic']}")

    # Update database
    logger.info("\n5. Updating database...")
    total_updated = 0
    matched_count = 0
    emergent_count = 0

    for skill_text, match in matches.items():
        if match:
            # Skill matched to ESCO
            updated = update_esco_mapping(
                skill_text,
                match.esco_skill_uri,
                match.matched_skill_text,  # Corrected attribute name
                match.match_method,
                match.confidence_score
            )
            total_updated += updated
            matched_count += 1
        else:
            # Emergent skill (no ESCO match)
            updated = update_esco_mapping(skill_text, None, None, 'emergent', 0.0)
            total_updated += updated
            emergent_count += 1

    logger.info(f"   ✅ Updated {total_updated} annotation records")
    logger.info(f"   - {matched_count} unique skills mapped to ESCO")
    logger.info(f"   - {emergent_count} unique skills marked as emergent")

    # Show sample matches
    logger.info("\n6. Sample ESCO Matches:")
    sample_matches = [(skill, match) for skill, match in matches.items() if match][:10]
    for skill, match in sample_matches:
        logger.info(f"   '{skill}' → '{match.matched_skill_text}' "
                   f"(method={match.match_method}, score={match.confidence_score:.3f})")

    # Show sample emergent skills
    logger.info("\n7. Sample Emergent Skills (No ESCO Match):")
    sample_emergent = [skill for skill, match in matches.items() if not match][:10]
    for skill in sample_emergent:
        logger.info(f"   '{skill}'")

    logger.info("\n" + "="*80)
    logger.info("✅ MAPPING COMPLETE")
    logger.info("="*80)

if __name__ == "__main__":
    main()
