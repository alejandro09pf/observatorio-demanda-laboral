#!/usr/bin/env python3
"""
Clustering Analysis Script - Fase 9

Performs complete clustering analysis using src/analyzer modules:
- DimensionReducer (UMAP)
- SkillClusterer (HDBSCAN)
- Temporal frequency tracking
- Visualization generation

Usage:
    python scripts/clustering_analysis.py --config configs/clustering/pipeline_a_300_post.json
"""

import sys
import json
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
sys.path.append('.')
from src.config.settings import get_settings
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def get_db_connection():
    """Get database connection from settings."""
    settings = get_settings()
    db_url = settings.database_url
    parts = db_url.replace('postgresql://', '').split('@')
    user_pass = parts[0].split(':')
    host_port_db = parts[1].split('/')
    host_port = host_port_db[0].split(':')
    return psycopg2.connect(
        dbname=host_port_db[1],
        user=user_pass[0],
        password=user_pass[1],
        host=host_port[0],
        port=host_port[1]
    )


def extract_skills(query: str) -> pd.DataFrame:
    """Extract skills using SQL query."""
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"   ✅ Extracted {len(df)} unique skills")
    logger.info(f"   Frequency range: {df['frequency'].min()} - {df['frequency'].max()}")
    logger.info(f"   Total mentions: {df['frequency'].sum():,}")

    return df


def get_embeddings(skills: List[str]) -> Tuple[np.ndarray, List[str]]:
    """Fetch embeddings from database."""
    conn = get_db_connection()
    cur = conn.cursor()

    logger.info(f"Requesting embeddings for {len(skills)} skills...")

    placeholders = ','.join(['%s'] * len(skills))
    cur.execute(f"""
        SELECT skill_text, embedding
        FROM skill_embeddings
        WHERE LOWER(TRIM(skill_text)) IN ({placeholders})
    """, tuple(skill.lower().strip() for skill in skills))

    results = cur.fetchall()
    conn.close()

    embedding_dict = {row[0].lower().strip(): np.array(row[1]) for row in results}

    embeddings = []
    missing = []
    for skill in skills:
        key = skill.lower().strip()
        if key in embedding_dict:
            embeddings.append(embedding_dict[key])
        else:
            missing.append(skill)

    embeddings = np.array(embeddings)

    logger.info(f"   ✅ Found embeddings: {len(embeddings)}/{len(skills)}")
    logger.info(f"   Coverage: {100*len(embeddings)/len(skills):.1f}%")

    if missing:
        logger.warning(f"   ⚠️  Missing {len(missing)} skills")

    return embeddings, missing


def analyze_clusters(df: pd.DataFrame, labels: np.ndarray) -> List[Dict]:
    """Analyze clusters and generate metadata."""
    df_clustered = df.copy()
    df_clustered['cluster'] = labels

    clusters = []
    for cluster_id in sorted(set(labels)):
        if cluster_id == -1:
            continue

        cluster_skills = df_clustered[df_clustered['cluster'] == cluster_id]
        top_skills = cluster_skills.nlargest(5, 'frequency')['skill_text'].tolist()

        cluster_info = {
            'cluster_id': int(cluster_id),
            'size': len(cluster_skills),
            'label': ', '.join(top_skills[:3]) + '...',
            'top_skills': top_skills,
            'total_frequency': int(cluster_skills['frequency'].sum()),
            'mean_frequency': float(cluster_skills['frequency'].mean())
        }

        # Add meta_cluster if it exists
        if 'meta_cluster' in df_clustered.columns:
            # Get the most common meta_cluster for this cluster (should be consistent)
            meta_cluster_values = cluster_skills['meta_cluster'].dropna()
            if len(meta_cluster_values) > 0:
                cluster_info['meta_cluster'] = int(meta_cluster_values.mode()[0])

        clusters.append(cluster_info)

    return clusters


def extract_temporal_data(query: str) -> pd.DataFrame:
    """Extract temporal frequency data."""
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    if 'quarter' in df.columns and pd.api.types.is_datetime64_any_dtype(df['quarter']):
        df['quarter_str'] = df['quarter'].dt.to_period('Q').astype(str)
    elif 'quarter_str' not in df.columns:
        df['quarter_str'] = df['quarter'].astype(str)

    logger.info(f"   ✅ Extracted temporal data")
    logger.info(f"   Quarters: {df['quarter_str'].nunique()}")
    logger.info(f"   Date range: {df['quarter_str'].min()} - {df['quarter_str'].max()}")

    return df


def create_temporal_matrix(df_temporal: pd.DataFrame, df_clustered: pd.DataFrame) -> pd.DataFrame:
    """Create temporal cluster frequency matrix."""
    df_merged = df_temporal.merge(
        df_clustered[['skill_text', 'cluster']],
        on='skill_text',
        how='left'
    )

    matrix = df_merged.pivot_table(
        index='quarter_str',
        columns='cluster',
        values='frequency',
        aggfunc='sum',
        fill_value=0
    )

    logger.info(f"   ✅ Matrix shape: {matrix.shape}")

    return matrix


def generate_visualizations(embedding_2d: np.ndarray, df: pd.DataFrame,
                           temporal_matrix: pd.DataFrame, output_dir: Path):
    """Generate all visualizations."""
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING VISUALIZATIONS")
    logger.info("=" * 80)

    # 1. UMAP scatter WITH LABELS AND ANNOTATIONS
    logger.info("\n🎨 UMAP scatter plot (enhanced)...")
    fig, ax = plt.subplots(figsize=(20, 14))

    # Get unique clusters (excluding noise)
    clusters = sorted(df['cluster'].unique())
    clusters = [c for c in clusters if c != -1]

    # Use a better colormap with more distinct colors
    if len(clusters) <= 10:
        colors = plt.cm.tab10(np.linspace(0, 1, 10))
    elif len(clusters) <= 20:
        colors = plt.cm.tab20(np.linspace(0, 1, 20))
    else:
        colors = plt.cm.hsv(np.linspace(0, 1, len(clusters)))

    # Plot noise first (gray, transparent)
    noise_mask = df['cluster'] == -1
    if noise_mask.any():
        ax.scatter(
            embedding_2d[noise_mask, 0],
            embedding_2d[noise_mask, 1],
            c='lightgray',
            s=20,
            alpha=0.3,
            label='Noise',
            edgecolors='none'
        )

    # Plot each cluster with annotations
    for idx, cluster_id in enumerate(clusters):
        cluster_mask = df['cluster'] == cluster_id
        cluster_data = df[cluster_mask]
        cluster_coords = embedding_2d[cluster_mask]

        # Get color for this cluster
        color = colors[idx % len(colors)]

        # Plot cluster points
        sizes = cluster_data['frequency'].values * 3
        ax.scatter(
            cluster_coords[:, 0],
            cluster_coords[:, 1],
            c=[color],
            s=sizes,
            alpha=0.6,
            label=f'C{cluster_id} ({len(cluster_data)} skills)',
            edgecolors='black',
            linewidths=0.5
        )

        # Add cluster label at centroid
        centroid_x = cluster_coords[:, 0].mean()
        centroid_y = cluster_coords[:, 1].mean()

        # Get top 3 skills by frequency for this cluster
        top_skills_df = cluster_data.nlargest(3, 'frequency')
        top_skills_list = top_skills_df['skill_text'].tolist()
        label_text = f"C{cluster_id}\n" + "\n".join(top_skills_list[:2])

        # Add text annotation with background
        ax.annotate(
            label_text,
            xy=(centroid_x, centroid_y),
            xytext=(0, 0),
            textcoords='offset points',
            fontsize=9,
            fontweight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.7, edgecolor='black'),
            color='white'
        )

        # Annotate top 3 most frequent skills in cluster with skill names
        for i, (_, skill_row) in enumerate(top_skills_df.head(3).iterrows()):
            skill_idx = df.index[df['skill_text'] == skill_row['skill_text']].tolist()[0]
            coord = embedding_2d[skill_idx]

            ax.annotate(
                skill_row['skill_text'][:30],  # Truncate long names
                xy=(coord[0], coord[1]),
                xytext=(5, 5 + i*15),
                textcoords='offset points',
                fontsize=7,
                alpha=0.8,
                bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.8, edgecolor=color),
                arrowprops=dict(arrowstyle='->', color=color, lw=1)
            )

    ax.set_title('UMAP Projection with Labeled Clusters', fontsize=16, fontweight='bold')
    ax.set_xlabel('UMAP 1', fontsize=12)
    ax.set_ylabel('UMAP 2', fontsize=12)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(output_dir / 'umap_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: umap_scatter.png (enhanced with labels)")

    # 2. Temporal heatmap (only if temporal_matrix is available)
    if temporal_matrix is not None:
        logger.info("\n🎨 Temporal heatmap...")
        plt.figure(figsize=(16, 10))
        sns.heatmap(temporal_matrix.T, cmap='YlOrRd', linewidths=0.5, cbar_kws={'label': 'Frequency'})
        plt.title('Cluster Evolution Over Time')
        plt.xlabel('Quarter')
        plt.ylabel('Cluster')
        plt.tight_layout()
        plt.savefig(output_dir / 'temporal_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"   ✅ Saved: temporal_heatmap.png")

        # 3. Top 10 clusters evolution
        logger.info("\n🎨 Top clusters evolution...")
        top_10 = temporal_matrix.sum().nlargest(10).index
        plt.figure(figsize=(14, 8))
        for cluster in top_10:
            if cluster != -1:
                plt.plot(temporal_matrix.index, temporal_matrix[cluster], marker='o', label=f'C{cluster}')
        plt.title('Top 10 Clusters Evolution')
        plt.xlabel('Quarter')
        plt.ylabel('Frequency')
        plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_dir / 'top_clusters_evolution.png', dpi=300, bbox_inches='tight')
        plt.close()
        logger.info(f"   ✅ Saved: top_clusters_evolution.png")
    else:
        logger.info("\n⏭  Skipping temporal visualizations (no temporal data available)")


def save_results(df: pd.DataFrame, embedding_2d: np.ndarray, clusters: List[Dict], metrics: Dict,
                temporal_matrix: pd.DataFrame, config: Dict, output_dir: Path):
    """Save all results."""
    logger.info("\n" + "=" * 80)
    logger.info("SAVING RESULTS")
    logger.info("=" * 80)

    results = {
        'metadata': {
            'dataset_name': config['dataset_name'],
            'created_at': datetime.now().isoformat(),
            'n_skills': len(df),
            'algorithm': 'UMAP + HDBSCAN',
            'parameters': config['clustering_params']
        },
        'metrics': metrics,
        'clusters': clusters,
        'skills': df['skill_text'].tolist(),
        'embedding_2d': embedding_2d.tolist()
    }

    with open(output_dir / f"{config['dataset_name']}_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"   ✅ results.json")

    if temporal_matrix is not None:
        temporal_matrix.to_csv(output_dir / 'temporal_matrix.csv')
        logger.info(f"   ✅ temporal_matrix.csv")

    with open(output_dir / 'metrics_summary.json', 'w') as f:
        json.dump({
            'execution_date': datetime.now().isoformat(),
            'parameters': config['clustering_params'],
            'metrics': metrics
        }, f, indent=2)
    logger.info(f"   ✅ metrics_summary.json")


def perform_meta_clustering(
    df: pd.DataFrame,
    embeddings: np.ndarray,
    embedding_2d: np.ndarray,
    min_cluster_size: int = 5,
    min_samples: int = 2
) -> Tuple[np.ndarray, Dict]:
    """
    Perform hierarchical meta-clustering on fine-grained clusters.

    For each fine cluster, compute centroid embedding and cluster those centroids.
    This creates a two-level hierarchy: fine clusters → meta-clusters.
    """
    from sklearn.metrics import silhouette_score, davies_bouldin_score
    import hdbscan

    logger.info("\n" + "=" * 80)
    logger.info("META-CLUSTERING (Hierarchical Grouping)")
    logger.info("=" * 80)

    # Get unique clusters (excluding noise)
    fine_clusters = df[df['cluster'] != -1]['cluster'].unique()
    n_fine = len(fine_clusters)

    logger.info(f"Clustering {n_fine} fine-grained clusters into meta-clusters...")

    # Compute centroid embedding for each fine cluster
    cluster_centroids = []
    cluster_ids = []

    for cluster_id in sorted(fine_clusters):
        cluster_mask = df['cluster'] == cluster_id
        cluster_embeddings = embeddings[cluster_mask.values]

        # Centroid = mean of embeddings
        centroid = np.mean(cluster_embeddings, axis=0)
        cluster_centroids.append(centroid)
        cluster_ids.append(cluster_id)

    cluster_centroids = np.array(cluster_centroids)

    # Normalize centroids for cosine similarity via euclidean distance
    from sklearn.preprocessing import normalize
    cluster_centroids_normalized = normalize(cluster_centroids)

    # Apply HDBSCAN on cluster centroids (using euclidean on normalized vectors = cosine similarity)
    meta_clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric='euclidean',  # euclidean on normalized vectors = cosine similarity
        cluster_selection_method='eom'  # Use eom for macro-level
    )

    meta_labels = meta_clusterer.fit_predict(cluster_centroids_normalized)

    # Count meta-clusters
    n_meta = len(set(meta_labels)) - (1 if -1 in meta_labels else 0)
    n_meta_noise = sum(meta_labels == -1)

    logger.info(f"Meta-clusters detected: {n_meta}")
    logger.info(f"Unclustered fine clusters: {n_meta_noise}")

    # Map fine clusters to meta-clusters
    fine_to_meta = dict(zip(cluster_ids, meta_labels))

    # Assign meta-cluster to each skill
    df['meta_cluster'] = df['cluster'].map(fine_to_meta).fillna(-1).astype(int)

    # Calculate meta-clustering quality (only on successfully clustered centroids)
    meta_metrics = {}
    valid_mask = meta_labels != -1
    if valid_mask.sum() > 1:
        try:
            # Use normalized centroids for silhouette (euclidean on normalized = cosine)
            meta_silhouette = silhouette_score(
                cluster_centroids_normalized[valid_mask],
                meta_labels[valid_mask],
                metric='euclidean'
            )
            meta_davies_bouldin = davies_bouldin_score(
                cluster_centroids_normalized[valid_mask],
                meta_labels[valid_mask]
            )
            meta_metrics = {
                'n_meta_clusters': int(n_meta),
                'n_fine_clusters': int(n_fine),
                'n_unclustered_fine': int(n_meta_noise),
                'meta_silhouette': float(meta_silhouette),
                'meta_davies_bouldin': float(meta_davies_bouldin)
            }
            logger.info(f"Meta-clustering Silhouette: {meta_silhouette:.3f}")
            logger.info(f"Meta-clustering Davies-Bouldin: {meta_davies_bouldin:.3f}")
        except Exception as e:
            logger.warning(f"Could not calculate meta-clustering metrics: {e}")
            meta_metrics = {
                'n_meta_clusters': int(n_meta),
                'n_fine_clusters': int(n_fine),
                'n_unclustered_fine': int(n_meta_noise)
            }
    else:
        logger.warning("Not enough meta-clusters to calculate quality metrics")
        meta_metrics = {
            'n_meta_clusters': int(n_meta),
            'n_fine_clusters': int(n_fine),
            'n_unclustered_fine': int(n_meta_noise)
        }

    return df, meta_metrics


def generate_hierarchical_visualizations(
    df: pd.DataFrame,
    embedding_2d: np.ndarray,
    output_dir: Path
):
    """
    Generate improved hierarchical visualizations:
    1. Fine-grained view colored by meta-cluster WITH TOP SKILLS ANNOTATED (MORE TECH SKILLS)
    2. Macro view showing only TOP cluster centroids (max 40, better spacing)
    """
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING HIERARCHICAL VISUALIZATIONS")
    logger.info("=" * 80)

    # Get unique meta-clusters
    meta_clusters = sorted(df[df['meta_cluster'] != -1]['meta_cluster'].unique())
    n_meta = len(meta_clusters)

    # Generate distinct colors for meta-clusters
    from matplotlib import cm
    import matplotlib.colors as mcolors

    if n_meta <= 20:
        cmap = plt.colormaps.get_cmap('tab20')
        meta_colors = [mcolors.to_hex(cmap(i)) for i in range(20)]
    else:
        cmap = plt.colormaps.get_cmap('hsv')
        meta_colors = [mcolors.to_hex(cmap(i / n_meta)) for i in range(n_meta)]

    # Define tech keywords for prioritization
    tech_keywords = ['python', 'java', 'sql', 'aws', 'docker', 'kubernetes', 'react',
                     'node', 'git', 'api', 'cloud', 'data', 'machine learning', 'ml',
                     'tensorflow', 'spark', 'kafka', 'redis', 'mongodb', 'postgresql',
                     '.net', 'c#', 'javascript', 'typescript', 'angular', 'vue',
                     'spring', 'django', 'flask', 'ci/cd', 'devops', 'microservices',
                     'azure', 'gcp', 'terraform', 'jenkins', 'power bi', 'tableau',
                     'pandas', 'numpy', 'scikit', 'kubernetes', 'airflow', 'dbt',
                     'snowflake', 'redshift', 'bigquery', 'looker', 'metabase', 'grafana']

    # 1. Fine-grained view (colored by meta-cluster) WITH MORE TECH ANNOTATIONS
    logger.info("\n🎨 Fine-grained view (colored by meta-cluster with annotations)...")

    fig, ax = plt.subplots(figsize=(30, 22))

    # Plot noise
    noise_mask = df['cluster'] == -1
    if noise_mask.any():
        ax.scatter(
            embedding_2d[noise_mask, 0],
            embedding_2d[noise_mask, 1],
            c='lightgray',
            s=15,
            alpha=0.15,
            label='Noise',
            edgecolors='none'
        )

    # Plot each meta-cluster
    for meta_idx, meta_id in enumerate(meta_clusters):
        meta_mask = df['meta_cluster'] == meta_id
        if not meta_mask.any():
            continue

        color = meta_colors[meta_idx % len(meta_colors)]

        # Get all skills in this meta-cluster
        meta_coords = embedding_2d[meta_mask]
        meta_sizes = df[meta_mask]['frequency'].values * 3

        ax.scatter(
            meta_coords[:, 0],
            meta_coords[:, 1],
            c=[color],
            s=meta_sizes,
            alpha=0.6,
            label=f'Meta-C{meta_id} ({meta_mask.sum()} skills)',
            edgecolors='white',
            linewidths=0.5
        )

        # Add centroid label
        centroid_x = meta_coords[:, 0].mean()
        centroid_y = meta_coords[:, 1].mean()

        ax.annotate(
            f'META-{meta_id}',
            xy=(centroid_x, centroid_y),
            fontsize=18,
            fontweight='bold',
            ha='center',
            va='center',
            bbox=dict(boxstyle='circle,pad=0.5', facecolor=color, alpha=0.9, edgecolor='black', linewidth=3),
            color='white',
            zorder=100
        )

        # Annotate top 10 skills, prioritizing tech skills
        all_skills = df[meta_mask].nlargest(30, 'frequency')

        # Separate tech vs soft skills
        tech_skills = []
        soft_skills = []
        for _, skill_row in all_skills.iterrows():
            skill_name = skill_row['skill_text'].lower()
            is_tech = any(kw in skill_name for kw in tech_keywords)
            if is_tech:
                tech_skills.append((skill_row.name, skill_row))
            else:
                soft_skills.append((skill_row.name, skill_row))

        # Take top 7 tech + top 3 soft
        skills_to_annotate = tech_skills[:7] + soft_skills[:3]

        for i, (idx, skill_row) in enumerate(skills_to_annotate):
            coord = embedding_2d[idx]

            ax.annotate(
                skill_row['skill_text'][:45],
                xy=(coord[0], coord[1]),
                xytext=(15, 15 + i*18),
                textcoords='offset points',
                fontsize=9,
                alpha=0.95,
                bbox=dict(boxstyle='round,pad=0.5', facecolor=color, alpha=0.85, edgecolor='black', linewidth=1.5),
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                color='white',
                fontweight='bold',
                zorder=90
            )

    ax.set_title('UMAP: Skills Coloreados por Meta-Cluster (con top skills anotados)', fontsize=20, fontweight='bold')
    ax.set_xlabel('UMAP 1', fontsize=16)
    ax.set_ylabel('UMAP 2', fontsize=16)
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=11, ncol=1)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_dir / 'umap_fine_by_meta.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: umap_fine_by_meta.png")

    # 2. Macro view (TOP 40 cluster centroids only, better spacing)
    logger.info("\n🎨 Macro view (top cluster centroids)...")

    fig, ax = plt.subplots(figsize=(28, 20))

    # Get fine clusters (excluding noise) and sort by total frequency
    cluster_frequencies = df[df['cluster'] != -1].groupby('cluster')['frequency'].sum().sort_values(ascending=False)
    top_clusters = cluster_frequencies.head(40).index.tolist()

    logger.info(f"   Showing top {len(top_clusters)} clusters (by frequency)")

    # First, plot ALL clusters as small gray dots for context
    all_clusters = sorted(df[df['cluster'] != -1]['cluster'].unique())
    for cluster_id in all_clusters:
        if cluster_id in top_clusters:
            continue  # Skip top clusters, we'll plot them later

        cluster_mask = df['cluster'] == cluster_id
        cluster_coords = embedding_2d[cluster_mask]
        centroid_x = cluster_coords[:, 0].mean()
        centroid_y = cluster_coords[:, 1].mean()

        ax.scatter(centroid_x, centroid_y, c='lightgray', s=30, alpha=0.25, edgecolors='none')

    # Collect annotation data for adjustText
    texts = []
    scatter_points = []

    # Now plot top clusters with labels
    for cluster_id in top_clusters:
        cluster_mask = df['cluster'] == cluster_id
        cluster_data = df[cluster_mask]
        cluster_coords = embedding_2d[cluster_mask]

        # Get meta-cluster for coloring
        meta_id = cluster_data['meta_cluster'].iloc[0]

        if meta_id == -1:
            color = 'dimgray'
            alpha = 0.6
        else:
            meta_idx = meta_clusters.index(meta_id) if meta_id in meta_clusters else 0
            color = meta_colors[meta_idx % len(meta_colors)]
            alpha = 0.9

        # Compute centroid
        centroid_x = cluster_coords[:, 0].mean()
        centroid_y = cluster_coords[:, 1].mean()

        # Size by cluster size
        cluster_size = len(cluster_data)
        point_size = 250 + cluster_size * 25

        # Plot centroid
        scatter = ax.scatter(
            centroid_x,
            centroid_y,
            c=[color],
            s=point_size,
            alpha=alpha,
            edgecolors='black',
            linewidths=3,
            zorder=10
        )
        scatter_points.append((centroid_x, centroid_y))

        # Add label with top 2 skills
        top_skills = cluster_data.nlargest(2, 'frequency')['skill_text'].tolist()
        label_text = f"C{cluster_id} ({cluster_size})\n{top_skills[0][:35]}"
        if len(top_skills) > 1:
            label_text += f"\n{top_skills[1][:35]}"

        # Create text annotation (without position yet - adjustText will handle it)
        text = ax.text(
            centroid_x,
            centroid_y,
            label_text,
            fontsize=9,
            ha='center',
            va='center',
            bbox=dict(boxstyle='round,pad=0.6', facecolor='white', alpha=0.95,
                     edgecolor=color, linewidth=2.5),
            fontweight='bold',
            zorder=20
        )
        texts.append(text)

    # Use adjustText to avoid overlap
    try:
        from adjustText import adjust_text
        adjust_text(
            texts,
            arrowprops=dict(arrowstyle='->', color='gray', lw=1.5, alpha=0.7),
            expand_points=(1.5, 1.5),
            force_text=(0.5, 0.5),
            force_points=(0.2, 0.2),
            ax=ax
        )
        logger.info(f"   ✅ Used adjustText for label placement")
    except ImportError:
        logger.warning(f"   ⚠️  adjustText not available, labels may overlap")
        # Fallback: simple offset
        for i, (text, (cx, cy)) in enumerate(zip(texts, scatter_points)):
            offset_x = 15 if i % 2 == 0 else -15
            offset_y = 15 if i % 3 == 0 else -15
            text.set_position((cx + offset_x/100, cy + offset_y/100))

    ax.set_title(f'UMAP: Top {len(top_clusters)} Cluster Centroids (de {len(all_clusters)} totales)', fontsize=20, fontweight='bold')
    ax.set_xlabel('UMAP 1', fontsize=16)
    ax.set_ylabel('UMAP 2', fontsize=16)
    ax.grid(True, alpha=0.2)
    plt.tight_layout()
    plt.savefig(output_dir / 'umap_macro_centroids.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: umap_macro_centroids.png")


def main():
    parser = argparse.ArgumentParser(description='Clustering analysis using src/analyzer')
    parser.add_argument('--config', required=True, help='Path to config JSON')
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    dataset_name = config['dataset_name']
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"CLUSTERING: {dataset_name.upper()}")
    logger.info("=" * 80)

    # Extract skills
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTING SKILLS")
    logger.info("=" * 80)
    df = extract_skills(config['sql_query'])

    # Get embeddings
    logger.info("\n" + "=" * 80)
    logger.info("FETCHING EMBEDDINGS")
    logger.info("=" * 80)
    embeddings, missing = get_embeddings(df['skill_text'].tolist())

    if missing:
        df = df[~df['skill_text'].isin(missing)].reset_index(drop=True)
        logger.info(f"   Using {len(df)} skills with embeddings")

    # Run UMAP using src/analyzer/dimension_reducer.py
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING UMAP (src/analyzer/dimension_reducer.py)")
    logger.info("=" * 80)
    umap_params = config['clustering_params']['umap']
    reducer = DimensionReducer(**umap_params, verbose=True)
    embedding_2d = reducer.fit_transform(embeddings)

    # Run HDBSCAN using src/analyzer/clustering.py
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING HDBSCAN (src/analyzer/clustering.py)")
    logger.info("=" * 80)
    hdbscan_params = config['clustering_params']['hdbscan']
    clusterer = SkillClusterer(**hdbscan_params)
    labels = clusterer.fit_predict(embedding_2d)

    # Calculate metrics using clusterer
    metrics = clusterer.calculate_metrics(embedding_2d, labels)
    logger.info(f"\n📊 Clustering Results:")
    logger.info(f"   Clusters: {metrics['n_clusters']}")
    logger.info(f"   Noise: {metrics['n_noise']} ({metrics['noise_percentage']:.1f}%)")
    logger.info(f"   Silhouette: {metrics.get('silhouette_score', 0):.3f}")
    logger.info(f"   Davies-Bouldin: {metrics.get('davies_bouldin_score', 0):.3f}")

    # Add labels to dataframe
    df['cluster'] = labels

    # Perform meta-clustering (hierarchical grouping) FIRST
    meta_params = config.get('meta_clustering_params', {'min_cluster_size': 5, 'min_samples': 2})
    df, meta_metrics = perform_meta_clustering(
        df,
        embeddings,
        embedding_2d,
        **meta_params
    )

    # Add meta-metrics to overall metrics
    metrics.update(meta_metrics)

    # Analyze clusters AFTER meta-clustering (to include meta_cluster info)
    logger.info("\n📊 Analyzing clusters...")
    clusters = analyze_clusters(df, labels)

    # Temporal data (optional)
    temporal_matrix = None
    if 'temporal_sql_query' in config:
        logger.info("\n" + "=" * 80)
        logger.info("EXTRACTING TEMPORAL DATA")
        logger.info("=" * 80)
        df_temporal = extract_temporal_data(config['temporal_sql_query'])

        logger.info("\n" + "=" * 80)
        logger.info("CREATING TEMPORAL MATRIX")
        logger.info("=" * 80)
        temporal_matrix = create_temporal_matrix(df_temporal, df)
    else:
        logger.info("\n⏭  Skipping temporal analysis (no temporal_sql_query in config)")

    # Generate traditional visualizations
    generate_visualizations(embedding_2d, df, temporal_matrix, output_dir)

    # Generate hierarchical visualizations (with meta-clusters)
    generate_hierarchical_visualizations(df, embedding_2d, output_dir)

    # Save results
    save_results(df, embedding_2d, clusters, metrics, temporal_matrix, config, output_dir)

    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ CLUSTERING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"   Dataset: {dataset_name}")
    logger.info(f"   Skills: {len(df)}")
    logger.info(f"   Clusters: {metrics['n_clusters']}")
    logger.info(f"   Silhouette: {metrics['silhouette_score']:.3f}")
    logger.info(f"   Output: {output_dir}/")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
