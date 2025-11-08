#!/usr/bin/env python3
"""
Simple test to compare fuzzy matching with and without partial_ratio.
This focuses on the immediate problem: partial_ratio causing false positives.
"""

import json
import sys
import psycopg2
from pathlib import Path
from typing import List, Dict, Tuple
from fuzzywuzzy import fuzz

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.database import get_database_config


def connect_db():
    """Connect to database"""
    db_config = get_database_config()
    conn = psycopg2.connect(**db_config)
    print(f"✅ Connected to database: {db_config['database']}")
    return conn


def load_esco_skills(conn):
    """Load all ESCO skills from database"""
    query = """
    SELECT
        skill_uri,
        preferred_label_es,
        skill_group
    FROM esco_skills
    WHERE preferred_label_es IS NOT NULL
    """

    cursor = conn.cursor()
    cursor.execute(query)

    esco_skills = []
    for row in cursor.fetchall():
        esco_skills.append({
            'uri': row[0],
            'label_es': row[1],
            'skill_group': row[2]
        })

    cursor.close()
    print(f"✅ Loaded {len(esco_skills)} ESCO skills\n")
    return esco_skills


def match_with_partial_ratio(skill_text: str, esco_skills: List[Dict], threshold: float = 0.85) -> Tuple[str, float, str]:
    """
    BASELINE: Current approach with ratio + partial_ratio
    """
    skill_text_lower = skill_text.lower().strip()
    best_match = None
    best_score = 0.0
    best_uri = None

    for esco in esco_skills:
        label_es = esco['label_es'].lower().strip()

        # Calculate scores
        score_ratio = fuzz.ratio(skill_text_lower, label_es) / 100.0
        score_partial = fuzz.partial_ratio(skill_text_lower, label_es) / 100.0

        # Current logic from esco_matcher_3layers.py
        if len(skill_text) <= 4:
            score = score_ratio
        elif len(label_es) > len(skill_text) and len(skill_text) <= 6:
            score = max(score_ratio, score_partial)  # PROBLEM HERE
        else:
            score = score_ratio

        if score > best_score:
            best_score = score
            best_match = esco['label_es']
            best_uri = esco['uri']

    if best_score >= threshold:
        return best_match, best_score, best_uri
    return None, 0.0, None


def match_without_partial_ratio(skill_text: str, esco_skills: List[Dict], threshold: float = 0.85) -> Tuple[str, float, str]:
    """
    IMPROVED: Fuzzy matching WITHOUT partial_ratio (ratio only)
    """
    skill_text_lower = skill_text.lower().strip()
    best_match = None
    best_score = 0.0
    best_uri = None

    for esco in esco_skills:
        label_es = esco['label_es'].lower().strip()

        # Only use ratio score (no partial_ratio)
        score = fuzz.ratio(skill_text_lower, label_es) / 100.0

        if score > best_score:
            best_score = score
            best_match = esco['label_es']
            best_uri = esco['uri']

    if best_score >= threshold:
        return best_match, best_score, best_uri
    return None, 0.0, None


def evaluate_approach(approach_name: str, match_func, test_cases: List[Dict], esco_skills: List[Dict]) -> Dict:
    """
    Evaluate a matching approach on test cases
    """
    print(f"{'='*70}")
    print(f"Testing: {approach_name}")
    print(f"{'='*70}\n")

    results = {
        'true_positives': 0,
        'false_positives': 0,
        'true_negatives': 0,
        'false_negatives': 0,
        'details': []
    }

    for case in test_cases:
        skill_text = case['extracted_skill']
        expected_match = case['expected_match']

        # Run matching
        esco_label, score, uri = match_func(skill_text, esco_skills)
        found_match = esco_label is not None

        # Classify result
        if expected_match and found_match:
            results['true_positives'] += 1
            outcome = "✅ TP"
        elif expected_match and not found_match:
            results['false_negatives'] += 1
            outcome = "❌ FN"
        elif not expected_match and found_match:
            results['false_positives'] += 1
            outcome = "❌ FP"
        else:  # not expected_match and not found_match
            results['true_negatives'] += 1
            outcome = "✅ TN"

        results['details'].append({
            'case_id': case['id'],
            'skill': skill_text,
            'expected': expected_match,
            'found': found_match,
            'esco_label': esco_label,
            'score': score,
            'outcome': outcome
        })

        # Print interesting cases
        if (not expected_match and found_match) or (expected_match and not found_match):
            print(f"{outcome} | {skill_text:15s} → {esco_label if esco_label else 'NO MATCH'} ({score:.2f})")

    # Calculate metrics
    tp = results['true_positives']
    fp = results['false_positives']
    tn = results['true_negatives']
    fn = results['false_negatives']

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
    accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0

    results['metrics'] = {
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'accuracy': accuracy
    }

    # Print summary
    print(f"\n📊 Results:")
    print(f"  True Positives:  {tp}")
    print(f"  False Positives: {fp} 🔴")
    print(f"  True Negatives:  {tn}")
    print(f"  False Negatives: {fn} 🔴")
    print(f"\n📈 Metrics:")
    print(f"  Precision: {precision:.3f}")
    print(f"  Recall:    {recall:.3f}")
    print(f"  F1-Score:  {f1:.3f}")
    print(f"  Accuracy:  {accuracy:.3f}\n")

    return results


def main():
    print("="*70)
    print("FUZZY MATCHING COMPARISON: WITH vs WITHOUT partial_ratio")
    print("="*70)
    print()

    # Load validation dataset
    validation_dataset = PROJECT_ROOT / "tests" / "matching_validation_dataset.json"

    if not validation_dataset.exists():
        print(f"❌ Error: Validation dataset not found at {validation_dataset}")
        return 1

    with open(validation_dataset, 'r', encoding='utf-8') as f:
        data = json.load(f)

    test_cases = data['cases']
    print(f"✅ Loaded {len(test_cases)} test cases")
    print(f"   - Expected good matches: {data['good_matches']}")
    print(f"   - Expected bad matches: {data['bad_matches']}\n")

    # Connect and load ESCO
    conn = connect_db()
    esco_skills = load_esco_skills(conn)

    # Run experiments
    print("\n" + "="*70)
    print("EXPERIMENT 1: BASELINE (with partial_ratio)")
    print("="*70 + "\n")

    baseline_results = evaluate_approach(
        "Baseline (ratio + partial_ratio)",
        match_with_partial_ratio,
        test_cases,
        esco_skills
    )

    print("\n" + "="*70)
    print("EXPERIMENT 2: IMPROVED (ratio only)")
    print("="*70 + "\n")

    improved_results = evaluate_approach(
        "Improved (ratio only, NO partial_ratio)",
        match_without_partial_ratio,
        test_cases,
        esco_skills
    )

    # Compare results
    print("\n" + "="*70)
    print("COMPARATIVE SUMMARY")
    print("="*70 + "\n")

    print(f"{'Metric':<20} {'Baseline (+ partial)':<25} {'Improved (no partial)':<25} {'Improvement':<15}")
    print("-" * 85)

    for metric in ['precision', 'recall', 'f1_score', 'accuracy']:
        baseline_val = baseline_results['metrics'][metric]
        improved_val = improved_results['metrics'][metric]
        diff = improved_val - baseline_val
        diff_str = f"+{diff:.3f}" if diff > 0 else f"{diff:.3f}"
        diff_emoji = "📈" if diff > 0 else ("📉" if diff < 0 else "➡️")

        print(f"{metric.replace('_', ' ').title():<20} {baseline_val:<25.3f} {improved_val:<25.3f} {diff_str:<10} {diff_emoji}")

    print("\n" + "-" * 85)
    print(f"{'False Positives':<20} {baseline_results['false_positives']:<25} {improved_results['false_positives']:<25} {improved_results['false_positives'] - baseline_results['false_positives']:<10} {'✅' if improved_results['false_positives'] < baseline_results['false_positives'] else '❌'}")
    print(f"{'False Negatives':<20} {baseline_results['false_negatives']:<25} {improved_results['false_negatives']:<25} {improved_results['false_negatives'] - baseline_results['false_negatives']:<10} {'❌' if improved_results['false_negatives'] > baseline_results['false_negatives'] else '✅'}")

    # Save results
    output_path = PROJECT_ROOT / "outputs" / "clustering" / "fuzzy_matching_comparison.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_results = {
        'baseline': baseline_results,
        'improved': improved_results,
        'comparison': {
            'precision_improvement': improved_results['metrics']['precision'] - baseline_results['metrics']['precision'],
            'recall_improvement': improved_results['metrics']['recall'] - baseline_results['metrics']['recall'],
            'f1_improvement': improved_results['metrics']['f1_score'] - baseline_results['metrics']['f1_score'],
            'accuracy_improvement': improved_results['metrics']['accuracy'] - baseline_results['metrics']['accuracy'],
            'false_positives_reduction': baseline_results['false_positives'] - improved_results['false_positives'],
            'false_negatives_increase': improved_results['false_negatives'] - baseline_results['false_negatives']
        }
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Results saved to: {output_path}\n")

    # Close connection
    conn.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
