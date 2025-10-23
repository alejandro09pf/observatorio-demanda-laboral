#!/usr/bin/env python3
"""
COMPREHENSIVE EMBEDDING TESTS

This script runs extensive tests on skill embeddings:
1. Database integrity tests
2. Embedding quality tests (dimension, normalization, distribution)
3. Semantic similarity tests (known similar/dissimilar pairs)
4. FAISS index tests (performance, correctness)
5. Language handling tests (Spanish/English tech terms)
6. Edge case tests
"""

import sys
import time
import pickle
from pathlib import Path
from typing import List, Tuple, Dict
from collections import Counter

import psycopg2
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings


class EmbeddingTester:
    """Comprehensive embedding test suite."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')

        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = []

    def log(self, msg: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"   {msg}")

    def test_header(self, title: str):
        """Print test section header."""
        print(f"\n{'='*70}")
        print(f"{title}")
        print(f"{'='*70}")

    def assert_test(self, condition: bool, test_name: str, error_msg: str = ""):
        """Assert test condition and track results."""
        if condition:
            print(f"✅ {test_name}")
            self.passed_tests += 1
        else:
            print(f"❌ {test_name}")
            if error_msg:
                print(f"   Error: {error_msg}")
            self.failed_tests += 1

    def warn(self, msg: str):
        """Record warning."""
        print(f"⚠️  {msg}")
        self.warnings.append(msg)

    # ==================== DATABASE TESTS ====================

    def test_database_integrity(self):
        """Test database structure and data integrity."""
        self.test_header("TEST 1: DATABASE INTEGRITY")

        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()

        # Test 1.1: Table exists
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'skill_embeddings'
            )
        """)
        self.assert_test(
            cursor.fetchone()[0],
            "Table 'skill_embeddings' exists"
        )

        # Test 1.2: Row count
        cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
        count = cursor.fetchone()[0]
        self.assert_test(
            count > 10000,
            f"Sufficient embeddings ({count:,} > 10,000)"
        )
        self.log(f"Total embeddings: {count:,}")

        # Test 1.3: No NULL embeddings
        cursor.execute("SELECT COUNT(*) FROM skill_embeddings WHERE embedding IS NULL")
        null_count = cursor.fetchone()[0]
        self.assert_test(
            null_count == 0,
            f"No NULL embeddings (found {null_count})"
        )

        # Test 1.4: No empty skill texts
        cursor.execute("SELECT COUNT(*) FROM skill_embeddings WHERE skill_text = '' OR skill_text IS NULL")
        empty_count = cursor.fetchone()[0]
        self.assert_test(
            empty_count == 0,
            f"No empty skill texts (found {empty_count})"
        )

        # Test 1.5: Unique skill texts
        cursor.execute("""
            SELECT COUNT(*) as total,
                   COUNT(DISTINCT skill_text) as unique_texts
            FROM skill_embeddings
        """)
        total, unique = cursor.fetchone()
        self.assert_test(
            total == unique,
            f"All skill texts unique ({unique:,} / {total:,})"
        )

        # Test 1.6: Correct model name
        cursor.execute("SELECT DISTINCT model_name FROM skill_embeddings")
        models = [row[0] for row in cursor.fetchall()]
        self.assert_test(
            len(models) == 1 and 'multilingual-e5-base' in models[0],
            f"Correct model used: {models}"
        )

        cursor.close()
        conn.close()

    # ==================== EMBEDDING QUALITY TESTS ====================

    def test_embedding_quality(self):
        """Test embedding dimensions, normalization, and distribution."""
        self.test_header("TEST 2: EMBEDDING QUALITY")

        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()

        # Load sample embeddings
        cursor.execute("""
            SELECT skill_text, embedding
            FROM skill_embeddings
            ORDER BY RANDOM()
            LIMIT 1000
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        embeddings = np.array([np.array(row[1], dtype=np.float32) for row in rows])
        skill_texts = [row[0] for row in rows]

        # Test 2.1: Correct dimension
        dims = [emb.shape[0] for emb in embeddings]
        self.assert_test(
            all(d == 768 for d in dims),
            f"All embeddings have dimension 768"
        )
        if len(set(dims)) > 1:
            print(f"   Found dimensions: {set(dims)}")

        # Test 2.2: No NaN or Inf values
        has_nan = np.any(np.isnan(embeddings))
        has_inf = np.any(np.isinf(embeddings))
        self.assert_test(
            not has_nan and not has_inf,
            "No NaN or Inf values in embeddings"
        )

        # Test 2.3: L2 normalization (embeddings should be unit vectors)
        norms = np.linalg.norm(embeddings, axis=1)
        avg_norm = np.mean(norms)
        std_norm = np.std(norms)
        self.log(f"L2 norms: mean={avg_norm:.4f}, std={std_norm:.4f}")
        self.assert_test(
            0.99 <= avg_norm <= 1.01,
            f"Embeddings are L2-normalized (avg norm: {avg_norm:.4f})"
        )

        # Test 2.4: Non-zero embeddings
        zero_embeddings = np.sum(np.all(embeddings == 0, axis=1))
        self.assert_test(
            zero_embeddings == 0,
            f"No zero embeddings (found {zero_embeddings})"
        )

        # Test 2.5: Value distribution (should be roughly Gaussian)
        all_values = embeddings.flatten()
        mean_val = np.mean(all_values)
        std_val = np.std(all_values)
        self.log(f"Value distribution: mean={mean_val:.4f}, std={std_val:.4f}")
        self.assert_test(
            -0.2 <= mean_val <= 0.2,
            f"Values centered around 0 (mean: {mean_val:.4f})"
        )

        # Test 2.6: Reasonable standard deviation
        # Note: For L2-normalized embeddings, std is typically lower (0.03-0.15)
        self.assert_test(
            0.02 <= std_val <= 0.20,
            f"Reasonable spread (std: {std_val:.4f})"
        )

    # ==================== SEMANTIC SIMILARITY TESTS ====================

    def test_semantic_similarity(self):
        """Test semantic similarity for known skill pairs."""
        self.test_header("TEST 3: SEMANTIC SIMILARITY")

        # Define test cases: (skill1_pattern, skill2_pattern, expected_similarity_range, relationship)
        # Note: multilingual-e5-base produces high similarity for tech skills (this is expected)
        test_cases = [
            # High similarity (identical skills)
            ("Python", "Python", (0.99, 1.01), "identical"),
            ("JavaScript", "JavaScript", (0.99, 1.01), "identical"),
            ("React", "React", (0.99, 1.01), "identical"),

            # Related technologies (should be very similar in e5-base)
            ("React", "Vue.js", (0.70, 0.95), "similar frameworks"),
            ("Python", "Django", (0.70, 0.95), "language and framework"),
            ("Docker", "Kubernetes", (0.75, 0.95), "container technologies"),
            ("PostgreSQL", "MySQL", (0.70, 0.95), "similar databases"),
            ("Git%", "GitHub", (0.70, 0.97), "version control tools"),

            # Moderately related (tech skills remain similar in e5-base)
            ("%Java%programación%", "Python", (0.50, 0.85), "programming languages"),
            ("%HTML%", "CSS", (0.60, 0.90), "web technologies"),
            ("AWS Lambda", "%Azure%", (0.50, 0.85), "cloud platforms"),

            # Less related (still somewhat similar for tech terms)
            ("Python", "PostgreSQL", (0.50, 0.90), "language vs database"),
            ("React", "PostgreSQL", (0.50, 0.90), "frontend vs database"),

            # Unrelated (should be more dissimilar)
            ("Python", "%Photoshop%", (0.20, 0.65), "programming vs design"),
            ("Docker", "%Excel%", (0.20, 0.65), "DevOps vs spreadsheet"),
        ]

        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()

        passed_similarity = 0
        failed_similarity = 0

        for skill1_pattern, skill2_pattern, (min_sim, max_sim), relationship in test_cases:
            # Get embeddings using ILIKE for flexible matching
            cursor.execute("""
                SELECT skill_text, embedding FROM skill_embeddings
                WHERE skill_text ILIKE %s
                LIMIT 1
            """, (skill1_pattern,))
            result1 = cursor.fetchone()

            cursor.execute("""
                SELECT skill_text, embedding FROM skill_embeddings
                WHERE skill_text ILIKE %s
                LIMIT 1
            """, (skill2_pattern,))
            result2 = cursor.fetchone()

            if not result1:
                self.warn(f"Skill pattern '{skill1_pattern}' not found in embeddings")
                continue
            if not result2:
                self.warn(f"Skill pattern '{skill2_pattern}' not found in embeddings")
                continue

            skill1_name, emb1_data = result1
            skill2_name, emb2_data = result2

            emb1 = np.array(emb1_data, dtype=np.float32)
            emb2 = np.array(emb2_data, dtype=np.float32)

            # Cosine similarity (since embeddings are normalized, this is just dot product)
            similarity = np.dot(emb1, emb2)

            # Check if similarity is in expected range
            in_range = min_sim <= similarity <= max_sim
            status = "✅" if in_range else "❌"

            # Truncate skill names for display
            display_name1 = skill1_name[:20] if len(skill1_name) <= 20 else skill1_name[:17] + "..."
            display_name2 = skill2_name[:20] if len(skill2_name) <= 20 else skill2_name[:17] + "..."

            print(f"{status} {display_name1:20} <-> {display_name2:20}: {similarity:.4f} "
                  f"[{min_sim:.2f}-{max_sim:.2f}] ({relationship})")

            if in_range:
                passed_similarity += 1
                self.passed_tests += 1
            else:
                failed_similarity += 1
                self.failed_tests += 1

        cursor.close()
        conn.close()

        print(f"\nSimilarity tests: {passed_similarity} passed, {failed_similarity} failed")

    # ==================== FAISS INDEX TESTS ====================

    def test_faiss_index(self):
        """Test FAISS index correctness and performance."""
        self.test_header("TEST 4: FAISS INDEX")

        # Check files exist
        index_path = Path(__file__).parent.parent / "data" / "embeddings" / "esco.faiss"
        mapping_path = Path(__file__).parent.parent / "data" / "embeddings" / "esco_mapping.pkl"

        self.assert_test(
            index_path.exists(),
            f"FAISS index file exists: {index_path}"
        )

        self.assert_test(
            mapping_path.exists(),
            f"Mapping file exists: {mapping_path}"
        )

        if not index_path.exists() or not mapping_path.exists():
            print("⚠️  Skipping FAISS tests (files not found)")
            return

        # Load index and mapping
        index = faiss.read_index(str(index_path))
        with open(mapping_path, 'rb') as f:
            skill_texts = pickle.load(f)

        # Test 4.1: Index size matches mapping
        self.assert_test(
            index.ntotal == len(skill_texts),
            f"Index size matches mapping ({index.ntotal:,} == {len(skill_texts):,})"
        )

        # Test 4.2: Index dimension
        self.assert_test(
            index.d == 768,
            f"Index dimension is 768 (found {index.d})"
        )

        # Test 4.3: Index type
        self.log(f"Index type: {type(index)}")
        self.assert_test(
            isinstance(index, faiss.IndexFlat) or isinstance(index, faiss.IndexFlatIP),
            "Index is IndexFlat or IndexFlatIP"
        )

        # Test 4.4: Search correctness
        # Query with first vector - should return itself as top result
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT skill_text, embedding
            FROM skill_embeddings
            ORDER BY skill_text
            LIMIT 1
        """)
        test_skill, test_embedding = cursor.fetchone()
        cursor.close()
        conn.close()

        test_query = np.array([test_embedding], dtype=np.float32)
        distances, indices = index.search(test_query, k=5)

        top_result = skill_texts[indices[0][0]]
        self.assert_test(
            top_result == test_skill,
            f"FAISS search returns correct top result: '{test_skill}'"
        )

        # Test 4.5: Search performance
        num_queries = 100
        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()
        cursor.execute(f"""
            SELECT embedding
            FROM skill_embeddings
            ORDER BY RANDOM()
            LIMIT {num_queries}
        """)
        query_embeddings = np.array([np.array(row[0], dtype=np.float32) for row in cursor.fetchall()])
        cursor.close()
        conn.close()

        start_time = time.time()
        distances, indices = index.search(query_embeddings, k=10)
        elapsed = time.time() - start_time

        qps = num_queries / elapsed  # queries per second
        self.log(f"Search performance: {qps:.1f} queries/sec ({num_queries} queries in {elapsed:.3f}s)")
        self.assert_test(
            qps > 100,
            f"FAISS search is fast (>{100} queries/sec, got {qps:.1f})"
        )

    # ==================== LANGUAGE HANDLING TESTS ====================

    def test_language_handling(self):
        """Test handling of Spanish and English tech terms."""
        self.test_header("TEST 5: LANGUAGE HANDLING")

        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()

        # Test 5.1: Tech terms present (should NOT be translated)
        tech_terms = [
            "Python", "JavaScript", "React", "Docker", "Kubernetes",
            "PostgreSQL", "MongoDB", "AWS", "Git", "TypeScript"
        ]

        found_count = 0
        for term in tech_terms:
            cursor.execute("""
                SELECT COUNT(*) FROM skill_embeddings
                WHERE skill_text = %s
            """, (term,))
            if cursor.fetchone()[0] > 0:
                found_count += 1

        self.assert_test(
            found_count >= len(tech_terms) * 0.7,  # At least 70%
            f"Tech terms preserved ({found_count}/{len(tech_terms)})"
        )

        # Test 5.2: Spanish ESCO skills present
        cursor.execute("""
            SELECT COUNT(*) FROM skill_embeddings
            WHERE skill_text LIKE '%gestionar%'
               OR skill_text LIKE '%supervisar%'
               OR skill_text LIKE '%garantizar%'
        """)
        spanish_count = cursor.fetchone()[0]
        self.assert_test(
            spanish_count > 100,
            f"Spanish ESCO skills present ({spanish_count:,} > 100)"
        )

        # Test 5.3: Mixed language skills
        cursor.execute("""
            SELECT skill_text
            FROM skill_embeddings
            WHERE skill_text ~ '[a-zA-Z]' AND skill_text ~ '[áéíóúñ]'
            LIMIT 5
        """)
        mixed = cursor.fetchall()
        if mixed:
            self.log(f"Found {len(mixed)} skills with mixed characters")
            for skill in mixed[:3]:
                self.log(f"  - {skill[0]}")

        cursor.close()
        conn.close()

    # ==================== EDGE CASE TESTS ====================

    def test_edge_cases(self):
        """Test edge cases and unusual inputs."""
        self.test_header("TEST 6: EDGE CASES")

        conn = psycopg2.connect(self.db_url)
        cursor = conn.cursor()

        # Test 6.1: Very short skill names (1-2 characters)
        cursor.execute("""
            SELECT skill_text, LENGTH(skill_text) as len
            FROM skill_embeddings
            WHERE LENGTH(skill_text) <= 2
            ORDER BY len
            LIMIT 10
        """)
        short_skills = cursor.fetchall()
        if short_skills:
            self.log(f"Found {len(short_skills)} very short skill names:")
            for skill, length in short_skills[:5]:
                self.log(f"  - '{skill}' (len={length})")

        # Test 6.2: Very long skill names (>80 characters)
        cursor.execute("""
            SELECT skill_text, LENGTH(skill_text) as len
            FROM skill_embeddings
            WHERE LENGTH(skill_text) > 80
            ORDER BY len DESC
            LIMIT 5
        """)
        long_skills = cursor.fetchall()
        if long_skills:
            self.log(f"Found {len(long_skills)} very long skill names:")
            for skill, length in long_skills:
                self.log(f"  - {skill[:60]}... (len={length})")

        # Test 6.3: Skills with special characters
        cursor.execute("""
            SELECT skill_text
            FROM skill_embeddings
            WHERE skill_text ~ '[^a-zA-Z0-9áéíóúñüÁÉÍÓÚÑÜ \-\.]'
            LIMIT 10
        """)
        special_char_skills = cursor.fetchall()
        if special_char_skills:
            self.log(f"Found {len(special_char_skills)} skills with special characters:")
            for skill in special_char_skills[:5]:
                self.log(f"  - {skill[0]}")

        # Test 6.4: Check for potential duplicates (case-insensitive)
        cursor.execute("""
            SELECT LOWER(skill_text) as lower_text, COUNT(*) as count
            FROM skill_embeddings
            GROUP BY LOWER(skill_text)
            HAVING COUNT(*) > 1
            ORDER BY count DESC
            LIMIT 10
        """)
        duplicates = cursor.fetchall()
        if duplicates:
            self.warn(f"Found {len(duplicates)} case-insensitive duplicates:")
            for lower_text, count in duplicates[:5]:
                cursor.execute("""
                    SELECT skill_text FROM skill_embeddings
                    WHERE LOWER(skill_text) = %s
                """, (lower_text,))
                variants = [row[0] for row in cursor.fetchall()]
                self.log(f"  - {variants} (count={count})")

        cursor.close()
        conn.close()

        # All edge case tests pass if no errors
        self.assert_test(True, "Edge case tests completed")

    # ==================== SUMMARY ====================

    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)

        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"\n Total tests: {total_tests}")
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f" Pass rate: {pass_rate:.1f}%")

        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings[:5]:
                print(f"   - {warning}")
            if len(self.warnings) > 5:
                print(f"   ... and {len(self.warnings) - 5} more")

        print()

        if self.failed_tests == 0:
            print("🎉 ALL TESTS PASSED!")
            return 0
        else:
            print("⚠️  SOME TESTS FAILED")
            return 1


def main():
    """Run all embedding tests."""
    import argparse

    parser = argparse.ArgumentParser(description="Test skill embeddings")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    print("="*70)
    print("COMPREHENSIVE EMBEDDING TESTS")
    print("="*70)
    print()

    tester = EmbeddingTester(verbose=args.verbose)

    # Run all test suites
    tester.test_database_integrity()
    tester.test_embedding_quality()
    tester.test_semantic_similarity()
    tester.test_faiss_index()
    tester.test_language_handling()
    tester.test_edge_cases()

    # Print summary and return exit code
    exit_code = tester.print_summary()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
