#!/usr/bin/env python3
"""
Parameter Experimentation for ESCO 30k Clustering

Tests different combinations of UMAP + HDBSCAN parameters to find optimal config.

Experiments:
- min_cluster_size: [3, 5, 7, 10, 15]
- n_neighbors: [10, 15, 20, 30]
- Total: 20 configurations

Runtime: ~15-20 minutes
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import psycopg2
import numpy as np
import pandas as pd
from typing import List, Tuple, Dict
import time
from collections import Counter

from config.settings import get_settings
from analyzer.dimension_reducer import DimensionReducer
from analyzer.clustering import SkillClusterer


def get_esco_skills_with_embeddings() -> Tuple[List[str], List[int], np.ndarray]:
    """
    Extract ESCO skills that have embeddings.

    Returns:
        skill_texts: List of skill texts
        skill_frequencies: List of global frequencies
        embeddings: numpy array of embeddings (Nx768)
    """
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print("📥 Fetching ESCO skills with embeddings...")

    # Get skills with frequencies
    cursor.execute("""
        SELECT
            e.skill_text,
            COUNT(DISTINCT e.job_id) as frequency
        FROM extracted_skills e
        WHERE e.skill_type = 'hard'
          AND e.esco_uri IS NOT NULL
        GROUP BY e.skill_text
        ORDER BY frequency DESC
    """)

    skills_data = cursor.fetchall()

    # Get embeddings for these skills
    embeddings = []
    found_skills = []
    found_frequencies = []

    for skill_text, freq in skills_data:
        cursor.execute("""
            SELECT embedding
            FROM skill_embeddings
            WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
        """, (skill_text,))

        result = cursor.fetchone()
        if result and result[0]:
            embeddings.append(result[0])
            found_skills.append(skill_text)
            found_frequencies.append(freq)

    cursor.close()
    conn.close()

    embeddings_array = np.array(embeddings, dtype=np.float32)

    print(f"✅ Loaded {len(found_skills):,} ESCO skills with embeddings")
    print(f"   Frequency range: {min(found_frequencies)} - {max(found_frequencies)}")
    print(f"   Embeddings shape: {embeddings_array.shape}")
    print()

    return found_skills, found_frequencies, embeddings_array


def run_experiment(
    embeddings: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int],
    n_neighbors: int,
    min_cluster_size: int,
    exp_name: str
) -> Dict:
    """Run single clustering experiment."""

    # UMAP
    reducer = DimensionReducer(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=0.1,
        metric='cosine'
    )

    coordinates = reducer.fit_transform(embeddings)

    # HDBSCAN
    clusterer = SkillClusterer(
        min_cluster_size=min_cluster_size,
        min_samples=5,
        metric='euclidean'
    )

    labels = clusterer.fit_predict(coordinates)

    # Analysis
    cluster_analysis = clusterer.analyze_clusters(labels, skill_texts, skill_frequencies)
    metrics = clusterer.calculate_metrics(coordinates, labels)

    # Count clusters
    n_clusters = len([l for l in set(labels) if l >= 0])
    n_noise = sum(1 for l in labels if l == -1)
    noise_pct = (n_noise / len(labels)) * 100

    return {
        'exp_name': exp_name,
        'n_neighbors': n_neighbors,
        'min_cluster_size': min_cluster_size,
        'n_clusters': n_clusters,
        'n_noise': n_noise,
        'noise_pct': noise_pct,
        'silhouette': metrics.get('silhouette_score', 0),
        'davies_bouldin': metrics.get('davies_bouldin_score', 0),
        'labels': labels,
        'coordinates': coordinates,
        'cluster_analysis': cluster_analysis
    }


def main():
    """Main execution."""

    print("="*80)
    print("ESCO 30K - PARAMETER EXPERIMENTATION")
    print("="*80)
    print()

    # Load data
    skill_texts, skill_frequencies, embeddings = get_esco_skills_with_embeddings()

    # Define parameter grid
    n_neighbors_vals = [10, 15, 20, 30]
    min_cluster_size_vals = [3, 5, 7, 10, 15]

    experiments = [
        (nn, mcs, f"nn{nn}_mcs{mcs}")
        for nn in n_neighbors_vals
        for mcs in min_cluster_size_vals
    ]

    print(f"🧪 Running {len(experiments)} experiments...")
    print(f"   n_neighbors: {n_neighbors_vals}")
    print(f"   min_cluster_size: {min_cluster_size_vals}")
    print()

    # Run experiments
    results = []
    start_time = time.time()

    for i, (nn, mcs, name) in enumerate(experiments, 1):
        exp_start = time.time()

        print(f"[{i}/{len(experiments)}] {name}...", end=" ", flush=True)

        result = run_experiment(
            embeddings, skill_texts, skill_frequencies,
            nn, mcs, name
        )

        exp_time = time.time() - exp_start
        print(f"✓ ({exp_time:.1f}s) - {result['n_clusters']} clusters, "
              f"sil={result['silhouette']:.3f}")

        results.append(result)

    total_time = time.time() - start_time

    print()
    print(f"✅ All experiments completed in {total_time/60:.1f} minutes")
    print()

    # Create comparison table
    df = pd.DataFrame([{
        'Config': r['exp_name'],
        'n_neighbors': r['n_neighbors'],
        'min_cluster_size': r['min_cluster_size'],
        'Clusters': r['n_clusters'],
        'Noise%': f"{r['noise_pct']:.1f}%",
        'Silhouette': f"{r['silhouette']:.3f}",
        'Davies-Bouldin': f"{r['davies_bouldin']:.3f}"
    } for r in results])

    print("="*80)
    print("RESULTS COMPARISON")
    print("="*80)
    print()
    print(df.to_string(index=False))
    print()

    # Score configurations
    print("="*80)
    print("RANKING (Multi-criteria scoring)")
    print("="*80)
    print()

    # Scoring system
    scores = []
    for r in results:
        score = 0

        # Silhouette (30%): higher is better
        sil_norm = (r['silhouette'] - 0.3) / (0.7 - 0.3)  # normalize 0.3-0.7 range
        score += max(0, min(1, sil_norm)) * 0.30

        # Davies-Bouldin (20%): lower is better
        db_norm = (2.0 - r['davies_bouldin']) / (2.0 - 0.0)  # normalize 0-2 range
        score += max(0, min(1, db_norm)) * 0.20

        # Number of clusters (30%): 15-40 is ideal
        if 15 <= r['n_clusters'] <= 40:
            clusters_score = 1.0
        elif 10 <= r['n_clusters'] < 15 or 40 < r['n_clusters'] <= 60:
            clusters_score = 0.7
        elif 5 <= r['n_clusters'] < 10 or 60 < r['n_clusters'] <= 80:
            clusters_score = 0.4
        else:
            clusters_score = 0.1
        score += clusters_score * 0.30

        # Noise (20%): <35% is ideal
        if r['noise_pct'] < 25:
            noise_score = 1.0
        elif r['noise_pct'] < 35:
            noise_score = 0.8
        elif r['noise_pct'] < 45:
            noise_score = 0.5
        else:
            noise_score = 0.2
        score += noise_score * 0.20

        scores.append({
            'Config': r['exp_name'],
            'Score': score,
            'Silhouette': r['silhouette'],
            'DB': r['davies_bouldin'],
            'Clusters': r['n_clusters'],
            'Noise%': r['noise_pct']
        })

    # Sort by score
    scores_df = pd.DataFrame(scores).sort_values('Score', ascending=False)
    scores_df['Score'] = scores_df['Score'].apply(lambda x: f"{x:.3f}")
    scores_df['Silhouette'] = scores_df['Silhouette'].apply(lambda x: f"{x:.3f}")
    scores_df['DB'] = scores_df['DB'].apply(lambda x: f"{x:.3f}")
    scores_df['Noise%'] = scores_df['Noise%'].apply(lambda x: f"{x:.1f}%")

    print(scores_df.to_string(index=False))
    print()

    # Top 3 recommendations
    top3 = scores_df.head(3)
    print("="*80)
    print("TOP 3 RECOMMENDED CONFIGURATIONS")
    print("="*80)
    print()

    for i, (_, row) in enumerate(top3.iterrows(), 1):
        config = row['Config']
        print(f"{i}. {config}")
        print(f"   Score: {row['Score']}")
        print(f"   Clusters: {row['Clusters']}, Noise: {row['Noise%']}")
        print(f"   Silhouette: {row['Silhouette']}, Davies-Bouldin: {row['DB']}")
        print()

    # Save results
    output_dir = Path("outputs/clustering/esco_30k_experiments")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save comparison table
    df.to_csv(output_dir / "comparison_table.csv", index=False)
    scores_df.to_csv(output_dir / "ranked_configs.csv", index=False)

    # Save detailed results
    import pickle
    with open(output_dir / "experiment_results.pkl", 'wb') as f:
        pickle.dump(results, f)

    print(f"💾 Results saved to: {output_dir}/")
    print()
    print("🎯 Next step: Review top 3, then run final clustering with best config")
    print()


if __name__ == '__main__':
    main()
