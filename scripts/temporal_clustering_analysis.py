#!/usr/bin/env python3
"""
Temporal Clustering Analysis

This script performs complete temporal analysis of skill demand:
1. Cluster ALL gold standard skills (1,914 hard skills)
2. Extract skill frequencies by quarter (2015-2024)
3. Generate temporal visualizations:
   - Heatmap: clusters × quarters
   - Line charts: evolution per cluster
   - UMAP scatter with size by frequency

Usage:
    python scripts/temporal_clustering_analysis.py
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


def extract_all_gold_standard_skills() -> Tuple[List[str], List[int]]:
    """
    Extract ALL unique hard skills from gold_standard_annotations.

    Returns:
        (skill_texts, global_frequencies)
    """
    print("="*80)
    print("EXTRACTING ALL GOLD STANDARD SKILLS")
    print("="*80)

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Get all unique hard skills with their global frequency
    query = """
        SELECT
            skill_text,
            COUNT(*) as frequency,
            COUNT(DISTINCT job_id) as job_count
        FROM gold_standard_annotations
        WHERE skill_type = 'hard'
        GROUP BY skill_text
        ORDER BY frequency DESC
    """

    cursor.execute(query)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    skill_texts = [row[0] for row in results]
    frequencies = [row[1] for row in results]

    print(f"   ✅ Extracted {len(skill_texts)} unique hard skills")
    print(f"   Frequency range: {min(frequencies)} - {max(frequencies)}")
    print(f"   Total annotations: {sum(frequencies):,}")

    return skill_texts, frequencies


def fetch_embeddings_batch(skill_texts: List[str]) -> Tuple[np.ndarray, List[str], List[int]]:
    """
    Fetch embeddings for all skills with embeddings.

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
    Run UMAP + HDBSCAN clustering with production parameters.

    Returns:
        (coordinates, labels, cluster_analysis, metrics)
    """
    print("\n" + "="*80)
    print("RUNNING UMAP + HDBSCAN CLUSTERING")
    print("="*80)

    # UMAP reduction
    print("\n🚀 UMAP dimensionality reduction...")
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
    clusterer = SkillClusterer(
        min_cluster_size=5,
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

    return coordinates, labels, cluster_analysis, metrics


def extract_temporal_frequencies(skill_texts: List[str]) -> pd.DataFrame:
    """
    Extract skill frequencies by quarter from gold_standard_annotations.

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
    query = """
        SELECT
            DATE_TRUNC('quarter', j.posted_date) as quarter,
            gsa.skill_text,
            COUNT(*) as frequency
        FROM gold_standard_annotations gsa
        JOIN raw_jobs j ON gsa.job_id = j.job_id
        WHERE gsa.skill_type = 'hard'
          AND j.posted_date IS NOT NULL
        GROUP BY DATE_TRUNC('quarter', j.posted_date), gsa.skill_text
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

    # Create cluster name mapping
    cluster_names = {}
    for c in cluster_analysis:
        if c['cluster_id'] == -1:
            cluster_names[-1] = "Noise"
        else:
            # Use top 2 skills as label
            top_skills = c['top_skills'][:2]
            cluster_names[c['cluster_id']] = f"C{c['cluster_id']}: {', '.join(top_skills)}"

    # Rename columns
    renamed_matrix = matrix.copy()
    renamed_matrix.columns = [cluster_names.get(col, f"C{col}") for col in matrix.columns]

    # Create figure
    fig, ax = plt.subplots(figsize=(20, 12))

    # Plot heatmap
    sns.heatmap(
        renamed_matrix.T,  # Transpose: clusters as rows, quarters as columns
        cmap='YlOrRd',
        annot=False,
        fmt='g',
        cbar_kws={'label': 'Frequency'},
        linewidths=0.5,
        linecolor='white',
        ax=ax
    )

    # Customize
    ax.set_xlabel('Quarter', fontsize=14, weight='bold')
    ax.set_ylabel('Skill Cluster', fontsize=14, weight='bold')
    ax.set_title(
        'Skill Cluster Evolution Over Time (2015-2024)\n'
        'Color intensity = demand frequency',
        fontsize=16,
        weight='bold',
        pad=20
    )

    # Rotate x-axis labels for readability
    plt.xticks(rotation=90, ha='center', fontsize=9)
    plt.yticks(fontsize=10)

    plt.tight_layout()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"   ✅ Heatmap saved: {output_file}")


def visualize_line_charts(
    matrix: pd.DataFrame,
    cluster_analysis: List[Dict[str, Any]],
    output_path: str
):
    """Generate line charts showing evolution of top clusters."""

    print("\n" + "="*80)
    print("GENERATING LINE CHARTS")
    print("="*80)

    # Get top 10 clusters by total volume (excluding noise)
    cluster_totals = matrix.sum(axis=0).sort_values(ascending=False)
    top_clusters = [c for c in cluster_totals.head(10).index if c != -1]

    # Create cluster name mapping
    cluster_names = {}
    for c in cluster_analysis:
        if c['cluster_id'] != -1:
            top_skills = c['top_skills'][:2]
            cluster_names[c['cluster_id']] = ', '.join(top_skills)

    # Create figure
    fig, ax = plt.subplots(figsize=(18, 10))

    # Plot each cluster
    colors = sns.color_palette("husl", len(top_clusters))

    for i, cluster_id in enumerate(top_clusters):
        data = matrix[cluster_id]
        label = f"C{int(cluster_id)}: {cluster_names.get(cluster_id, 'Unknown')}"
        ax.plot(
            range(len(data)),
            data.values,
            marker='o',
            linewidth=2.5,
            markersize=6,
            label=label,
            color=colors[i],
            alpha=0.8
        )

    # Customize
    ax.set_xlabel('Quarter', fontsize=14, weight='bold')
    ax.set_ylabel('Demand Frequency', fontsize=14, weight='bold')
    ax.set_title(
        'Top 10 Skill Clusters: Demand Evolution Over Time',
        fontsize=16,
        weight='bold',
        pad=20
    )

    # Set x-axis labels (show every 4th quarter for readability)
    quarter_labels = matrix.index.tolist()
    x_positions = range(len(quarter_labels))
    ax.set_xticks([x for i, x in enumerate(x_positions) if i % 4 == 0])
    ax.set_xticklabels([q for i, q in enumerate(quarter_labels) if i % 4 == 0], rotation=45, ha='right')

    # Legend
    ax.legend(
        loc='upper left',
        fontsize=10,
        framealpha=0.95,
        ncol=2
    )

    # Grid
    ax.grid(True, alpha=0.3, linestyle='--')

    plt.tight_layout()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"   ✅ Line charts saved: {output_file}")


def visualize_umap_with_frequency(
    coordinates: np.ndarray,
    labels: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int],
    cluster_analysis: List[Dict[str, Any]],
    output_path: str
):
    """Generate UMAP scatter with point size proportional to frequency."""

    print("\n" + "="*80)
    print("GENERATING UMAP SCATTER WITH FREQUENCY")
    print("="*80)

    plt.style.use('seaborn-v0_8-whitegrid')

    fig, ax = plt.subplots(figsize=(16, 12))

    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
    colors = sns.color_palette("husl", n_clusters)

    # Normalize frequencies to reasonable sizes (20-500 pixels)
    freq_array = np.array(skill_frequencies)
    min_size, max_size = 20, 500
    sizes = min_size + (freq_array - freq_array.min()) / (freq_array.max() - freq_array.min()) * (max_size - min_size)

    # Plot each cluster
    for label in sorted(unique_labels):
        if label == -1:
            color = 'lightgray'
            marker = 'x'
            alpha = 0.3
            zorder = 1
        else:
            color = colors[label % len(colors)]
            marker = 'o'
            alpha = 0.6
            zorder = 2

        mask = labels == label

        ax.scatter(
            coordinates[mask, 0],
            coordinates[mask, 1],
            s=sizes[mask],  # Size by frequency
            c=[color],
            marker=marker,
            alpha=alpha,
            edgecolors='black',
            linewidth=0.5,
            label=f"Cluster {label}" if label != -1 else "Noise",
            zorder=zorder
        )

    # Add cluster labels for top 5 largest clusters
    cluster_sizes = [(c['cluster_id'], c['size']) for c in cluster_analysis if c['cluster_id'] != -1]
    cluster_sizes.sort(key=lambda x: x[1], reverse=True)
    top_clusters = [c_id for c_id, _ in cluster_sizes[:5]]

    for cluster_info in cluster_analysis:
        cluster_id = cluster_info['cluster_id']
        if cluster_id == -1 or cluster_id not in top_clusters:
            continue

        mask = labels == cluster_id
        centroid_x = coordinates[mask, 0].mean()
        centroid_y = coordinates[mask, 1].mean()

        label_text = f"C{cluster_id}: {cluster_info['auto_label'][:30]}"

        ax.text(
            centroid_x, centroid_y,
            label_text,
            fontsize=9,
            weight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.85, edgecolor='black', linewidth=1.5)
        )

    # Add size legend
    legend_sizes = [
        (freq_array.min(), min_size),
        (np.percentile(freq_array, 50), min_size + (max_size - min_size) * 0.5),
        (freq_array.max(), max_size)
    ]

    legend_elements = []
    for freq, size in legend_sizes:
        legend_elements.append(
            plt.scatter([], [], s=size, c='gray', alpha=0.6, edgecolors='black',
                       label=f'{int(freq)} occurrences')
        )

    # Create two legends: one for clusters, one for sizes
    legend1 = ax.legend(loc='upper right', fontsize=8, ncol=2, title='Clusters')
    ax.add_artist(legend1)

    ax.legend(handles=legend_elements, loc='lower right', fontsize=9, title='Frequency', framealpha=0.95)

    # Labels and title
    ax.set_xlabel('UMAP Dimension 1', fontsize=12, weight='bold')
    ax.set_ylabel('UMAP Dimension 2', fontsize=12, weight='bold')
    ax.set_title(
        f'Skill Clustering with Demand Frequency\n'
        f'{n_clusters} clusters | Point size = frequency',
        fontsize=14,
        weight='bold',
        pad=15
    )

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()

    print(f"   ✅ UMAP with frequency saved: {output_file}")


def save_results(
    skill_texts: List[str],
    skill_frequencies: List[int],
    coordinates: np.ndarray,
    labels: np.ndarray,
    cluster_analysis: List[Dict[str, Any]],
    metrics: Dict[str, float],
    temporal_matrix: pd.DataFrame,
    output_path: str
):
    """Save all results to JSON."""

    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    results = {
        'metadata': {
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'n_skills': len(skill_texts),
            'algorithm': 'UMAP + HDBSCAN',
            'parameters': {
                'umap': {
                    'n_components': 2,
                    'n_neighbors': 15,
                    'min_dist': 0.1,
                    'metric': 'cosine'
                },
                'hdbscan': {
                    'min_cluster_size': 5,
                    'min_samples': 5,
                    'metric': 'euclidean'
                }
            }
        },
        'metrics': metrics,
        'clusters': cluster_analysis,
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
        'temporal_matrix': {
            'quarters': temporal_matrix.index.tolist(),
            'cluster_ids': [int(c) for c in temporal_matrix.columns],
            'data': temporal_matrix.values.tolist()
        }
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"   ✅ Results saved: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")


def main():
    print("="*80)
    print("TEMPORAL CLUSTERING ANALYSIS - FULL PIPELINE")
    print("="*80)
    print()

    output_dir = Path('outputs/clustering/temporal')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 1: Extract all gold standard skills
    all_skills, all_frequencies = extract_all_gold_standard_skills()

    # Step 2: Fetch embeddings
    embeddings, found_skills, found_indices = fetch_embeddings_batch(all_skills)

    # Get frequencies for skills with embeddings
    found_frequencies = [all_frequencies[i] for i in found_indices]

    # Step 3: Run clustering
    coordinates, labels, cluster_analysis, metrics = run_clustering(
        embeddings, found_skills, found_frequencies
    )

    # Step 4: Extract temporal frequencies
    temporal_df = extract_temporal_frequencies(found_skills)

    # Step 5: Create temporal cluster matrix
    temporal_matrix, cluster_labels = create_cluster_temporal_matrix(
        temporal_df, found_skills, labels
    )

    # Step 6: Generate visualizations
    print("\n" + "="*80)
    print("GENERATING VISUALIZATIONS")
    print("="*80)

    visualize_temporal_heatmap(
        temporal_matrix,
        cluster_labels,
        cluster_analysis,
        output_dir / 'temporal_heatmap.png'
    )

    visualize_line_charts(
        temporal_matrix,
        cluster_analysis,
        output_dir / 'temporal_line_charts.png'
    )

    visualize_umap_with_frequency(
        coordinates,
        labels,
        found_skills,
        found_frequencies,
        cluster_analysis,
        output_dir / 'umap_with_frequency.png'
    )

    # Step 7: Save results
    save_results(
        found_skills,
        found_frequencies,
        coordinates,
        labels,
        cluster_analysis,
        metrics,
        temporal_matrix,
        output_dir / 'temporal_results.json'
    )

    # Summary
    print("\n" + "="*80)
    print("✅ TEMPORAL ANALYSIS COMPLETE")
    print("="*80)
    print(f"\n📁 Output directory: {output_dir}")
    print(f"\nGenerated files:")
    print(f"   📊 temporal_heatmap.png - Cluster evolution heatmap")
    print(f"   📈 temporal_line_charts.png - Top 10 clusters evolution")
    print(f"   🎯 umap_with_frequency.png - UMAP with size by frequency")
    print(f"   💾 temporal_results.json - Complete results data")
    print()


if __name__ == '__main__':
    main()
