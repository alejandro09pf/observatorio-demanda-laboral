#!/usr/bin/env python3
"""
Clustering Parameter Experimentation

This script runs clustering with multiple parameter configurations to determine
optimal settings for production.

Experiments:
1. Varying min_cluster_size (5, 10, 15, 20)
2. Varying UMAP n_neighbors (10, 15, 20, 30)
3. Combinations of best parameters

Usage:
    python scripts/experiment_clustering_parameters.py
    python scripts/experiment_clustering_parameters.py --quick  # Only test min_cluster_size
"""

import sys
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any, Tuple
from datetime import datetime
import time

import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns
from itertools import product

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer


def load_subset(subset_path: str) -> Tuple[List[str], List[int]]:
    """Load skill subset from JSON file."""
    with open(subset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    skill_texts = [s['skill_text'] for s in data['skills']]
    skill_frequencies = [s['frequency'] for s in data['skills']]

    return skill_texts, skill_frequencies


def fetch_embeddings(skill_texts: List[str]) -> np.ndarray:
    """Fetch embeddings from database for given skills."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    embeddings = []
    for skill_text in skill_texts:
        cursor.execute("""
            SELECT embedding
            FROM skill_embeddings
            WHERE LOWER(TRIM(skill_text)) = LOWER(TRIM(%s))
            LIMIT 1
        """, (skill_text,))

        result = cursor.fetchone()
        if result:
            embeddings.append(result[0])

    cursor.close()
    conn.close()

    return np.array(embeddings, dtype=np.float32)


def run_experiment(
    embeddings: np.ndarray,
    skill_texts: List[str],
    skill_frequencies: List[int],
    umap_params: Dict[str, Any],
    hdbscan_params: Dict[str, Any],
    experiment_name: str
) -> Dict[str, Any]:
    """Run a single clustering experiment with given parameters."""

    start_time = time.time()

    # UMAP reduction
    reducer = DimensionReducer(**umap_params)
    coordinates = reducer.fit_transform(embeddings)

    # HDBSCAN clustering
    clusterer = SkillClusterer(**hdbscan_params)
    labels = clusterer.fit_predict(coordinates)

    # Analyze clusters
    cluster_analysis = clusterer.analyze_clusters(labels, skill_texts, skill_frequencies)

    # Calculate metrics
    metrics = clusterer.calculate_metrics(coordinates, labels)

    duration = time.time() - start_time

    # Compile results
    results = {
        'experiment_name': experiment_name,
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'duration_seconds': duration,
        'umap_params': umap_params,
        'hdbscan_params': hdbscan_params,
        'metrics': metrics,
        'cluster_analysis': cluster_analysis,
        'coordinates': coordinates.tolist(),
        'labels': labels.tolist()
    }

    return results


def visualize_experiment(
    coordinates: np.ndarray,
    labels: np.ndarray,
    cluster_analysis: List[Dict[str, Any]],
    experiment_name: str,
    metrics: Dict[str, Any],
    output_path: str
):
    """Generate visualization for a single experiment."""

    plt.style.use('seaborn-v0_8-whitegrid')
    sns.set_palette("husl")

    fig, ax = plt.subplots(figsize=(14, 10))

    unique_labels = set(labels)
    n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)

    colors = sns.color_palette("husl", n_clusters)

    # Plot each cluster
    for i, label in enumerate(sorted(unique_labels)):
        if label == -1:
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

    # Add cluster labels (only top 5 clusters by size)
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

        label_text = f"C{cluster_id}: {cluster_info['auto_label'][:25]}"

        ax.text(
            centroid_x, centroid_y,
            label_text,
            fontsize=8,
            weight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.8, edgecolor='black', linewidth=1)
        )

    # Title with metrics
    title = (
        f'{experiment_name}\n'
        f'{n_clusters} clusters, {metrics["n_noise"]} noise ({metrics["noise_percentage"]:.1f}%) | '
        f'Silhouette: {metrics["silhouette_score"]:.3f}, Davies-Bouldin: {metrics["davies_bouldin_score"]:.3f}'
    )

    ax.set_xlabel('UMAP Dimension 1', fontsize=12)
    ax.set_ylabel('UMAP Dimension 2', fontsize=12)
    ax.set_title(title, fontsize=13, weight='bold')

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def create_comparison_table(all_results: List[Dict[str, Any]], output_path: str):
    """Create a comparison table of all experiments."""

    # Create figure with table
    fig, ax = plt.subplots(figsize=(16, len(all_results) * 0.8 + 2))
    ax.axis('off')

    # Prepare data
    headers = [
        'Experiment',
        'min_cluster_size',
        'n_neighbors',
        'Clusters',
        'Noise %',
        'Silhouette',
        'Davies-Bouldin',
        'Largest Cluster',
        'Duration (s)'
    ]

    rows = []
    for result in all_results:
        m = result['metrics']
        umap_p = result['umap_params']
        hdb_p = result['hdbscan_params']

        rows.append([
            result['experiment_name'],
            hdb_p['min_cluster_size'],
            umap_p['n_neighbors'],
            m['n_clusters'],
            f"{m['noise_percentage']:.1f}%",
            f"{m['silhouette_score']:.3f}",
            f"{m['davies_bouldin_score']:.3f}",
            m.get('largest_cluster_size', 0),
            f"{result['duration_seconds']:.1f}"
        ])

    # Create table
    table = ax.table(
        cellText=rows,
        colLabels=headers,
        cellLoc='center',
        loc='center',
        colWidths=[0.15, 0.10, 0.10, 0.08, 0.08, 0.10, 0.12, 0.12, 0.10]
    )

    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1, 2.5)

    # Style header
    for i in range(len(headers)):
        cell = table[(0, i)]
        cell.set_facecolor('#4CAF50')
        cell.set_text_props(weight='bold', color='white')

    # Color code rows by performance
    for i, result in enumerate(all_results, start=1):
        silhouette = result['metrics']['silhouette_score']

        if silhouette >= 0.5:
            color = '#E8F5E9'  # Light green
        elif silhouette >= 0.4:
            color = '#FFF9C4'  # Light yellow
        else:
            color = '#FFEBEE'  # Light red

        for j in range(len(headers)):
            table[(i, j)].set_facecolor(color)

    plt.title('Clustering Experiments Comparison', fontsize=16, weight='bold', pad=20)

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()


def print_experiment_summary(result: Dict[str, Any]):
    """Print summary of a single experiment."""
    m = result['metrics']

    print(f"\n{'='*70}")
    print(f"EXPERIMENT: {result['experiment_name']}")
    print(f"{'='*70}")
    print(f"Parameters:")
    print(f"  UMAP n_neighbors: {result['umap_params']['n_neighbors']}")
    print(f"  HDBSCAN min_cluster_size: {result['hdbscan_params']['min_cluster_size']}")
    print(f"\nResults:")
    print(f"  Clusters: {m['n_clusters']}")
    print(f"  Noise: {m['n_noise']} ({m['noise_percentage']:.1f}%)")
    print(f"  Silhouette: {m['silhouette_score']:.3f}")
    print(f"  Davies-Bouldin: {m['davies_bouldin_score']:.3f}")
    print(f"  Largest cluster: {m.get('largest_cluster_size', 0)} skills")
    print(f"  Smallest cluster: {m.get('smallest_cluster_size', 0)} skills")
    print(f"  Mean cluster size: {m.get('mean_cluster_size', 0):.1f}")
    print(f"  Duration: {result['duration_seconds']:.1f}s")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Run clustering parameter experiments"
    )
    parser.add_argument(
        '--subset',
        type=str,
        default='outputs/clustering/prototype_subset.json',
        help="Path to skill subset JSON"
    )
    parser.add_argument(
        '--quick',
        action='store_true',
        help="Quick mode: only test min_cluster_size variations"
    )
    parser.add_argument(
        '--output',
        type=str,
        default='outputs/clustering/experiments',
        help="Output directory for experiment results"
    )

    args = parser.parse_args()

    print("="*70)
    print("CLUSTERING PARAMETER EXPERIMENTATION")
    print("="*70)
    print(f"Mode: {'Quick (min_cluster_size only)' if args.quick else 'Full'}")
    print(f"Subset: {args.subset}")
    print(f"Output: {args.output}")
    print()

    # Load data
    print("📂 Loading data...")
    skill_texts, skill_frequencies = load_subset(args.subset)
    embeddings = fetch_embeddings(skill_texts)
    print(f"   ✅ Loaded {len(skill_texts)} skills with embeddings")

    # Define experiment configurations
    if args.quick:
        # Quick mode: only vary min_cluster_size
        experiments = [
            {
                'name': 'Baseline_mcs5',
                'umap': {'n_components': 2, 'n_neighbors': 15, 'min_dist': 0.1, 'metric': 'cosine', 'random_state': 42, 'verbose': False},
                'hdbscan': {'min_cluster_size': 5, 'min_samples': 5, 'metric': 'euclidean'}
            },
            {
                'name': 'Test_mcs10',
                'umap': {'n_components': 2, 'n_neighbors': 15, 'min_dist': 0.1, 'metric': 'cosine', 'random_state': 42, 'verbose': False},
                'hdbscan': {'min_cluster_size': 10, 'min_samples': 10, 'metric': 'euclidean'}
            },
            {
                'name': 'Test_mcs15',
                'umap': {'n_components': 2, 'n_neighbors': 15, 'min_dist': 0.1, 'metric': 'cosine', 'random_state': 42, 'verbose': False},
                'hdbscan': {'min_cluster_size': 15, 'min_samples': 15, 'metric': 'euclidean'}
            },
            {
                'name': 'Test_mcs20',
                'umap': {'n_components': 2, 'n_neighbors': 15, 'min_dist': 0.1, 'metric': 'cosine', 'random_state': 42, 'verbose': False},
                'hdbscan': {'min_cluster_size': 20, 'min_samples': 20, 'metric': 'euclidean'}
            }
        ]
    else:
        # Full mode: vary both parameters
        min_cluster_sizes = [5, 10, 15, 20]
        n_neighbors_values = [10, 15, 20, 30]

        experiments = []
        for mcs, nn in product(min_cluster_sizes, n_neighbors_values):
            experiments.append({
                'name': f'mcs{mcs}_nn{nn}',
                'umap': {'n_components': 2, 'n_neighbors': nn, 'min_dist': 0.1, 'metric': 'cosine', 'random_state': 42, 'verbose': False},
                'hdbscan': {'min_cluster_size': mcs, 'min_samples': mcs, 'metric': 'euclidean'}
            })

    print(f"\n🧪 Running {len(experiments)} experiments...\n")

    # Run all experiments
    all_results = []
    for i, exp_config in enumerate(experiments, 1):
        print(f"[{i}/{len(experiments)}] Running: {exp_config['name']}...", end=' ')

        result = run_experiment(
            embeddings,
            skill_texts,
            skill_frequencies,
            exp_config['umap'],
            exp_config['hdbscan'],
            exp_config['name']
        )

        all_results.append(result)
        print(f"✅ ({result['duration_seconds']:.1f}s)")

        # Generate visualization
        viz_path = f"{args.output}/viz_{exp_config['name']}.png"
        visualize_experiment(
            np.array(result['coordinates']),
            np.array(result['labels']),
            result['cluster_analysis'],
            exp_config['name'],
            result['metrics'],
            viz_path
        )

    # Save all results
    results_path = f"{args.output}/all_experiments.json"
    Path(results_path).parent.mkdir(parents=True, exist_ok=True)
    with open(results_path, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

    print(f"\n✅ All experiments complete!")
    print(f"   Results saved: {results_path}")

    # Print summaries
    for result in all_results:
        print_experiment_summary(result)

    # Create comparison table
    print(f"\n📊 Creating comparison table...")
    table_path = f"{args.output}/comparison_table.png"
    create_comparison_table(all_results, table_path)
    print(f"   ✅ Table saved: {table_path}")

    # Find best configuration
    print(f"\n{'='*70}")
    print("🏆 BEST CONFIGURATIONS")
    print(f"{'='*70}")

    # Best by silhouette
    best_silhouette = max(all_results, key=lambda x: x['metrics']['silhouette_score'])
    print(f"\n🥇 Best Silhouette Score ({best_silhouette['metrics']['silhouette_score']:.3f}):")
    print(f"   {best_silhouette['experiment_name']}")
    print(f"   min_cluster_size={best_silhouette['hdbscan_params']['min_cluster_size']}, "
          f"n_neighbors={best_silhouette['umap_params']['n_neighbors']}")
    print(f"   Clusters: {best_silhouette['metrics']['n_clusters']}, "
          f"Noise: {best_silhouette['metrics']['noise_percentage']:.1f}%")

    # Best by Davies-Bouldin (lower is better)
    best_db = min(all_results, key=lambda x: x['metrics']['davies_bouldin_score'])
    print(f"\n🥇 Best Davies-Bouldin Score ({best_db['metrics']['davies_bouldin_score']:.3f}):")
    print(f"   {best_db['experiment_name']}")
    print(f"   min_cluster_size={best_db['hdbscan_params']['min_cluster_size']}, "
          f"n_neighbors={best_db['umap_params']['n_neighbors']}")

    # Best balance (highest silhouette with <25% noise)
    balanced = [r for r in all_results if r['metrics']['noise_percentage'] < 25]
    if balanced:
        best_balanced = max(balanced, key=lambda x: x['metrics']['silhouette_score'])
        print(f"\n🥇 Best Balanced (Silhouette + <25% noise):")
        print(f"   {best_balanced['experiment_name']}")
        print(f"   Silhouette: {best_balanced['metrics']['silhouette_score']:.3f}, "
              f"Noise: {best_balanced['metrics']['noise_percentage']:.1f}%")
        print(f"   min_cluster_size={best_balanced['hdbscan_params']['min_cluster_size']}, "
              f"n_neighbors={best_balanced['umap_params']['n_neighbors']}")

    print(f"\n{'='*70}")
    print("📁 OUTPUT FILES")
    print(f"{'='*70}")
    print(f"   Results JSON: {results_path}")
    print(f"   Comparison table: {table_path}")
    print(f"   Visualizations: {args.output}/viz_*.png ({len(experiments)} files)")
    print()


if __name__ == '__main__':
    main()
