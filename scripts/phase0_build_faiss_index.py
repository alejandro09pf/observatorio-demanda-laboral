#!/usr/bin/env python3
"""
PHASE 0 - Step 0.2: Build FAISS index for fast semantic skill matching.

This script:
1. Loads all skill embeddings from skill_embeddings table
2. Builds FAISS IndexFlatIP index (cosine similarity via inner product)
3. Saves index to data/embeddings/esco.faiss
4. Saves skill_text to index mapping to data/embeddings/esco_mapping.pkl

FAISS provides 25x faster semantic search than PostgreSQL pgvector.
"""

import sys
import pickle
from pathlib import Path
from typing import List, Tuple

import psycopg2
import numpy as np
import faiss

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings


def load_embeddings_from_db() -> Tuple[List[str], np.ndarray]:
    """
    Load all embeddings from skill_embeddings table.

    Returns:
        Tuple of (skill_texts, embeddings_array)
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    print("=" * 70)
    print("LOADING EMBEDDINGS FROM DATABASE")
    print("=" * 70)

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT skill_text, embedding
        FROM skill_embeddings
        ORDER BY skill_text
    """)

    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    print(f"   Loaded: {len(rows):,} embeddings")
    print()

    # Extract skill texts and embeddings
    skill_texts = []
    embeddings_list = []

    for skill_text, embedding in rows:
        skill_texts.append(skill_text)
        # Convert PostgreSQL array to numpy array
        embeddings_list.append(np.array(embedding, dtype=np.float32))

    # Stack into single array
    embeddings = np.vstack(embeddings_list)

    print(f"✅ Embeddings loaded:")
    print(f"   Shape: {embeddings.shape}")
    print(f"   Dtype: {embeddings.dtype}")
    print(f"   Skills: {len(skill_texts):,}")
    print()

    return skill_texts, embeddings


def build_faiss_index(embeddings: np.ndarray) -> faiss.Index:
    """
    Build FAISS IndexFlatIP index for cosine similarity search.

    IndexFlatIP uses inner product, which equals cosine similarity
    when embeddings are L2-normalized (which ours are).

    Args:
        embeddings: Numpy array of shape (N, 768)

    Returns:
        FAISS index
    """
    print("=" * 70)
    print("BUILDING FAISS INDEX")
    print("=" * 70)

    dimension = embeddings.shape[1]
    print(f"   Dimension: {dimension}")
    print(f"   Index type: IndexFlatIP (cosine similarity)")
    print(f"   Total vectors: {len(embeddings):,}")
    print()

    # Create index
    # IndexFlatIP = exact search using inner product
    # For L2-normalized vectors, inner product = cosine similarity
    index = faiss.IndexFlatIP(dimension)

    # Add embeddings to index
    print("🚀 Adding vectors to index...")
    index.add(embeddings)

    print(f"✅ Index built successfully!")
    print(f"   Total indexed: {index.ntotal:,}")
    print()

    return index


def save_index_and_mapping(
    index: faiss.Index,
    skill_texts: List[str],
    output_dir: Path
) -> None:
    """
    Save FAISS index and skill_text mapping to disk.

    Args:
        index: FAISS index
        skill_texts: List of skill text labels
        output_dir: Directory to save files
    """
    print("=" * 70)
    print("SAVING INDEX AND MAPPING")
    print("=" * 70)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save FAISS index
    index_path = output_dir / "esco.faiss"
    faiss.write_index(index, str(index_path))
    print(f"✅ FAISS index saved: {index_path}")
    print(f"   File size: {index_path.stat().st_size / 1024 / 1024:.2f} MB")

    # Save skill_text mapping
    # This maps index position → skill_text
    mapping_path = output_dir / "esco_mapping.pkl"
    with open(mapping_path, 'wb') as f:
        pickle.dump(skill_texts, f)
    print(f"✅ Mapping saved: {mapping_path}")
    print(f"   File size: {mapping_path.stat().st_size / 1024:.2f} KB")
    print()


def test_index(
    index: faiss.Index,
    skill_texts: List[str],
    embeddings: np.ndarray,
    k: int = 5
) -> None:
    """
    Test the FAISS index with a sample query.

    Args:
        index: FAISS index
        skill_texts: List of skill texts
        embeddings: Embeddings array
        k: Number of nearest neighbors to retrieve
    """
    print("=" * 70)
    print("TESTING INDEX")
    print("=" * 70)

    # Test with first embedding (should return itself as top result)
    test_idx = 0
    test_query = embeddings[test_idx:test_idx+1]  # Shape (1, 768)
    test_skill = skill_texts[test_idx]

    print(f"🔍 Query skill: '{test_skill}'")
    print(f"   Finding {k} nearest neighbors...")
    print()

    # Search
    distances, indices = index.search(test_query, k)

    print(f"📊 Results (cosine similarity scores):")
    for i, (dist, idx) in enumerate(zip(distances[0], indices[0])):
        result_skill = skill_texts[idx]
        print(f"   {i+1}. [{dist:.4f}] {result_skill}")
    print()

    # Verify top result is the query itself
    if indices[0][0] == test_idx:
        print("✅ Index test passed! Query returned itself as top result.")
    else:
        print("⚠️  Warning: Query did not return itself as top result.")
    print()


def main():
    """Main execution function."""

    print("=" * 70)
    print("PHASE 0 - STEP 0.2: BUILD FAISS INDEX")
    print("=" * 70)
    print()

    # Step 1: Load embeddings from database
    skill_texts, embeddings = load_embeddings_from_db()

    # Step 2: Build FAISS index
    index = build_faiss_index(embeddings)

    # Step 3: Save index and mapping
    output_dir = Path(__file__).parent.parent / "data" / "embeddings"
    save_index_and_mapping(index, skill_texts, output_dir)

    # Step 4: Test index
    test_index(index, skill_texts, embeddings, k=5)

    # Final summary
    print("=" * 70)
    print("✅ PHASE 0 - STEP 0.2 COMPLETE")
    print("=" * 70)
    print(f"   Index location: {output_dir / 'esco.faiss'}")
    print(f"   Mapping location: {output_dir / 'esco_mapping.pkl'}")
    print(f"   Total skills indexed: {index.ntotal:,}")
    print(f"   Index dimension: {embeddings.shape[1]}")
    print()
    print("🎯 Next step: Implement ESCO Matcher Layer 2 (semantic matching)")
    print("   Modify: src/extractor/esco_matcher.py")
    print()


if __name__ == '__main__':
    main()
