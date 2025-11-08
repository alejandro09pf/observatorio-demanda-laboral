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

        clusters.append({
            'cluster_id': int(cluster_id),
            'size': len(cluster_skills),
            'label': ', '.join(top_skills[:3]) + '...',
            'top_skills': top_skills,
            'total_frequency': int(cluster_skills['frequency'].sum()),
            'mean_frequency': float(cluster_skills['frequency'].mean())
        })

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

    # 1. UMAP scatter
    logger.info("\n🎨 UMAP scatter plot...")
    plt.figure(figsize=(14, 10))
    scatter = plt.scatter(
        embedding_2d[:, 0],
        embedding_2d[:, 1],
        c=df['cluster'],
        s=df['frequency'] * 2,
        alpha=0.6,
        cmap='tab20'
    )
    plt.colorbar(scatter, label='Cluster')
    plt.title('UMAP Projection with Clusters')
    plt.xlabel('UMAP 1')
    plt.ylabel('UMAP 2')
    plt.tight_layout()
    plt.savefig(output_dir / 'umap_scatter.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: umap_scatter.png")

    # 2. Temporal heatmap
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


def save_results(df: pd.DataFrame, clusters: List[Dict], metrics: Dict,
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
        'clusters': clusters
    }

    with open(output_dir / f"{config['dataset_name']}_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"   ✅ results.json")

    temporal_matrix.to_csv(output_dir / 'temporal_matrix.csv')
    logger.info(f"   ✅ temporal_matrix.csv")

    with open(output_dir / 'metrics_summary.json', 'w') as f:
        json.dump({
            'execution_date': datetime.now().isoformat(),
            'parameters': config['clustering_params'],
            'metrics': metrics
        }, f, indent=2)
    logger.info(f"   ✅ metrics_summary.json")


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

    # Analyze clusters
    logger.info("\n📊 Analyzing clusters...")
    clusters = analyze_clusters(df, labels)

    # Temporal data
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTING TEMPORAL DATA")
    logger.info("=" * 80)
    df_temporal = extract_temporal_data(config['temporal_sql_query'])

    logger.info("\n" + "=" * 80)
    logger.info("CREATING TEMPORAL MATRIX")
    logger.info("=" * 80)
    temporal_matrix = create_temporal_matrix(df_temporal, df)

    # Generate visualizations
    generate_visualizations(embedding_2d, df, temporal_matrix, output_dir)

    # Save results
    save_results(df, clusters, metrics, temporal_matrix, config, output_dir)

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
