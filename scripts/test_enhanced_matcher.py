#!/usr/bin/env python3
"""
Test Enhanced ESCO Matcher vs Current Matcher

Compares mapping results between:
- Current matcher (exact + fuzzy): ~10% coverage
- Enhanced matcher (exact + manual_dict + fuzzy + substring): expected ~40-60% coverage

Output: CSV + JSON files for manual review
NO DATABASE MODIFICATIONS
"""

import sys
import os
import json
import csv
from pathlib import Path
import psycopg2
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.extractor.esco_matcher_enhanced import ESCOMatcherEnhanced
from src.config import get_settings

def get_gold_standard_skills():
    """Get all unique hard skills from gold standard annotations."""
    settings = get_settings()
    db_url = settings.database_url

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT skill_text
        FROM gold_standard_annotations
        WHERE skill_type = 'hard'
        ORDER BY skill_text
    """)

    skills = [row[0] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return skills


def main():
    print("="*80)
    print("ENHANCED ESCO MATCHER - EXPERIMENTAL TEST")
    print("="*80)
    print()

    # Create output directory
    output_dir = Path("outputs/matcher_comparison")
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Get skills from gold standard
    print("📥 Loading skills from gold_standard_annotations...")
    skills = get_gold_standard_skills()
    print(f"   Loaded {len(skills):,} unique hard skills")
    print()

    # Known baseline from current matcher
    baseline_mapped = 198  # From our query earlier
    baseline_rate = 10.34  # 198/1914 = 10.34%

    print("📊 BASELINE (Current Matcher):")
    print(f"   Total skills: {len(skills):,}")
    print(f"   Mapped: {baseline_mapped} ({baseline_rate:.2f}%)")
    print(f"   Unmapped: {len(skills) - baseline_mapped} ({100 - baseline_rate:.2f}%)")
    print()

    # Run enhanced matcher
    print("🚀 Running ENHANCED matcher...")
    matcher = ESCOMatcherEnhanced()
    matches = matcher.batch_match_skills(skills)

    # Get stats
    stats = matcher.get_matching_stats(matches)

    print()
    print("="*80)
    print("RESULTS - ENHANCED MATCHER")
    print("="*80)
    print(f"Total skills:        {stats['total_skills']:,}")
    print(f"Mapped:              {stats['matched']:,} ({stats['match_rate']*100:.2f}%)")
    print(f"Unmapped (emergent): {stats['emergent_skills']:,} ({stats['emergent_rate']*100:.2f}%)")
    print()
    print("By method:")
    print(f"  - Exact:           {stats['by_method']['exact']:,}")
    print(f"  - Manual Dict:     {stats['by_method']['manual_dict']:,}")
    print(f"  - Fuzzy:           {stats['by_method']['fuzzy']:,}")
    print(f"  - Substring:       {stats['by_method']['substring']:,}")
    print()

    # Calculate improvement
    improvement = stats['matched'] - baseline_mapped
    improvement_pct = ((stats['matched'] / baseline_mapped) - 1) * 100 if baseline_mapped > 0 else 0

    print("="*80)
    print("IMPROVEMENT vs BASELINE")
    print("="*80)
    print(f"New mappings:     +{improvement} skills")
    print(f"Coverage increase: {stats['match_rate']*100 - baseline_rate:.2f} percentage points")
    print(f"Relative improvement: {improvement_pct:.1f}% more skills mapped")
    print()

    # Prepare data for export
    results = []
    new_mappings = []

    for skill_text, match in matches.items():
        if match:
            result = {
                'skill_text': skill_text,
                'matched': True,
                'esco_label': match.matched_skill_text,
                'esco_uri': match.esco_skill_uri,
                'confidence': match.confidence_score,
                'method': match.match_method,
                'skill_type': match.skill_type,
                'skill_group': match.skill_group
            }
            results.append(result)

            # Track new mappings (anything not from exact match is likely new)
            if match.match_method in ['manual_dict', 'substring']:
                new_mappings.append(result)
        else:
            results.append({
                'skill_text': skill_text,
                'matched': False,
                'esco_label': None,
                'esco_uri': None,
                'confidence': 0.0,
                'method': 'unmapped',
                'skill_type': None,
                'skill_group': None
            })

    # Export CSV
    csv_path = output_dir / f"enhanced_matcher_results_{timestamp}.csv"
    print(f"💾 Saving results to CSV: {csv_path}")

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'skill_text', 'matched', 'esco_label', 'esco_uri',
            'confidence', 'method', 'skill_type', 'skill_group'
        ])
        writer.writeheader()
        writer.writerows(results)

    # Export JSON with full report
    json_path = output_dir / f"enhanced_matcher_report_{timestamp}.json"
    print(f"💾 Saving report to JSON: {json_path}")

    report = {
        'timestamp': timestamp,
        'baseline': {
            'total_skills': len(skills),
            'mapped': baseline_mapped,
            'match_rate': baseline_rate / 100,
            'unmapped': len(skills) - baseline_mapped
        },
        'enhanced': {
            'total_skills': stats['total_skills'],
            'mapped': stats['matched'],
            'match_rate': stats['match_rate'],
            'unmapped': stats['emergent_skills'],
            'by_method': stats['by_method']
        },
        'improvement': {
            'new_mappings_count': improvement,
            'coverage_increase_pct': stats['match_rate']*100 - baseline_rate,
            'relative_improvement_pct': improvement_pct
        },
        'sample_new_mappings': new_mappings[:50]  # Top 50 new mappings for review
    }

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Show sample of new mappings
    print()
    print("="*80)
    print(f"SAMPLE NEW MAPPINGS (Top 30 from manual_dict + substring)")
    print("="*80)
    print()

    for i, mapping in enumerate(new_mappings[:30], 1):
        print(f"{i:2d}. '{mapping['skill_text']}' → '{mapping['esco_label']}'")
        print(f"    Method: {mapping['method']}, Confidence: {mapping['confidence']:.2f}")
        print()

    print("="*80)
    print("✅ TEST COMPLETE")
    print("="*80)
    print(f"Results saved to:")
    print(f"  - CSV: {csv_path}")
    print(f"  - JSON: {json_path}")
    print()


if __name__ == '__main__':
    main()
