#!/usr/bin/env python3
"""
Comprehensive analysis of all clustering experiments to determine optimal configuration.
"""

import json
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def load_all_results():
    """Load results from all experiment runs."""

    # Load main experiments
    exp_path = Path('outputs/clustering/experiments/all_experiments.json')
    with open(exp_path) as f:
        main_exp = json.load(f)

    # Load fine-tuning experiments
    fine_path = Path('outputs/clustering/fine_tuning/fine_tuning_results.json')
    with open(fine_path) as f:
        fine_exp = json.load(f)

    all_results = []

    # Parse main experiments
    for exp in main_exp:
        all_results.append({
            'name': exp['experiment_name'],
            'mcs': exp['hdbscan_params']['min_cluster_size'],
            'nn': exp['umap_params']['n_neighbors'],
            'clusters': exp['metrics']['n_clusters'],
            'noise_pct': exp['metrics']['noise_percentage'],
            'silhouette': exp['metrics']['silhouette_score'],
            'davies_bouldin': exp['metrics']['davies_bouldin_score'],
            'max_size': exp['metrics'].get('largest_cluster_size', 0),
            'min_size': exp['metrics'].get('smallest_cluster_size', 0),
            'mean_size': exp['metrics'].get('mean_cluster_size', 0)
        })

    # Parse fine-tuning experiments
    for exp in fine_exp:
        all_results.append({
            'name': exp['name'],
            'mcs': exp['mcs'],
            'nn': exp['nn'],
            'clusters': exp['metrics']['n_clusters'],
            'noise_pct': exp['metrics']['noise_percentage'],
            'silhouette': exp['metrics']['silhouette_score'],
            'davies_bouldin': exp['metrics']['davies_bouldin_score'],
            'max_size': exp['metrics'].get('largest_cluster_size', 0),
            'min_size': exp['metrics'].get('smallest_cluster_size', 0),
            'mean_size': exp['metrics'].get('mean_cluster_size', 0)
        })

    return all_results


def analyze_trends(results):
    """Analyze trends across parameter variations."""

    print("="*80)
    print("COMPREHENSIVE EXPERIMENT ANALYSIS")
    print("="*80)
    print(f"\nTotal experiments: {len(results)}\n")

    # Group by min_cluster_size
    by_mcs = {}
    for r in results:
        mcs = r['mcs']
        if mcs not in by_mcs:
            by_mcs[mcs] = []
        by_mcs[mcs].append(r)

    print("="*80)
    print("TREND ANALYSIS BY min_cluster_size")
    print("="*80)
    print(f"\n{'mcs':<5} {'Count':<7} {'Avg Clusters':<13} {'Avg Noise %':<12} {'Avg Silhouette':<16} {'Range Clusters':<15}")
    print("-" * 80)

    for mcs in sorted(by_mcs.keys()):
        exps = by_mcs[mcs]
        avg_clusters = np.mean([e['clusters'] for e in exps])
        avg_noise = np.mean([e['noise_pct'] for e in exps])
        avg_sil = np.mean([e['silhouette'] for e in exps])
        min_clust = min([e['clusters'] for e in exps])
        max_clust = max([e['clusters'] for e in exps])

        print(f"{mcs:<5} {len(exps):<7} {avg_clusters:<13.1f} {avg_noise:<12.1f} {avg_sil:<16.3f} {min_clust}-{max_clust}")

    # Critical observation
    print("\n" + "="*80)
    print("🔍 CRITICAL OBSERVATION: CLUSTERING CLIFF")
    print("="*80)

    print("\n📊 Pattern detected:")
    print("   • mcs=5:  17 clusters (high granularity)")
    print("   • mcs=6:  8 clusters (moderate granularity)")
    print("   • mcs=7+: 2-3 clusters (collapsed granularity)")
    print("\n💡 Interpretation:")
    print("   The data has 2 main super-clusters:")
    print("   1. Concrete Technologies (JavaScript, Python, AWS, SQL, etc.)")
    print("   2. Abstract Concepts (Microservices, Architecture, Methodologies)")
    print("\n   Sub-clusters exist WITHIN these super-clusters:")
    print("   - Testing (spanish vs english)")
    print("   - Databases (SQL-specific)")
    print("   - Cloud (AWS, GCP, Terraform)")
    print("   - Data Engineering (pipelines, science)")

    # Trade-off analysis
    print("\n" + "="*80)
    print("⚖️  TRADE-OFF ANALYSIS")
    print("="*80)

    print("\nConfiguration Comparison:")
    print(f"\n{'Config':<15} {'Clusters':<10} {'Noise %':<10} {'Silhouette':<12} {'Granularity':<15} {'Quality':<10}")
    print("-" * 80)

    # Find representative configs
    configs = [
        ('mcs=5', [r for r in results if r['mcs'] == 5 and r['nn'] == 15][0]),
        ('mcs=6', [r for r in results if r['mcs'] == 6 and r['nn'] == 15][0]),
        ('mcs=7', [r for r in results if r['mcs'] == 7 and r['nn'] == 15][0]),
        ('mcs=8', [r for r in results if r['mcs'] == 8 and r['nn'] == 15][0]),
    ]

    for name, config in configs:
        gran = "BEST" if config['clusters'] > 10 else ("GOOD" if config['clusters'] > 5 else "POOR")
        qual = "BEST" if config['silhouette'] > 0.6 else ("GOOD" if config['silhouette'] > 0.45 else "MODERATE")

        print(f"{name:<15} {config['clusters']:<10} {config['noise_pct']:<10.1f} "
              f"{config['silhouette']:<12.3f} {gran:<15} {qual:<10}")

    return by_mcs


def score_configurations(results):
    """Score each configuration based on use case requirements."""

    print("\n" + "="*80)
    print("🎯 CONFIGURATION SCORING (Labor Observatory Context)")
    print("="*80)

    print("\nScoring Criteria:")
    print("  1. Granularity (40%): More clusters = better trend detection")
    print("  2. Silhouette (30%): Cluster quality")
    print("  3. Noise penalty (20%): Lower noise preferred")
    print("  4. Interpretability (10%): 5-20 clusters optimal\n")

    scored = []
    for r in results:
        # Granularity score (normalize clusters to 0-1, cap at 20)
        gran_score = min(r['clusters'] / 20.0, 1.0) * 0.4

        # Silhouette score (already 0-1)
        sil_score = max(r['silhouette'], 0) * 0.3

        # Noise penalty (inverse, normalize)
        noise_score = (1 - min(r['noise_pct'] / 50.0, 1.0)) * 0.2

        # Interpretability (optimal range 5-20 clusters)
        if 5 <= r['clusters'] <= 20:
            interp_score = 0.1
        elif r['clusters'] < 5:
            interp_score = 0.05
        else:
            interp_score = 0.08

        total_score = gran_score + sil_score + noise_score + interp_score

        scored.append({
            **r,
            'gran_score': gran_score,
            'sil_score': sil_score,
            'noise_score': noise_score,
            'interp_score': interp_score,
            'total_score': total_score
        })

    # Sort by total score
    scored.sort(key=lambda x: x['total_score'], reverse=True)

    print(f"{'Rank':<6} {'Config':<15} {'Clusters':<9} {'Silh':<6} {'Noise%':<8} {'Total':<7} "
          f"{'Gran':<6} {'Sil':<6} {'Noise':<7} {'Interp':<7}")
    print("-" * 95)

    for i, s in enumerate(scored[:10], 1):
        print(f"{i:<6} {s['name']:<15} {s['clusters']:<9} {s['silhouette']:<6.3f} "
              f"{s['noise_pct']:<8.1f} {s['total_score']:<7.3f} "
              f"{s['gran_score']:<6.3f} {s['sil_score']:<6.3f} {s['noise_score']:<7.3f} "
              f"{s['interp_score']:<7.2f}")

    return scored


def make_recommendations(scored_results):
    """Make final recommendations based on analysis."""

    print("\n" + "="*80)
    print("🏆 FINAL RECOMMENDATIONS")
    print("="*80)

    top = scored_results[0]

    print(f"\n✅ RECOMMENDED FOR PRODUCTION: {top['name']}")
    print(f"   min_cluster_size = {top['mcs']}")
    print(f"   n_neighbors = {top['nn']}")
    print(f"\n   Results:")
    print(f"   • Clusters: {top['clusters']}")
    print(f"   • Silhouette: {top['silhouette']:.3f}")
    print(f"   • Noise: {top['noise_pct']:.1f}%")
    print(f"   • Score: {top['total_score']:.3f}/1.0")

    print(f"\n   ✅ Justification:")
    print(f"   • Provides granular clusters for specific skill tracking")
    print(f"   • Silhouette {top['silhouette']:.3f} shows reasonable cluster cohesion")
    print(f"   • {top['clusters']} clusters enable detailed temporal analysis")
    print(f"   • Noise {top['noise_pct']:.1f}% is acceptable for HDBSCAN")

    # Alternative for quality-focused
    quality_focused = [r for r in scored_results if r['silhouette'] > 0.65]
    if quality_focused:
        alt = quality_focused[0]
        print(f"\n⚠️  ALTERNATIVE (Quality-focused): {alt['name']}")
        print(f"   min_cluster_size = {alt['mcs']}, n_neighbors = {alt['nn']}")
        print(f"   • Clusters: {alt['clusters']} (less granular)")
        print(f"   • Silhouette: {alt['silhouette']:.3f} (excellent quality)")
        print(f"   • Noise: {alt['noise_pct']:.1f}%")
        print(f"\n   ⚠️  Trade-off: Better metrics but LOSES granularity ({alt['clusters']} clusters)")
        print(f"   Not recommended for temporal analysis of specific skills")

    print("\n" + "="*80)
    print("📝 IMPLEMENTATION NOTES")
    print("="*80)
    print("\n1. Use recommended config for ALL temporal analysis")
    print("2. Accept moderate silhouette (0.4-0.5) as trade-off for granularity")
    print("3. High noise (20-30%) is expected and acceptable for HDBSCAN")
    print("4. Noise points represent:")
    print("   • Low-frequency skills (outliers)")
    print("   • Highly specific/niche skills")
    print("   • Skills that don't fit semantic clusters")
    print("\n5. For thesis:")
    print("   • Report BOTH metrics AND cluster interpretability")
    print("   • Emphasize practical value over perfect metrics")
    print("   • Show cluster examples (SQL, Cloud, Testing, etc.)")


def create_visualizations(results):
    """Create comprehensive comparison visualizations."""

    print("\n" + "="*80)
    print("📊 Generating comparison visualizations...")
    print("="*80)

    output_dir = Path('outputs/clustering/analysis')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter to nn=15 for cleaner comparison
    nn15 = [r for r in results if r['nn'] == 15]

    # 1. Multi-metric comparison
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    mcs_values = sorted(set(r['mcs'] for r in nn15))

    # Clusters vs mcs
    ax = axes[0, 0]
    clusters_by_mcs = [np.mean([r['clusters'] for r in nn15 if r['mcs'] == mcs]) for mcs in mcs_values]
    ax.plot(mcs_values, clusters_by_mcs, 'o-', linewidth=2, markersize=10, color='#2E86AB')
    ax.set_xlabel('min_cluster_size', fontsize=12, weight='bold')
    ax.set_ylabel('Number of Clusters', fontsize=12, weight='bold')
    ax.set_title('Clusters Detected vs min_cluster_size', fontsize=14, weight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=5, color='red', linestyle='--', alpha=0.5, label='Min acceptable (5)')
    ax.legend()

    # Silhouette vs mcs
    ax = axes[0, 1]
    sil_by_mcs = [np.mean([r['silhouette'] for r in nn15 if r['mcs'] == mcs]) for mcs in mcs_values]
    ax.plot(mcs_values, sil_by_mcs, 's-', linewidth=2, markersize=10, color='#A23B72')
    ax.set_xlabel('min_cluster_size', fontsize=12, weight='bold')
    ax.set_ylabel('Silhouette Score', fontsize=12, weight='bold')
    ax.set_title('Cluster Quality vs min_cluster_size', fontsize=14, weight='bold')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0.5, color='green', linestyle='--', alpha=0.5, label='Good threshold (0.5)')
    ax.legend()

    # Noise vs mcs
    ax = axes[1, 0]
    noise_by_mcs = [np.mean([r['noise_pct'] for r in nn15 if r['mcs'] == mcs]) for mcs in mcs_values]
    ax.plot(mcs_values, noise_by_mcs, '^-', linewidth=2, markersize=10, color='#F18F01')
    ax.set_xlabel('min_cluster_size', fontsize=12, weight='bold')
    ax.set_ylabel('Noise %', fontsize=12, weight='bold')
    ax.set_title('Noise Points vs min_cluster_size', fontsize=14, weight='bold')
    ax.grid(True, alpha=0.3)

    # Trade-off scatter
    ax = axes[1, 1]
    colors = ['#E63946' if r['mcs'] == 5 else '#06FFA5' if r['mcs'] == 6 else '#4361EE' for r in nn15]
    ax.scatter([r['clusters'] for r in nn15], [r['silhouette'] for r in nn15],
               s=[300 - r['noise_pct']*10 for r in nn15], c=colors, alpha=0.7, edgecolors='black')
    ax.set_xlabel('Number of Clusters (Granularity)', fontsize=12, weight='bold')
    ax.set_ylabel('Silhouette Score (Quality)', fontsize=12, weight='bold')
    ax.set_title('Granularity vs Quality Trade-off', fontsize=14, weight='bold')
    ax.grid(True, alpha=0.3)

    # Add annotations for key points
    for r in nn15:
        if r['mcs'] in [5, 6, 7, 8]:
            ax.annotate(f"mcs={r['mcs']}", (r['clusters'], r['silhouette']),
                       xytext=(5, 5), textcoords='offset points', fontsize=9)

    plt.tight_layout()
    path = output_dir / 'parameter_comparison.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"   ✅ {path.name}")

    return output_dir


def main():
    # Load all results
    results = load_all_results()

    # Analyze trends
    by_mcs = analyze_trends(results)

    # Score configurations
    scored = score_configurations(results)

    # Make recommendations
    make_recommendations(scored)

    # Create visualizations
    viz_dir = create_visualizations(results)

    print(f"\n{'='*80}")
    print("✅ ANALYSIS COMPLETE")
    print(f"{'='*80}")
    print(f"\nOutput directory: {viz_dir}")
    print("\nNext steps:")
    print("  1. Review recommendations above")
    print("  2. Check visualizations in outputs/clustering/analysis/")
    print("  3. Document decision in CLUSTERING_IMPLEMENTATION_LOG.md")
    print("  4. Run final clustering with recommended parameters")
    print()


if __name__ == '__main__':
    main()
