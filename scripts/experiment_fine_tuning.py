#!/usr/bin/env python3
"""
Fine-tuning clustering parameters.

Based on initial experiments, test intermediate values:
- min_cluster_size: 6, 7, 8, 9
- n_neighbors: 10, 15, 20, 25

Goal: Find balance between granularity (>5 clusters) and quality (silhouette >0.5)
"""

import sys
import json
from pathlib import Path
from typing import List, Tuple
from datetime import datetime
import time

import numpy as np
import psycopg2
import matplotlib.pyplot as plt
import seaborn as sns

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer


def load_subset(subset_path: str) -> Tuple[List[str], List[int]]:
    with open(subset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    skill_texts = [s['skill_text'] for s in data['skills']]
    skill_frequencies = [s['frequency'] for s in data['skills']]
    return skill_texts, skill_frequencies


def fetch_embeddings(skill_texts: List[str]) -> np.ndarray:
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


def run_experiment(embeddings, skill_texts, skill_frequencies, mcs, nn, exp_name):
    start = time.time()

    reducer = DimensionReducer(
        n_components=2, n_neighbors=nn, min_dist=0.1,
        metric='cosine', random_state=42, verbose=False
    )
    coords = reducer.fit_transform(embeddings)

    clusterer = SkillClusterer(
        min_cluster_size=mcs, min_samples=mcs, metric='euclidean'
    )
    labels = clusterer.fit_predict(coords)
    analysis = clusterer.analyze_clusters(labels, skill_texts, skill_frequencies)
    metrics = clusterer.calculate_metrics(coords, labels)

    duration = time.time() - start

    return {
        'name': exp_name,
        'mcs': mcs,
        'nn': nn,
        'metrics': metrics,
        'analysis': analysis,
        'coords': coords,
        'labels': labels,
        'duration': duration
    }


def main():
    print("="*70)
    print("FINE-TUNING CLUSTERING PARAMETERS")
    print("="*70)
    print("Goal: Balance granularity (>5 clusters) + quality (silhouette >0.5)\n")

    # Load data
    print("📂 Loading data...")
    skill_texts, skill_frequencies = load_subset('outputs/clustering/prototype_subset.json')
    embeddings = fetch_embeddings(skill_texts)
    print(f"   ✅ {len(skill_texts)} skills loaded\n")

    # Define experiments
    experiments = [
        # Fine-tune min_cluster_size (6-9) with default n_neighbors=15
        (6, 15, "mcs6_nn15"),
        (7, 15, "mcs7_nn15"),
        (8, 15, "mcs8_nn15"),
        (9, 15, "mcs9_nn15"),

        # Best min_cluster_size with different n_neighbors
        (7, 10, "mcs7_nn10"),
        (7, 20, "mcs7_nn20"),
        (7, 25, "mcs7_nn25"),

        (8, 10, "mcs8_nn10"),
        (8, 20, "mcs8_nn20"),
    ]

    print(f"🧪 Running {len(experiments)} fine-tuning experiments...\n")

    results = []
    for i, (mcs, nn, name) in enumerate(experiments, 1):
        print(f"[{i}/{len(experiments)}] {name} (mcs={mcs}, nn={nn})...", end=' ')
        result = run_experiment(embeddings, skill_texts, skill_frequencies, mcs, nn, name)
        results.append(result)

        m = result['metrics']
        print(f"✅ {m['n_clusters']} clusters, {m['noise_percentage']:.1f}% noise, "
              f"sil={m['silhouette_score']:.3f}")

    # Save results
    output_dir = Path('outputs/clustering/fine_tuning')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate comparison table
    print(f"\n{'='*70}")
    print("📊 RESULTS COMPARISON")
    print(f"{'='*70}\n")

    print(f"{'Experiment':<15} {'mcs':>3} {'nn':>3} {'Clusters':>8} {'Noise %':>8} "
          f"{'Silhouette':>11} {'Davies-B':>10} {'Max Size':>9}")
    print("-" * 90)

    for r in results:
        m = r['metrics']
        print(f"{r['name']:<15} {r['mcs']:>3} {r['nn']:>3} {m['n_clusters']:>8} "
              f"{m['noise_percentage']:>7.1f}% {m['silhouette_score']:>11.3f} "
              f"{m['davies_bouldin_score']:>10.3f} {m.get('largest_cluster_size', 0):>9}")

    # Find best configurations
    print(f"\n{'='*70}")
    print("🏆 TOP CONFIGURATIONS")
    print(f"{'='*70}\n")

    # Best granularity with good quality (>5 clusters, silhouette >0.45)
    good_granular = [r for r in results if r['metrics']['n_clusters'] > 5
                     and r['metrics']['silhouette_score'] > 0.45]

    if good_granular:
        best_granular = max(good_granular, key=lambda x: x['metrics']['silhouette_score'])
        print(f"🥇 Best Granular (>5 clusters, sil >0.45):")
        print(f"   {best_granular['name']}")
        print(f"   Clusters: {best_granular['metrics']['n_clusters']}, "
              f"Silhouette: {best_granular['metrics']['silhouette_score']:.3f}, "
              f"Noise: {best_granular['metrics']['noise_percentage']:.1f}%")

    # Best balance: maximize clusters * silhouette / (noise% + 1)
    scores = []
    for r in results:
        m = r['metrics']
        balance_score = (m['n_clusters'] * m['silhouette_score']) / (m['noise_percentage'] + 1)
        scores.append((r, balance_score))

    best_balance = max(scores, key=lambda x: x[1])
    print(f"\n🥇 Best Balance (clusters × silhouette / noise):")
    print(f"   {best_balance[0]['name']}")
    m = best_balance[0]['metrics']
    print(f"   Clusters: {m['n_clusters']}, Silhouette: {m['silhouette_score']:.3f}, "
          f"Noise: {m['noise_percentage']:.1f}%")
    print(f"   Balance score: {best_balance[1]:.2f}")

    # Visualization of top 3
    print(f"\n📊 Generating visualizations for top 3 configurations...")

    top_3 = sorted(scores, key=lambda x: x[1], reverse=True)[:3]

    for i, (result, score) in enumerate(top_3, 1):
        fig, ax = plt.subplots(figsize=(14, 10))

        coords = result['coords']
        labels = result['labels']

        unique_labels = set(labels)
        n_clusters = len(unique_labels) - (1 if -1 in unique_labels else 0)
        colors = sns.color_palette("husl", n_clusters)

        for label in sorted(unique_labels):
            if label == -1:
                color, marker, size, alpha = 'lightgray', 'x', 30, 0.3
            else:
                color, marker, size, alpha = colors[label % len(colors)], 'o', 50, 0.6

            mask = labels == label
            ax.scatter(coords[mask, 0], coords[mask, 1], c=[color], marker=marker,
                      s=size, alpha=alpha, edgecolors='black', linewidth=0.5)

        m = result['metrics']
        title = (f"{result['name']} (Rank #{i}, Score: {score:.2f})\n"
                f"{m['n_clusters']} clusters, {m['noise_percentage']:.1f}% noise | "
                f"Silhouette: {m['silhouette_score']:.3f}, Davies-Bouldin: {m['davies_bouldin_score']:.3f}")

        ax.set_title(title, fontsize=13, weight='bold')
        ax.set_xlabel('UMAP Dimension 1', fontsize=12)
        ax.set_ylabel('UMAP Dimension 2', fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        viz_path = output_dir / f"top{i}_{result['name']}.png"
        plt.savefig(viz_path, dpi=300, bbox_inches='tight')
        plt.close()

        print(f"   ✅ Top #{i}: {viz_path.name}")

    # Save detailed results
    results_json = []
    for r in results:
        results_json.append({
            'name': r['name'],
            'mcs': r['mcs'],
            'nn': r['nn'],
            'metrics': r['metrics'],
            'duration': r['duration']
        })

    json_path = output_dir / 'fine_tuning_results.json'
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results_json, f, indent=2)

    print(f"\n✅ Results saved: {json_path}")
    print(f"\n{'='*70}")
    print("✅ FINE-TUNING COMPLETE")
    print(f"{'='*70}\n")


if __name__ == '__main__':
    main()
