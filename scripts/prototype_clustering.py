#!/usr/bin/env python3
"""
Clustering Prototype - End-to-End Pipeline

This script runs the complete clustering pipeline:
1. Load skill subset from JSON
2. Fetch embeddings from database
3. Apply UMAP dimensionality reduction (768D → 2D)
4. Apply HDBSCAN clustering
5. Generate visualizations
6. Export results

Usage:
    python scripts/prototype_clustering.py
    python scripts/prototype_clustering.py --subset outputs/clustering/prototype_subset.json
    python scripts/prototype_clustering.py --min-cluster-size 10 --output outputs/clustering/results
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime

import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer


def load_subset(subset_path: str) -> Dict[str, Any]:
    """Load skill subset from JSON file."""
    print(f"\n{'='*70}")
    print(f"LOADING SKILL SUBSET")
    print(f"{'='*70}")
    print(f"Path: {subset_path}\n")

    with open(subset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"✅ Loaded {len(data['skills'])} skills")
    print(f"   Created: {data['metadata']['created_at']}")
    print(f"   Model: {data['metadata']['model_info']['embedding_model']}")
    print(f"   Embedding dim: {data['metadata']['model_info']['embedding_dim']}")

    return data


def fetch_embeddings(skill_texts: List[str]) -> Tuple[np.ndarray, List[str]]:
    """
    Fetch embeddings from database for given skills.

    Returns:
        (embeddings_array, found_skills): Embeddings and corresponding skill texts
    """
    print(f"\n{'='*70}")
    print(f"FETCHING EMBEDDINGS FROM DATABASE")
    print(f"{'='*70}")
    print(f"Requesting {len(skill_texts)} skills\n")

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    embeddings = []
    found_skills = []
    missing_skills = []

    for skill_text in skill_texts:
        cursor.execute("""
            SELECT embedding
            FROM skill_embeddings
            WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            LIMIT 1
        """, (skill_text,))

        result = cursor.fetchone()

        if result:
            embeddings.append(result[0])  # PostgreSQL array
            found_skills.append(skill_text)
        else:
            missing_skills.append(skill_text)

    cursor.close()
    conn.close()

    embeddings_array = np.array(embeddings, dtype=np.float32)

    print(f"✅ Found: {len(found_skills)} skills")
    if missing_skills:
        print(f"⚠️  Missing: {len(missing_skills)} skills")
        if len(missing_skills) <= 10:
            for skill in missing_skills:
                print(f"     - {skill}")

    print(f"\n📊 Embeddings shape: {embeddings_array.shape}")

    return embeddings_array, found_skills


def run_umap(
    embeddings: np.ndarray,
    n_neighbors: int = 15,
    min_dist: float = 0.1
) -> np.ndarray:
    """Run UMAP dimensionality reduction."""
    print(f"\n{'='*70}")
    print(f"UMAP DIMENSIONALITY REDUCTION")
    print(f"{'='*70}")
    print(f"Input shape: {embeddings.shape}")
    print(f"Parameters:")
    print(f"  n_components: 2")
    print(f"  n_neighbors: {n_neighbors}")
    print(f"  min_dist: {min_dist}")
    print(f"  metric: cosine\n")

    reducer = DimensionReducer(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='cosine',
        random_state=42,
        verbose=False
    )

    print("🚀 Fitting UMAP...")
    coordinates = reducer.fit_transform(embeddings)

    print(f"✅ UMAP complete")
    print(f"   Output shape: {coordinates.shape}")
    print(f"   X range: [{coordinates[:, 0].min():.2f}, {coordinates[:, 0].max():.2f}]")
    print(f"   Y range: [{coordinates[:, 1].min():.2f}, {coordinates[:, 1].max():.2f}]")

    return coordinates


def run_hdbscan(
    coordinates: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int],
    min_cluster_size: int = 5
) -> Tuple[np.ndarray, List[Dict[str, Any]], Dict[str, float]]:
    """Run HDBSCAN clustering."""
    print(f"\n{'='*70}")
    print(f"HDBSCAN CLUSTERING")
    print(f"{'='*70}")
    print(f"Input shape: {coordinates.shape}")
    print(f"Parameters:")
    print(f"  min_cluster_size: {min_cluster_size}")
    print(f"  min_samples: {min_cluster_size}")
    print(f"  metric: euclidean\n")

    clusterer = SkillClusterer(
        min_cluster_size=min_cluster_size,
        min_samples=min_cluster_size,
        metric='euclidean',
        cluster_selection_method='eom'
    )

    print("🚀 Fitting HDBSCAN...")
    labels = clusterer.fit_predict(coordinates)

    print(f"\n📊 Analyzing clusters...")
    cluster_analysis = clusterer.analyze_clusters(labels, skill_texts, skill_frequencies)

    print(f"\n📏 Calculating quality metrics...")
    metrics = clusterer.calculate_metrics(coordinates, labels)

    return labels, cluster_analysis, metrics


def visualize_clusters(
    coordinates: np.ndarray,
    labels: np.ndarray,
    skill_texts: List[str],
    cluster_analysis: List[Dict[str, Any]],
    output_path: str
):
    """Generate 2D scatter plot of clusters."""
    print(f"\n{'='*70}")
    print(f"GENERATING VISUALIZATION")
    print(f"{'='*70}")

    # Set style
    plt.style.use('seaborn-v0_8-whitegrid')
    sns.set_palette("husl")

    # Create figure
    fig, ax = plt.subplots(figsize=(14, 10))

    # Get unique labels (including noise)
    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)

    # Color map
    colors = sns.color_palette("husl", n_clusters)

    # Plot each cluster
    for i, label in enumerate(sorted(unique_labels)):
        if label == -1:
            # Noise: gray
            color = 'lightgray'
            marker = 'x'
            size = 30
            alpha = 0.3
            zorder = 1
        else:
            color = colors[label % len(colors)]
            marker = 'o'
            size = 50
            alpha = 0.6
            zorder = 2

        mask = labels == label
        ax.scatter(
            coordinates[mask, 0],
            coordinates[mask, 1],
            c=[color],
            marker=marker,
            s=size,
            alpha=alpha,
            edgecolors='black',
            linewidth=0.5,
            label=f"Cluster {label}" if label != -1 else "Noise",
            zorder=zorder
        )

    # Add cluster labels
    for cluster_info in cluster_analysis:
        cluster_id = cluster_info['cluster_id']
        if cluster_id == -1:
            continue

        # Get cluster centroid
        mask = labels == cluster_id
        centroid_x = coordinates[mask, 0].mean()
        centroid_y = coordinates[mask, 1].mean()

        # Label text
        label_text = f"C{cluster_id}: {cluster_info['auto_label'][:30]}"

        # Add text
        ax.text(
            centroid_x, centroid_y,
            label_text,
            fontsize=9,
            weight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='white', alpha=0.7, edgecolor='black')
        )

    # Labels and title
    ax.set_xlabel('UMAP Dimension 1', fontsize=12)
    ax.set_ylabel('UMAP Dimension 2', fontsize=12)
    ax.set_title(
        f'Skill Clustering (UMAP + HDBSCAN)\n'
        f'{n_clusters} clusters, {(labels == -1).sum()} noise points',
        fontsize=14,
        weight='bold'
    )

    # Legend
    ax.legend(loc='upper right', fontsize=8, ncol=2)

    # Grid
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Visualization saved: {output_file}")

    plt.close()


def export_results(
    skill_texts: List[str],
    skill_frequencies: List[int],
    coordinates: np.ndarray,
    labels: np.ndarray,
    cluster_analysis: List[Dict[str, Any]],
    metrics: Dict[str, float],
    output_path: str
):
    """Export clustering results to JSON."""
    print(f"\n{'='*70}")
    print(f"EXPORTING RESULTS")
    print(f"{'='*70}")

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
        ]
    }

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"✅ Results exported: {output_file}")
    print(f"   Size: {output_file.stat().st_size / 1024:.1f} KB")


def print_summary(
    cluster_analysis: List[Dict[str, Any]],
    metrics: Dict[str, float]
):
    """Print clustering summary."""
    print(f"\n{'='*70}")
    print(f"📊 CLUSTERING SUMMARY")
    print(f"{'='*70}\n")

    print(f"🔢 Overall Statistics:")
    print(f"   Total skills:      {metrics['n_samples']}")
    print(f"   Clusters found:    {metrics['n_clusters']}")
    print(f"   Noise points:      {metrics['n_noise']} ({metrics['noise_percentage']:.1f}%)")

    if metrics['n_clusters'] > 0:
        print(f"\n📏 Quality Metrics:")
        print(f"   Silhouette score:  {metrics['silhouette_score']:.3f}")
        print(f"   Davies-Bouldin:    {metrics['davies_bouldin_score']:.3f}")

        print(f"\n📐 Cluster Sizes:")
        print(f"   Largest:           {metrics['largest_cluster_size']}")
        print(f"   Smallest:          {metrics['smallest_cluster_size']}")
        print(f"   Mean:              {metrics['mean_cluster_size']:.1f}")

    print(f"\n🏷️  Cluster Labels:")
    for cluster in cluster_analysis:
        if cluster['cluster_id'] == -1:
            continue
        print(f"   Cluster {cluster['cluster_id']:2d} ({cluster['size']:3d} skills): {cluster['auto_label'][:50]}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(
        description="Run clustering prototype on skill subset"
    )
    parser.add_argument(
        '--subset',
        type=str,
        default='outputs/clustering/prototype_subset.json',
        help="Path to skill subset JSON"
    )
    parser.add_argument(
        '--min-cluster-size',
        type=int,
        default=5,
        help="Minimum cluster size for HDBSCAN"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='outputs/clustering',
        help="Output directory for results"
    )

    args = parser.parse_args()

    print("="*70)
    print("SKILL CLUSTERING PROTOTYPE")
    print("="*70)
    print(f"Subset: {args.subset}")
    print(f"Min cluster size: {args.min_cluster_size}")
    print(f"Output: {args.output}")

    # Step 1: Load subset
    subset_data = load_subset(args.subset)
    skill_texts = [s['skill_text'] for s in subset_data['skills']]
    skill_frequencies = [s['frequency'] for s in subset_data['skills']]

    # Step 2: Fetch embeddings
    embeddings, found_skills = fetch_embeddings(skill_texts)

    # Update skills/frequencies to match found embeddings
    found_frequencies = [
        skill_frequencies[skill_texts.index(skill)]
        for skill in found_skills
    ]

    # Step 3: UMAP
    coordinates = run_umap(embeddings)

    # Step 4: HDBSCAN
    labels, cluster_analysis, metrics = run_hdbscan(
        coordinates,
        found_skills,
        found_frequencies,
        min_cluster_size=args.min_cluster_size
    )

    # Step 5: Visualize
    viz_path = f"{args.output}/clusters_umap_2d.png"
    visualize_clusters(coordinates, labels, found_skills, cluster_analysis, viz_path)

    # Step 6: Export results
    results_path = f"{args.output}/clustering_results.json"
    export_results(
        found_skills,
        found_frequencies,
        coordinates,
        labels,
        cluster_analysis,
        metrics,
        results_path
    )

    # Step 7: Summary
    print_summary(cluster_analysis, metrics)

    print(f"\n{'='*70}")
    print(f"✅ CLUSTERING PROTOTYPE COMPLETE")
    print(f"{'='*70}")
    print(f"\n📁 Output files:")
    print(f"   Visualization: {viz_path}")
    print(f"   Results JSON:  {results_path}")
    print(f"\n🎯 Next step: Analyze results and iterate on parameters")
    print()


if __name__ == '__main__':
    main()
