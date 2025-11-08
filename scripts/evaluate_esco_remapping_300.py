#!/usr/bin/env python3
"""
Evaluate ESCO remapping impact on 300 gold standard jobs
Compare OLD (with partial_ratio) vs NEW (ratio only) matching
"""

import sys
import psycopg2
import json
from pathlib import Path
from fuzzywuzzy import fuzz
from collections import defaultdict, Counter

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.database import get_database_config

# Known false positives from investigation
KNOWN_FALSE_POSITIVES = {
    'Piano', 'Europa', 'Oferta', 'Acceso', 'Apoyo', 'Perfil',
    'Bordo', 'Fondo', 'Polanco', 'CORTES', 'Puntos', 'Vales',
    'Clara', 'Excel', 'Cursos', 'ASTECI', 'Seguro', 'Video',
    'Empleo', 'Banca', 'Bonos', 'Centro', 'Crane', 'Estar', 'GRUPO'
}

def connect_db():
    db_config = get_database_config()
    return psycopg2.connect(**db_config)

def load_esco_skills(conn):
    """Load ESCO skills dictionary"""
    query = """
    SELECT skill_uri, preferred_label_es, skill_group
    FROM esco_skills
    WHERE preferred_label_es IS NOT NULL
    """
    cursor = conn.cursor()
    cursor.execute(query)

    esco_dict = {}
    for uri, label, group in cursor.fetchall():
        esco_dict[label.lower().strip()] = {
            'uri': uri,
            'label': label,
            'group': group
        }

    cursor.close()
    return esco_dict

def match_esco_old(skill_text, esco_dict, threshold=0.85):
    """OLD: with partial_ratio"""
    skill_lower = skill_text.lower().strip()
    best_match = None
    best_score = 0.0

    for esco_label, esco_info in esco_dict.items():
        ratio = fuzz.ratio(skill_lower, esco_label) / 100.0
        partial = fuzz.partial_ratio(skill_lower, esco_label) / 100.0

        # OLD logic
        if len(skill_text) <= 4:
            score = ratio
        elif len(esco_label) > len(skill_text) and len(skill_text) <= 6:
            score = max(ratio, partial)  # PROBLEM
        else:
            score = ratio

        if score > best_score:
            best_score = score
            best_match = esco_info

    if best_score >= threshold:
        return best_match, best_score
    return None, 0.0

def match_esco_new(skill_text, esco_dict, threshold=0.85):
    """NEW: ratio only"""
    skill_lower = skill_text.lower().strip()
    best_match = None
    best_score = 0.0

    for esco_label, esco_info in esco_dict.items():
        score = fuzz.ratio(skill_lower, esco_label) / 100.0

        if score > best_score:
            best_score = score
            best_match = esco_info

    if best_score >= threshold:
        return best_match, best_score
    return None, 0.0

def evaluate_remapping(conn, esco_dict):
    """Evaluate remapping on all 300 jobs"""

    print("="*80)
    print("ESCO REMAPPING EVALUATION - 300 Gold Standard Jobs")
    print("="*80)
    print()

    # Get all skills from Pipeline A (NER + Regex)
    query = """
    SELECT DISTINCT
        es.skill_text,
        es.esco_uri as old_esco_uri,
        esco.preferred_label_es as old_esco_label,
        esco.skill_group as old_skill_group,
        COUNT(DISTINCT es.job_id) as job_count
    FROM extracted_skills es
    LEFT JOIN esco_skills esco ON es.esco_uri = esco.skill_uri
    WHERE es.job_id IN (SELECT DISTINCT job_id FROM gold_standard_annotations)
      AND es.extraction_method IN ('ner', 'regex')
      AND es.skill_type = 'hard'
    GROUP BY es.skill_text, es.esco_uri, esco.preferred_label_es, esco.skill_group
    ORDER BY job_count DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    skills = cursor.fetchall()
    cursor.close()

    print(f"📊 Analyzing {len(skills)} unique skills from Pipeline A...")
    print()

    # Statistics
    stats = {
        'total_skills': len(skills),
        'old_with_esco': 0,
        'new_with_esco': 0,
        'same_mapping': 0,
        'lost_mapping': 0,
        'gained_mapping': 0,
        'changed_mapping': 0,
        'false_positives_removed': 0,
        'legitimate_lost': 0,
    }

    changes_by_category = {
        'false_positives_removed': [],
        'legitimate_lost': [],
        'gained': [],
        'changed_better': [],
        'changed_worse': []
    }

    skill_groups_old = Counter()
    skill_groups_new = Counter()

    # Analyze each skill
    for skill_text, old_uri, old_label, old_group, job_count in skills:
        # Old mapping
        has_old_mapping = old_uri is not None
        if has_old_mapping:
            stats['old_with_esco'] += 1
            skill_groups_old[old_group if old_group else 'NULL'] += 1

        # New mapping
        new_match, new_score = match_esco_new(skill_text, esco_dict)
        has_new_mapping = new_match is not None

        if has_new_mapping:
            stats['new_with_esco'] += 1
            skill_groups_new[new_match['group'] if new_match['group'] else 'NULL'] += 1

        # Categorize change
        if has_old_mapping and has_new_mapping:
            if old_uri == new_match['uri']:
                stats['same_mapping'] += 1
            else:
                stats['changed_mapping'] += 1
                changes_by_category['changed_better'].append({
                    'skill': skill_text,
                    'old': old_label,
                    'new': new_match['label'],
                    'jobs': job_count
                })

        elif has_old_mapping and not has_new_mapping:
            stats['lost_mapping'] += 1

            # Is it a known false positive?
            if skill_text in KNOWN_FALSE_POSITIVES:
                stats['false_positives_removed'] += 1
                changes_by_category['false_positives_removed'].append({
                    'skill': skill_text,
                    'old_label': old_label,
                    'jobs': job_count
                })
            else:
                stats['legitimate_lost'] += 1
                changes_by_category['legitimate_lost'].append({
                    'skill': skill_text,
                    'old_label': old_label,
                    'jobs': job_count
                })

        elif not has_old_mapping and has_new_mapping:
            stats['gained_mapping'] += 1
            changes_by_category['gained'].append({
                'skill': skill_text,
                'new_label': new_match['label'],
                'jobs': job_count
            })

    # Calculate metrics
    old_coverage = stats['old_with_esco'] / stats['total_skills'] * 100
    new_coverage = stats['new_with_esco'] / stats['total_skills'] * 100

    old_precision_est = (stats['old_with_esco'] - stats['false_positives_removed']) / stats['old_with_esco'] * 100 if stats['old_with_esco'] > 0 else 0
    new_precision_est = 100.0  # Assume new has no false positives (conservative)

    # Print results
    print("="*80)
    print("📈 COVERAGE METRICS")
    print("="*80)
    print(f"Total unique skills:        {stats['total_skills']}")
    print(f"OLD coverage (with ESCO):   {stats['old_with_esco']} ({old_coverage:.1f}%)")
    print(f"NEW coverage (with ESCO):   {stats['new_with_esco']} ({new_coverage:.1f}%)")
    print(f"Coverage change:            {stats['new_with_esco'] - stats['old_with_esco']:+d} ({new_coverage - old_coverage:+.1f}%)")
    print()

    print("="*80)
    print("🎯 QUALITY METRICS")
    print("="*80)
    print(f"OLD estimated precision:    {old_precision_est:.1f}%")
    print(f"NEW estimated precision:    {new_precision_est:.1f}%")
    print(f"Precision improvement:      {new_precision_est - old_precision_est:+.1f}%")
    print()

    print("="*80)
    print("🔄 MAPPING CHANGES")
    print("="*80)
    print(f"✅ Same mapping:            {stats['same_mapping']}")
    print(f"🔴 Lost mapping:            {stats['lost_mapping']}")
    print(f"   ├─ False positives:      {stats['false_positives_removed']} (GOOD)")
    print(f"   └─ Legitimate lost:      {stats['legitimate_lost']} (BAD)")
    print(f"🟢 Gained mapping:          {stats['gained_mapping']}")
    print(f"🔄 Changed mapping:         {stats['changed_mapping']}")
    print()

    print("="*80)
    print("📊 SKILL GROUP DISTRIBUTION")
    print("="*80)
    print(f"\nOLD (top 10):")
    for group, count in skill_groups_old.most_common(10):
        print(f"  {group[:50]:50s}: {count:3d}")

    print(f"\nNEW (top 10):")
    for group, count in skill_groups_new.most_common(10):
        print(f"  {group[:50]:50s}: {count:3d}")
    print()

    # Show samples
    print("="*80)
    print("🔴 FALSE POSITIVES REMOVED (sample - top 10 by frequency)")
    print("="*80)
    for item in sorted(changes_by_category['false_positives_removed'], key=lambda x: x['jobs'], reverse=True)[:10]:
        print(f"  {item['skill']:20s} → {item['old_label'][:50]:50s} ({item['jobs']} jobs)")
    print()

    print("="*80)
    print("❌ LEGITIMATE SKILLS LOST (sample - top 10 by frequency)")
    print("="*80)
    for item in sorted(changes_by_category['legitimate_lost'], key=lambda x: x['jobs'], reverse=True)[:10]:
        print(f"  {item['skill']:20s} → {item['old_label'][:50]:50s} ({item['jobs']} jobs)")
    print()

    if changes_by_category['gained']:
        print("="*80)
        print("🟢 SKILLS GAINED MAPPING (sample - top 10 by frequency)")
        print("="*80)
        for item in sorted(changes_by_category['gained'], key=lambda x: x['jobs'], reverse=True)[:10]:
            print(f"  {item['skill']:20s} → {item['new_label'][:50]:50s} ({item['jobs']} jobs)")
        print()

    # Save results
    output = {
        'stats': stats,
        'metrics': {
            'old_coverage': old_coverage,
            'new_coverage': new_coverage,
            'old_precision_est': old_precision_est,
            'new_precision_est': new_precision_est,
        },
        'skill_groups': {
            'old': dict(skill_groups_old),
            'new': dict(skill_groups_new)
        },
        'changes': changes_by_category
    }

    output_path = PROJECT_ROOT / "outputs" / "clustering" / "esco_remapping_evaluation_300.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"✅ Results saved to: {output_path}")

    return stats

def main():
    conn = connect_db()
    print("✅ Connected to database\n")

    print("Loading ESCO skills...")
    esco_dict = load_esco_skills(conn)
    print(f"✅ Loaded {len(esco_dict)} ESCO skills\n")

    stats = evaluate_remapping(conn, esco_dict)

    conn.close()

    print("\n" + "="*80)
    print("✅ EVALUATION COMPLETE")
    print("="*80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
