#!/usr/bin/env python3
"""
ESCO 30k - Final Clustering Analysis

Performs complete temporal clustering analysis on ESCO-matched skills from 30k jobs:
1. Cluster all ESCO-matched hard skills (1,700 skills)
2. Extract skill frequencies by quarter (17 trimestres: 2020-Q3 to 2024-Q4)
3. Generate temporal visualizations:
   - Heatmap: clusters × quarters
   - Line charts: evolution per cluster
   - UMAP scatter with size by frequency

Parameters (from experimentation - Fase 7):
- n_neighbors: 15
- min_cluster_size: 15
- Expected: 36 clusters, Silhouette ~0.475, DB ~0.652

Usage:
    python scripts/clustering_esco_30k_final.py
"""

import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
from collections import defaultdict

import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer


def extract_esco_skills() -> Tuple[List[str], List[int]]:
    """
    Extract all unique ESCO-matched hard skills from extracted_skills (30k jobs).

    Returns:
        (skill_texts, global_frequencies)
    """
    print("="*80)
    print("EXTRACTING ESCO-MATCHED SKILLS FROM 30K JOBS")
    print("="*80)

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Get all unique ESCO hard skills with their global frequency
    # Filter: Only NER + REGEX methods (exclude pipeline-a1-tfidf-np)
    query = """
        SELECT
            skill_text,
            COUNT(*) as frequency,
            COUNT(DISTINCT job_id) as job_count
        FROM extracted_skills
        WHERE skill_type = 'hard'
          AND esco_uri IS NOT NULL
          AND extraction_method IN ('ner', 'regex')
        GROUP BY skill_text
        ORDER BY frequency DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    skill_texts = [row[0] for row in results]
    frequencies = [row[1] for row in results]

    print(f"   ✅ Extracted {len(skill_texts)} unique ESCO hard skills")
    print(f"   Frequency range: {min(frequencies)} - {max(frequencies)}")
    print(f"   Total mentions: {sum(frequencies):,}")

    return skill_texts, frequencies


def fetch_embeddings_batch(skill_texts: List[str]) -> Tuple[np.ndarray, List[str], List[int]]:
    """
    Fetch embeddings for all skills.

    Returns:
        (embeddings, found_skills, found_indices)
    """
    print("\n" + "="*80)
    print("FETCHING EMBEDDINGS")
    print("="*80)
    print(f"Requesting embeddings for {len(skill_texts)} skills...")

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    embeddings = []
    found_skills = []
    found_indices = []

    for i, skill_text in enumerate(skill_texts):
        cursor.execute("""
            SELECT embedding
            FROM skill_embeddings
            WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            LIMIT 1
        """, (skill_text,))

        result = cursor.fetchone()
        if result:
            embeddings.append(result[0])
            found_skills.append(skill_text)
            found_indices.append(i)

    cursor.close()
    conn.close()

    embeddings_array = np.array(embeddings, dtype=np.float32)

    print(f"   ✅ Found embeddings: {len(found_skills)}/{len(skill_texts)}")
    print(f"   Coverage: {len(found_skills)/len(skill_texts)*100:.1f}%")

    return embeddings_array, found_skills, found_indices


def run_clustering(
    embeddings: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int]
) -> Tuple[np.ndarray, np.ndarray, List[Dict[str, Any]], Dict[str, float]]:
    """
    Run UMAP + HDBSCAN clustering with selected parameters (nn15_mcs15).

    Parameters from experimentation (Fase 7.10):
    - n_neighbors: 15
    - min_cluster_size: 15
    - Expected: 36 clusters, Silhouette ~0.475, DB ~0.652

    Returns:
        (coordinates, labels, cluster_analysis, metrics)
    """
    print("\n" + "="*80)
    print("RUNNING UMAP + HDBSCAN CLUSTERING (nn15_mcs15)")
    print("="*80)

    # UMAP reduction
    print("\n🚀 UMAP dimensionality reduction...")
    print("   Parameters: n_neighbors=15, min_dist=0.1, metric=cosine")
    reducer = DimensionReducer(
        n_components=2,
        n_neighbors=15,
        min_dist=0.1,
        metric='cosine',
        random_state=42,
        verbose=False
    )
    coordinates = reducer.fit_transform(embeddings)
    print(f"   ✅ UMAP complete: {coordinates.shape}")

    # HDBSCAN clustering
    print("\n🚀 HDBSCAN clustering...")
    print("   Parameters: min_cluster_size=15, min_samples=5, metric=euclidean")
    clusterer = SkillClusterer(
        min_cluster_size=15,
        min_samples=5,
        metric='euclidean',
        cluster_selection_method='eom'
    )
    labels = clusterer.fit_predict(coordinates)

    print("\n📊 Analyzing clusters...")
    cluster_analysis = clusterer.analyze_clusters(labels, skill_texts, skill_frequencies)

    print("\n📏 Calculating metrics...")
    metrics = clusterer.calculate_metrics(coordinates, labels)

    # Print summary
    print("\n" + "="*80)
    print("CLUSTERING RESULTS")
    print("="*80)
    print(f"   Clusters detected: {metrics['n_clusters']}")
    print(f"   Noise points: {metrics['n_noise']} ({metrics['noise_percentage']:.1f}%)")
    print(f"   Silhouette score: {metrics['silhouette_score']:.3f}")
    print(f"   Davies-Bouldin: {metrics['davies_bouldin_score']:.3f}")

    # Verify expected results
    print("\n   Expected from experiments:")
    print("   Clusters: ~36, Noise: ~32.8%, Silhouette: ~0.475, DB: ~0.652")

    return coordinates, labels, cluster_analysis, metrics


def extract_temporal_frequencies(skill_texts: List[str]) -> pd.DataFrame:
    """
    Extract skill frequencies by quarter from extracted_skills (30k jobs).

    Returns:
        DataFrame with columns: [quarter, skill_text, frequency]
    """
    print("\n" + "="*80)
    print("EXTRACTING TEMPORAL FREQUENCIES")
    print("="*80)

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)

    # Query to get frequencies by quarter
    # Filter: Only NER + REGEX methods (exclude pipeline-a1-tfidf-np)
    query = """
        SELECT
            DATE_TRUNC('quarter', j.posted_date) as quarter,
            es.skill_text,
            COUNT(*) as frequency
        FROM extracted_skills es
        JOIN raw_jobs j ON es.job_id = j.job_id
        WHERE es.skill_type = 'hard'
          AND es.esco_uri IS NOT NULL
          AND es.extraction_method IN ('ner', 'regex')
          AND j.posted_date IS NOT NULL
        GROUP BY DATE_TRUNC('quarter', j.posted_date), es.skill_text
        ORDER BY quarter, frequency DESC
    """

    df = pd.read_sql_query(query, conn)
    conn.close()

    # Convert quarter to period string
    df['quarter_str'] = df['quarter'].dt.to_period('Q').astype(str)

    print(f"   ✅ Extracted temporal data")
    print(f"   Quarters: {df['quarter_str'].nunique()}")
    print(f"   Date range: {df['quarter_str'].min()} - {df['quarter_str'].max()}")
    print(f"   Total records: {len(df):,}")

    return df


def create_cluster_temporal_matrix(
    temporal_df: pd.DataFrame,
    skill_texts: List[str],
    labels: np.ndarray
) -> Tuple[pd.DataFrame, List[str]]:
    """
    Create matrix of cluster frequencies by quarter.

    Returns:
        (cluster_matrix, cluster_labels)
        cluster_matrix: rows=quarters, columns=clusters, values=frequency
    """
    print("\n" + "="*80)
    print("CREATING TEMPORAL CLUSTER MATRIX")
    print("="*80)

    # Map skills to clusters
    skill_to_cluster = {skill: int(label) for skill, label in zip(skill_texts, labels)}

    # Add cluster column to temporal data
    temporal_df['cluster_id'] = temporal_df['skill_text'].map(skill_to_cluster)

    # Filter out skills without cluster assignment (missing embeddings)
    temporal_df = temporal_df[temporal_df['cluster_id'].notna()]

    # Aggregate by quarter and cluster
    cluster_temporal = temporal_df.groupby(['quarter_str', 'cluster_id'])['frequency'].sum().reset_index()

    # Pivot to matrix format
    matrix = cluster_temporal.pivot(index='quarter_str', columns='cluster_id', values='frequency')
    matrix = matrix.fillna(0)

    # Sort quarters chronologically
    matrix = matrix.sort_index()

    # Sort clusters by total frequency (most important first)
    cluster_totals = matrix.sum(axis=0).sort_values(ascending=False)
    matrix = matrix[cluster_totals.index]

    # Create cluster labels (exclude noise cluster -1)
    cluster_labels = []
    for cluster_id in matrix.columns:
        if cluster_id == -1:
            cluster_labels.append("Noise")
        else:
            cluster_labels.append(f"C{int(cluster_id)}")

    print(f"   ✅ Matrix shape: {matrix.shape}")
    print(f"   Quarters: {len(matrix)}")
    print(f"   Clusters: {len(matrix.columns)}")

    return matrix, cluster_labels


def visualize_temporal_heatmap(
    matrix: pd.DataFrame,
    cluster_labels: List[str],
    cluster_analysis: List[Dict[str, Any]],
    output_path: str
):
    """Generate heatmap of cluster evolution over time."""

    print("\n" + "="*80)
    print("GENERATING TEMPORAL HEATMAP")
    print("="*80)

    # Create enriched labels with top skills
    enriched_labels = []
    cluster_info_map = {c['cluster_id']: c for c in cluster_analysis}

    for i, cluster_id in enumerate(matrix.columns):
        if cluster_id == -1:
            enriched_labels.append("Noise")
        else:
            info = cluster_info_map.get(int(cluster_id), {})
            top_skills = info.get('top_skills', [])
            label = f"C{int(cluster_id)}: {', '.join(top_skills[:2])}"
            enriched_labels.append(label[:50])  # Truncate

    # Create figure
    fig, ax = plt.subplots(figsize=(20, 12))

    # Log-scale for better visualization
    matrix_log = np.log1p(matrix)

    # Plot heatmap
    sns.heatmap(
        matrix_log.T,
        cmap='YlOrRd',
        linewidths=0.5,
        linecolor='gray',
        cbar_kws={'label': 'log(frequency + 1)'},
        yticklabels=enriched_labels,
        ax=ax
    )

    ax.set_title('ESCO 30k: Cluster Evolution Over Time (17 Quarters)', fontsize=16, pad=20)
    ax.set_xlabel('Quarter', fontsize=12)
    ax.set_ylabel('Cluster', fontsize=12)
    plt.xticks(rotation=45, ha='right')
    plt.yticks(fontsize=8)
    plt.tight_layout()

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved: {output_path}")
    plt.close()


def visualize_top_clusters_evolution(
    matrix: pd.DataFrame,
    cluster_labels: List[str],
    cluster_analysis: List[Dict[str, Any]],
    output_path: str,
    top_n: int = 10
):
    """Generate line charts for top N clusters."""

    print("\n" + "="*80)
    print(f"GENERATING TOP {top_n} CLUSTERS EVOLUTION")
    print("="*80)

    # Select top N clusters by total frequency
    cluster_totals = matrix.sum(axis=0).sort_values(ascending=False)
    top_clusters = cluster_totals.head(top_n).index

    # Get cluster info
    cluster_info_map = {c['cluster_id']: c for c in cluster_analysis}

    # Create figure
    fig, ax = plt.subplots(figsize=(16, 10))

    # Plot each cluster
    for cluster_id in top_clusters:
        if cluster_id == -1:
            label = "Noise"
        else:
            info = cluster_info_map.get(int(cluster_id), {})
            top_skills = info.get('top_skills', [])
            label = f"C{int(cluster_id)}: {', '.join(top_skills[:2])}"

        ax.plot(
            range(len(matrix)),
            matrix[cluster_id],
            marker='o',
            linewidth=2,
            label=label[:50]
        )

    ax.set_xticks(range(len(matrix)))
    ax.set_xticklabels(matrix.index, rotation=45, ha='right')
    ax.set_xlabel('Quarter', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(f'ESCO 30k: Top {top_n} Clusters Evolution (17 Quarters)', fontsize=16, pad=20)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved: {output_path}")
    plt.close()


def visualize_umap_scatter(
    coordinates: np.ndarray,
    labels: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int],
    output_path: str
):
    """Generate UMAP scatter plot with frequency-based sizing."""

    print("\n" + "="*80)
    print("GENERATING UMAP SCATTER PLOT")
    print("="*80)

    fig, ax = plt.subplots(figsize=(16, 12))

    # Normalize sizes
    sizes = np.array(skill_frequencies)
    sizes_norm = (sizes - sizes.min()) / (sizes.max() - sizes.min())
    sizes_scaled = 10 + sizes_norm * 200  # 10-210 point size

    # Get unique clusters
    unique_labels = set(labels)
    n_clusters = len(unique_labels - {-1})

    # Color palette
    palette = sns.color_palette('tab20', n_colors=n_clusters)
    colors = []
    for label in labels:
        if label == -1:
            colors.append('lightgray')
        else:
            colors.append(palette[label % len(palette)])

    # Plot points
    scatter = ax.scatter(
        coordinates[:, 0],
        coordinates[:, 1],
        c=colors,
        s=sizes_scaled,
        alpha=0.6,
        edgecolors='black',
        linewidth=0.5
    )

    ax.set_title(
        f'ESCO 30k: UMAP Projection (nn15_mcs15)\n'
        f'{n_clusters} clusters, {len(skill_texts)} skills, Size = Frequency',
        fontsize=16,
        pad=20
    )
    ax.set_xlabel('UMAP 1', fontsize=12)
    ax.set_ylabel('UMAP 2', fontsize=12)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"   ✅ Saved: {output_path}")
    plt.close()


def save_results(
    skill_texts: List[str],
    skill_frequencies: List[int],
    coordinates: np.ndarray,
    labels: np.ndarray,
    cluster_analysis: List[Dict[str, Any]],
    metrics: Dict[str, float],
    temporal_matrix: pd.DataFrame,
    output_dir: Path
):
    """Save all results to JSON files."""

    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    # Main results
    results = {
        'parameters': {
            'n_neighbors': 15,
            'min_cluster_size': 15,
            'min_dist': 0.1,
            'metric_umap': 'cosine',
            'metric_hdbscan': 'euclidean'
        },
        'metrics': metrics,
        'n_skills': len(skill_texts),
        'n_clusters': metrics['n_clusters'],
        'skills': [
            {
                'skill_text': skill_texts[i],
                'frequency': int(skill_frequencies[i]),
                'cluster_id': int(labels[i]),
                'umap_x': float(coordinates[i, 0]),
                'umap_y': float(coordinates[i, 1])
            }
            for i in range(len(skill_texts))
        ],
        'cluster_analysis': cluster_analysis
    }

    results_path = output_dir / 'esco_30k_results.json'
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   ✅ Saved: {results_path}")

    # Temporal matrix
    temporal_path = output_dir / 'temporal_matrix.csv'
    temporal_matrix.to_csv(temporal_path)
    print(f"   ✅ Saved: {temporal_path}")

    # Metrics summary
    metrics_path = output_dir / 'metrics_summary.json'
    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump({
            'execution_date': datetime.now().isoformat(),
            'parameters': results['parameters'],
            'metrics': metrics,
            'n_skills_total': len(skill_texts),
            'n_skills_clustered': int((labels != -1).sum()),
            'n_clusters': metrics['n_clusters'],
            'temporal_quarters': len(temporal_matrix)
        }, f, indent=2)
    print(f"   ✅ Saved: {metrics_path}")


def main():
    """Main execution."""

    print("\n" + "="*80)
    print("ESCO 30K - FINAL CLUSTERING ANALYSIS")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Parameters: n_neighbors=15, min_cluster_size=15")
    print("="*80)

    # Create output directory
    output_dir = Path("outputs/clustering/esco_30k")
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOutput directory: {output_dir}/")

    # Step 1: Extract ESCO skills
    skill_texts, skill_frequencies = extract_esco_skills()

    # Step 2: Fetch embeddings
    embeddings, found_skills, found_indices = fetch_embeddings_batch(skill_texts)

    # Filter skills to those with embeddings
    skill_texts_filtered = [skill_texts[i] for i in found_indices]
    skill_frequencies_filtered = [skill_frequencies[i] for i in found_indices]

    print(f"\n   Using {len(skill_texts_filtered)} skills for clustering")

    # Step 3: Run clustering
    coordinates, labels, cluster_analysis, metrics = run_clustering(
        embeddings,
        skill_texts_filtered,
        skill_frequencies_filtered
    )

    # Step 4: Extract temporal frequencies
    temporal_df = extract_temporal_frequencies(skill_texts)

    # Step 5: Create temporal matrix
    temporal_matrix, cluster_labels = create_cluster_temporal_matrix(
        temporal_df,
        skill_texts_filtered,
        labels
    )

    # Step 6: Generate visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)

    visualize_temporal_heatmap(
        temporal_matrix,
        cluster_labels,
        cluster_analysis,
        str(output_dir / 'temporal_heatmap.png')
    )

    visualize_top_clusters_evolution(
        temporal_matrix,
        cluster_labels,
        cluster_analysis,
        str(output_dir / 'top_clusters_evolution.png'),
        top_n=10
    )

    visualize_umap_scatter(
        coordinates,
        labels,
        skill_texts_filtered,
        skill_frequencies_filtered,
        str(output_dir / 'umap_scatter.png')
    )

    # Step 7: Save results
    save_results(
        skill_texts_filtered,
        skill_frequencies_filtered,
        coordinates,
        labels,
        cluster_analysis,
        metrics,
        temporal_matrix,
        output_dir
    )

    # Final summary
    print("\n" + "="*80)
    print("✅ CLUSTERING COMPLETE")
    print("="*80)
    print(f"   Skills clustered: {len(skill_texts_filtered)}")
    print(f"   Clusters detected: {metrics['n_clusters']}")
    print(f"   Silhouette score: {metrics['silhouette_score']:.3f}")
    print(f"   Davies-Bouldin: {metrics['davies_bouldin_score']:.3f}")
    print(f"   Temporal quarters: {len(temporal_matrix)}")
    print(f"\n   All results saved to: {output_dir}/")
    print("\n" + "="*80)


if __name__ == '__main__':
    main()
