#!/usr/bin/env python3
"""
Test different ESCO matching approaches against validation dataset.

Compares:
- Baseline: Current fuzzy matching (ratio + partial_ratio)
- Approach A: Fuzzy without partial_ratio (ratio only)
- Approach B: E5 embeddings with threshold
- Approach C: E5 embeddings + ESCO descriptions + domain filter
"""

import json
import sys
import psycopg2
from pathlib import Path
from typing import List, Dict, Tuple
from fuzzywuzzy import fuzz
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from config.database import get_database_config


class MatchingTester:
    def __init__(self):
        self.db_config = get_database_config()
        self.conn = None
        self.esco_skills = []
        self.model = None

    def connect_db(self):
        """Connect to database"""
        self.conn = psycopg2.connect(**self.db_config)
        print(f"✅ Connected to database: {self.db_config['database']}")

    def load_esco_skills(self):
        """Load all ESCO skills from database"""
        query = """
        SELECT
            skill_uri,
            preferred_label_es,
            preferred_label_en,
            description_es,
            description_en,
            skill_group,
            skill_type
        FROM esco_skills
        WHERE preferred_label_es IS NOT NULL
        """

        cursor = self.conn.cursor()
        cursor.execute(query)

        self.esco_skills = []
        for row in cursor.fetchall():
            self.esco_skills.append({
                'uri': row[0],
                'label_es': row[1],
                'label_en': row[2],
                'desc_es': row[3],
                'desc_en': row[4],
                'skill_group': row[5],
                'skill_type': row[6]
            })

        cursor.close()
        print(f"✅ Loaded {len(self.esco_skills)} ESCO skills")

    def load_embedding_model(self):
        """Load E5 multilingual embedding model"""
        print("🔄 Loading E5 multilingual model...")
        self.model = SentenceTransformer('intfloat/multilingual-e5-large')
        print("✅ E5 model loaded")

    def baseline_match(self, skill_text: str, threshold: float = 0.85) -> Tuple[str, float, str]:
        """
        Baseline: Current approach with ratio + partial_ratio
        Returns: (esco_label, score, uri)
        """
        skill_text_lower = skill_text.lower().strip()
        best_match = None
        best_score = 0.0
        best_uri = None

        for esco in self.esco_skills:
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

    def approach_a_match(self, skill_text: str, threshold: float = 0.85) -> Tuple[str, float, str]:
        """
        Approach A: Fuzzy matching WITHOUT partial_ratio (ratio only)
        Returns: (esco_label, score, uri)
        """
        skill_text_lower = skill_text.lower().strip()
        best_match = None
        best_score = 0.0
        best_uri = None

        for esco in self.esco_skills:
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

    def approach_b_match(self, skill_text: str, threshold: float = 0.75) -> Tuple[str, float, str]:
        """
        Approach B: E5 embeddings with cosine similarity
        Returns: (esco_label, score, uri)
        """
        if self.model is None:
            self.load_embedding_model()

        # Generate embedding for input skill
        skill_embedding = self.model.encode([f"query: {skill_text}"], normalize_embeddings=True)

        best_match = None
        best_score = 0.0
        best_uri = None

        for esco in self.esco_skills:
            # Use label for embedding
            label = esco['label_es']
            label_embedding = self.model.encode([f"passage: {label}"], normalize_embeddings=True)

            # Cosine similarity
            similarity = cosine_similarity(skill_embedding, label_embedding)[0][0]

            if similarity > best_score:
                best_score = similarity
                best_match = label
                best_uri = esco['uri']

        if best_score >= threshold:
            return best_match, best_score, best_uri
        return None, 0.0, None

    def approach_c_match(self, skill_text: str, threshold: float = 0.70) -> Tuple[str, float, str]:
        """
        Approach C: E5 embeddings + ESCO descriptions + domain filter
        Only considers tech-related skill_groups
        Returns: (esco_label, score, uri)
        """
        if self.model is None:
            self.load_embedding_model()

        # Tech-related skill groups
        TECH_GROUPS = {
            'Software and applications development and analysis',
            'Database and network design and administration',
            'ICT service management',
            'ICT security',
            'Web platform development software',
            'Data base management system software',
            'Application server software',
            'Backend Frameworks',
            'Data Engineering',
            'Object or component oriented development software',
            'Development environment software',
            'Mobile Development',
            'Data base user interface and query software',
            'Web Development',
            'Cloud Platforms',
            'Monitoring',
            'Software Architecture',
            'AI/ML',
            'Project management software',
            'DevOps Tools',
            'Version Control',
            'Testing Frameworks'
        }

        # Generate embedding for input skill
        skill_embedding = self.model.encode([f"query: {skill_text}"], normalize_embeddings=True)

        best_match = None
        best_score = 0.0
        best_uri = None

        for esco in self.esco_skills:
            # Filter by tech groups OR General Skills with high threshold
            skill_group = esco.get('skill_group', '')

            if skill_group not in TECH_GROUPS and skill_group != 'General Skills':
                continue

            # Use label + description for richer context
            label = esco['label_es']
            desc = esco.get('desc_es', '')

            # Combine label and description
            if desc:
                text = f"{label}. {desc[:200]}"  # Limit description length
            else:
                text = label

            text_embedding = self.model.encode([f"passage: {text}"], normalize_embeddings=True)

            # Cosine similarity
            similarity = cosine_similarity(skill_embedding, text_embedding)[0][0]

            # Apply higher threshold for General Skills
            effective_threshold = threshold + 0.1 if skill_group == 'General Skills' else threshold

            if similarity > best_score and similarity >= effective_threshold:
                best_score = similarity
                best_match = label
                best_uri = esco['uri']

        if best_score >= threshold:
            return best_match, best_score, best_uri
        return None, 0.0, None

    def evaluate_approach(self, approach_name: str, test_cases: List[Dict]) -> Dict:
        """
        Evaluate a matching approach on test cases
        Returns metrics: precision, recall, F1, accuracy
        """
        print(f"\n{'='*60}")
        print(f"Testing: {approach_name}")
        print(f"{'='*60}")

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
            if approach_name == "Baseline (ratio + partial_ratio)":
                esco_label, score, uri = self.baseline_match(skill_text)
            elif approach_name == "Approach A (ratio only)":
                esco_label, score, uri = self.approach_a_match(skill_text)
            elif approach_name == "Approach B (embeddings)":
                esco_label, score, uri = self.approach_b_match(skill_text)
            elif approach_name == "Approach C (embeddings + desc + filter)":
                esco_label, score, uri = self.approach_c_match(skill_text)
            else:
                raise ValueError(f"Unknown approach: {approach_name}")

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
        print(f"  False Positives: {fp}")
        print(f"  True Negatives:  {tn}")
        print(f"  False Negatives: {fn}")
        print(f"\n📈 Metrics:")
        print(f"  Precision: {precision:.3f}")
        print(f"  Recall:    {recall:.3f}")
        print(f"  F1-Score:  {f1:.3f}")
        print(f"  Accuracy:  {accuracy:.3f}")

        return results

    def run_experiments(self, validation_dataset_path: str):
        """Run all experiments and compare results"""
        print("="*60)
        print("ESCO MATCHING EXPERIMENTS")
        print("="*60)

        # Load validation dataset
        with open(validation_dataset_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        test_cases = data['cases']
        print(f"\n✅ Loaded {len(test_cases)} test cases")
        print(f"   - Expected good matches: {data['good_matches']}")
        print(f"   - Expected bad matches: {data['bad_matches']}")

        # Connect and load ESCO
        self.connect_db()
        self.load_esco_skills()

        # Run experiments
        approaches = [
            "Baseline (ratio + partial_ratio)",
            "Approach A (ratio only)",
            "Approach B (embeddings)",
            "Approach C (embeddings + desc + filter)"
        ]

        all_results = {}

        for approach in approaches:
            results = self.evaluate_approach(approach, test_cases)
            all_results[approach] = results

        # Compare results
        print(f"\n{'='*60}")
        print("COMPARATIVE SUMMARY")
        print(f"{'='*60}\n")

        print(f"{'Approach':<40} {'Precision':<12} {'Recall':<12} {'F1':<12} {'Accuracy':<12}")
        print("-" * 88)

        for approach, results in all_results.items():
            metrics = results['metrics']
            print(f"{approach:<40} "
                  f"{metrics['precision']:<12.3f} "
                  f"{metrics['recall']:<12.3f} "
                  f"{metrics['f1_score']:<12.3f} "
                  f"{metrics['accuracy']:<12.3f}")

        # Save results
        output_path = PROJECT_ROOT / "outputs" / "clustering" / "matching_experiments_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Results saved to: {output_path}")

        # Close connection
        self.conn.close()

        return all_results


def main():
    tester = MatchingTester()

    validation_dataset = PROJECT_ROOT / "tests" / "matching_validation_dataset.json"

    if not validation_dataset.exists():
        print(f"❌ Error: Validation dataset not found at {validation_dataset}")
        return 1

    tester.run_experiments(str(validation_dataset))

    return 0


if __name__ == "__main__":
    sys.exit(main())
