#!/usr/bin/env python3
"""
Generic Clustering Analysis Script

Performs complete clustering analysis on any dataset with temporal tracking:
- UMAP dimensionality reduction (768D → 2D)
- HDBSCAN clustering
- Temporal frequency analysis by quarter
- Visualization generation (heatmap, evolution, scatter)
- Quality metrics calculation

Usage:
    python scripts/clustering_generic.py --config outputs/clustering/config.json

The config file specifies:
- dataset_name: Name for outputs (e.g., "manual_300", "pipeline_b_pre")
- sql_query: Query to extract skills with frequencies
- temporal_sql_query: Query for temporal data (skills × quarters)
- output_dir: Where to save results
- clustering_params: UMAP + HDBSCAN parameters
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
import umap
import hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score
import matplotlib.pyplot as plt
import seaborn as sns

# Add src to path
sys.path.append('.')
from src.config import get_settings

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

    # Parse connection string
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
    """
    Extract skills using custom SQL query.

    Expected columns: skill_text, frequency, job_count
    """
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    logger.info(f"   ✅ Extracted {len(df)} unique skills")
    logger.info(f"   Frequency range: {df['frequency'].min()} - {df['frequency'].max()}")
    logger.info(f"   Total mentions: {df['frequency'].sum():,}")

    return df

def get_embeddings(skills: List[str]) -> np.ndarray:
    """Fetch embeddings from database."""
    conn = get_db_connection()
    cur = conn.cursor()

    logger.info(f"Requesting embeddings for {len(skills)} skills...")

    # Fetch embeddings
    placeholders = ','.join(['%s'] * len(skills))
    cur.execute(f"""
        SELECT skill_text, embedding
        FROM skill_embeddings
        WHERE LOWER(TRIM(skill_text)) IN ({placeholders})
    """, tuple(skill.lower().strip() for skill in skills))

    results = cur.fetchall()
    conn.close()

    # Create embedding dict (case-insensitive)
    embedding_dict = {row[0].lower().strip(): np.array(row[1]) for row in results}

    # Match embeddings to original skills (preserve order)
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
        logger.warning(f"   ⚠️  Missing embeddings for {len(missing)} skills")

    return embeddings, missing

def run_umap(embeddings: np.ndarray, params: Dict) -> np.ndarray:
    """Run UMAP dimensionality reduction."""
    logger.info(f"\n🚀 UMAP dimensionality reduction...")
    logger.info(f"   Parameters: n_neighbors={params['n_neighbors']}, min_dist={params['min_dist']}, metric={params['metric']}")

    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=params['n_neighbors'],
        min_dist=params['min_dist'],
        metric=params['metric'],
        random_state=42
    )

    embedding_2d = reducer.fit_transform(embeddings)

    logger.info(f"   ✅ UMAP complete: {embedding_2d.shape}")

    return embedding_2d

def run_hdbscan(embedding_2d: np.ndarray, params: Dict) -> np.ndarray:
    """Run HDBSCAN clustering."""
    logger.info(f"\n🚀 HDBSCAN clustering...")
    logger.info(f"   Parameters: min_cluster_size={params['min_cluster_size']}, min_samples={params['min_samples']}, metric={params['metric']}")

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=params['min_cluster_size'],
        min_samples=params['min_samples'],
        metric=params['metric']
    )

    labels = clusterer.fit_predict(embedding_2d)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)

    logger.info(f"   ✅ Clustering complete")
    logger.info(f"   Clusters detected: {n_clusters}")
    logger.info(f"   Noise points: {n_noise} ({100*n_noise/len(labels):.1f}%)")

    return labels

def analyze_clusters(df: pd.DataFrame, labels: np.ndarray) -> List[Dict]:
    """Analyze clusters and generate auto-labels."""
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

def calculate_metrics(embedding_2d: np.ndarray, labels: np.ndarray) -> Dict:
    """Calculate clustering quality metrics."""
    # Filter out noise points
    mask = labels != -1
    if mask.sum() < 2:
        return {
            'silhouette_score': None,
            'davies_bouldin_score': None
        }

    silhouette = silhouette_score(embedding_2d[mask], labels[mask])
    davies_bouldin = davies_bouldin_score(embedding_2d[mask], labels[mask])

    return {
        'silhouette_score': float(silhouette),
        'davies_bouldin_score': float(davies_bouldin)
    }

def extract_temporal_data(query: str, skills_list: List[str]) -> pd.DataFrame:
    """Extract temporal frequency data."""
    conn = get_db_connection()
    df = pd.read_sql_query(query, conn)
    conn.close()

    # Convert quarter to string if it's datetime
    if 'quarter' in df.columns and pd.api.types.is_datetime64_any_dtype(df['quarter']):
        df['quarter_str'] = df['quarter'].dt.to_period('Q').astype(str)
    elif 'quarter_str' not in df.columns:
        df['quarter_str'] = df['quarter'].astype(str)

    logger.info(f"   ✅ Extracted temporal data")
    logger.info(f"   Quarters: {df['quarter_str'].nunique()}")
    logger.info(f"   Date range: {df['quarter_str'].min()} - {df['quarter_str'].max()}")
    logger.info(f"   Total records: {len(df):,}")

    return df

def create_temporal_matrix(df_temporal: pd.DataFrame, df_clustered: pd.DataFrame) -> pd.DataFrame:
    """Create temporal cluster frequency matrix."""
    # Merge temporal data with cluster assignments
    df_merged = df_temporal.merge(
        df_clustered[['skill_text', 'cluster']],
        on='skill_text',
        how='left'
    )

    # Create pivot table
    matrix = df_merged.pivot_table(
        index='quarter_str',
        columns='cluster',
        values='frequency',
        aggfunc='sum',
        fill_value=0
    )

    logger.info(f"   ✅ Matrix shape: {matrix.shape}")
    logger.info(f"   Quarters: {len(matrix)}")
    logger.info(f"   Clusters: {len(matrix.columns)}")

    return matrix

def generate_visualizations(
    embedding_2d: np.ndarray,
    df: pd.DataFrame,
    temporal_matrix: pd.DataFrame,
    output_dir: Path
):
    """Generate all visualizations."""
    logger.info("\n" + "=" * 80)
    logger.info("GENERATING VISUALIZATIONS")
    logger.info("=" * 80)

    # 1. UMAP scatter
    logger.info("\n🎨 Generating UMAP scatter plot...")
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
    logger.info(f"   ✅ Saved: {output_dir}/umap_scatter.png")

    # 2. Temporal heatmap
    logger.info("\n🎨 Generating temporal heatmap...")
    plt.figure(figsize=(16, 10))
    sns.heatmap(temporal_matrix.T, cmap='YlOrRd', linewidths=0.5, cbar_kws={'label': 'Frequency'})
    plt.title('Cluster Evolution Over Time')
    plt.xlabel('Quarter')
    plt.ylabel('Cluster')
    plt.tight_layout()
    plt.savefig(output_dir / 'temporal_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: {output_dir}/temporal_heatmap.png")

    # 3. Top 10 clusters evolution
    logger.info("\n🎨 Generating top 10 clusters evolution...")
    top_10_clusters = temporal_matrix.sum().nlargest(10).index
    plt.figure(figsize=(14, 8))
    for cluster in top_10_clusters:
        if cluster != -1:
            plt.plot(temporal_matrix.index, temporal_matrix[cluster], marker='o', label=f'Cluster {cluster}')
    plt.title('Top 10 Clusters Evolution')
    plt.xlabel('Quarter')
    plt.ylabel('Frequency')
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig(output_dir / 'top_clusters_evolution.png', dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"   ✅ Saved: {output_dir}/top_clusters_evolution.png")

def save_results(
    df: pd.DataFrame,
    clusters: List[Dict],
    metrics: Dict,
    temporal_matrix: pd.DataFrame,
    config: Dict,
    output_dir: Path
):
    """Save all results to files."""
    logger.info("\n" + "=" * 80)
    logger.info("SAVING RESULTS")
    logger.info("=" * 80)

    # 1. Main results JSON
    results = {
        'metadata': {
            'dataset_name': config['dataset_name'],
            'created_at': datetime.now().isoformat(),
            'n_skills': len(df),
            'algorithm': 'UMAP + HDBSCAN',
            'parameters': config['clustering_params']
        },
        'metrics': {
            'n_clusters': len(clusters),
            'n_samples': len(df),
            'n_noise': int((df['cluster'] == -1).sum()),
            'noise_percentage': float(100 * (df['cluster'] == -1).sum() / len(df)),
            **metrics
        },
        'clusters': clusters
    }

    with open(output_dir / f"{config['dataset_name']}_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    logger.info(f"   ✅ Saved: {output_dir}/{config['dataset_name']}_results.json")

    # 2. Temporal matrix CSV
    temporal_matrix.to_csv(output_dir / 'temporal_matrix.csv')
    logger.info(f"   ✅ Saved: {output_dir}/temporal_matrix.csv")

    # 3. Metrics summary JSON
    metrics_summary = {
        'execution_date': datetime.now().isoformat(),
        'parameters': config['clustering_params'],
        'metrics': results['metrics']
    }

    with open(output_dir / 'metrics_summary.json', 'w') as f:
        json.dump(metrics_summary, f, indent=2)
    logger.info(f"   ✅ Saved: {output_dir}/metrics_summary.json")

def main():
    parser = argparse.ArgumentParser(description='Generic clustering analysis')
    parser.add_argument('--config', required=True, help='Path to config JSON file')
    args = parser.parse_args()

    # Load config
    with open(args.config) as f:
        config = json.load(f)

    dataset_name = config['dataset_name']
    output_dir = Path(config['output_dir'])
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info(f"CLUSTERING ANALYSIS: {dataset_name.upper()}")
    logger.info("=" * 80)
    logger.info(f"Output directory: {output_dir}")

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

    # Filter out skills without embeddings
    if missing:
        df = df[~df['skill_text'].isin(missing)].reset_index(drop=True)
        logger.info(f"   Using {len(df)} skills with embeddings")

    # Run UMAP
    logger.info("\n" + "=" * 80)
    logger.info("RUNNING UMAP + HDBSCAN CLUSTERING")
    logger.info("=" * 80)
    embedding_2d = run_umap(embeddings, config['clustering_params']['umap'])

    # Run HDBSCAN
    labels = run_hdbscan(embedding_2d, config['clustering_params']['hdbscan'])

    # Add labels to dataframe
    df['cluster'] = labels

    # Analyze clusters
    logger.info("\n📊 Analyzing clusters...")
    clusters = analyze_clusters(df, labels)

    # Calculate metrics
    logger.info("\n📏 Calculating metrics...")
    metrics = calculate_metrics(embedding_2d, labels)
    logger.info(f"   Silhouette score: {metrics['silhouette_score']:.3f}")
    logger.info(f"   Davies-Bouldin: {metrics['davies_bouldin_score']:.3f}")

    # Extract temporal data
    logger.info("\n" + "=" * 80)
    logger.info("EXTRACTING TEMPORAL FREQUENCIES")
    logger.info("=" * 80)
    df_temporal = extract_temporal_data(config['temporal_sql_query'], df['skill_text'].tolist())

    # Create temporal matrix
    logger.info("\n" + "=" * 80)
    logger.info("CREATING TEMPORAL CLUSTER MATRIX")
    logger.info("=" * 80)
    temporal_matrix = create_temporal_matrix(df_temporal, df)

    # Generate visualizations
    generate_visualizations(embedding_2d, df, temporal_matrix, output_dir)

    # Save results
    save_results(df, clusters, metrics, temporal_matrix, config, output_dir)

    # Final summary
    logger.info("\n" + "=" * 80)
    logger.info("✅ CLUSTERING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"   Skills clustered: {len(df)}")
    logger.info(f"   Clusters detected: {len(clusters)}")
    logger.info(f"   Silhouette score: {metrics['silhouette_score']:.3f}")
    logger.info(f"   Davies-Bouldin: {metrics['davies_bouldin_score']:.3f}")
    logger.info(f"   Temporal quarters: {len(temporal_matrix)}")
    logger.info(f"\n   All results saved to: {output_dir}/")
    logger.info("=" * 80)

if __name__ == "__main__":
    main()
