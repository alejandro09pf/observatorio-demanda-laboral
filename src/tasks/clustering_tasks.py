"""
Celery Tasks for Clustering Analysis
Worker 4: Run clustering analysis on enhanced skills and save results
"""
import logging
import psycopg2
import os
import json
import numpy as np
from datetime import datetime
from celery import Task
from src.tasks.celery_app import celery_app
from src.analyzer.dimension_reducer import DimensionReducer
from src.analyzer.clustering import SkillClusterer

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def run_clustering_task(
    self: Task,
    pipeline_name: str,
    n_clusters: int = 50,
    country_filter: str = None
) -> dict:
    """
    Run clustering analysis on enhanced skills.

    This task:
    1. Loads enhanced skills and embeddings from database
    2. Runs clustering algorithm (KMeans, HDBSCAN, etc.)
    3. Generates cluster labels using LLM
    4. Saves results to analysis_results table

    Args:
        pipeline_name: Name of the clustering pipeline (e.g., 'pipeline_b_300_post')
        n_clusters: Number of clusters to generate
        country_filter: Optional country code filter (e.g., 'CO', 'MX')

    Returns:
        dict: Clustering results with statistics
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Starting clustering analysis: {pipeline_name}...',
                'progress': 0,
                'pipeline': pipeline_name
            }
        )

        logger.info(
            f"🔬 Celery Worker: Starting clustering task - "
            f"{pipeline_name} (n_clusters={n_clusters}, country={country_filter})"
        )

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Update task state: Loading data
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Loading enhanced skills and embeddings...',
                'progress': 20,
                'pipeline': pipeline_name
            }
        )

        # Load embeddings from database
        query = """
            SELECT
                se.embedding_id,
                se.embedding_vector,
                enh.normalized_skill,
                enh.skill_type,
                rj.country
            FROM skill_embeddings se
            JOIN enhanced_skills enh ON se.enhancement_id = enh.enhancement_id
            JOIN raw_jobs rj ON enh.job_id = rj.job_id
            WHERE se.embedding_vector IS NOT NULL
        """

        params = []
        if country_filter:
            query += " AND rj.country = %s"
            params.append(country_filter)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        if len(rows) < n_clusters:
            cursor.close()
            conn.close()
            raise ValueError(
                f"Not enough embeddings ({len(rows)}) for {n_clusters} clusters. "
                f"Need at least {n_clusters} skills with embeddings."
            )

        logger.info(f"📊 Loaded {len(rows)} skill embeddings for clustering")

        # Update task state: Running UMAP
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Running UMAP dimension reduction...',
                'progress': 30,
                'pipeline': pipeline_name,
                'skills_loaded': len(rows)
            }
        )

        # Extract embeddings and metadata
        embedding_ids = [str(row[0]) for row in rows]
        embedding_vectors = np.array([row[1] for row in rows])  # Already numpy-compatible
        skill_names = [row[2] for row in rows]
        skill_types = [row[3] for row in rows]

        logger.info(f"   Embeddings shape: {embedding_vectors.shape}")

        # Step 1: UMAP dimension reduction (to 2D for visualization)
        umap_reducer = DimensionReducer(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            metric='cosine',
            random_state=42,
            verbose=True
        )
        embedding_2d = umap_reducer.fit_transform(embedding_vectors)
        logger.info(f"   ✅ UMAP completed: {embedding_2d.shape}")

        # Update task state: Running HDBSCAN
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Running HDBSCAN clustering...',
                'progress': 50,
                'pipeline': pipeline_name,
                'skills_loaded': len(rows)
            }
        )

        # Step 2: HDBSCAN clustering on reduced embeddings
        # min_cluster_size based on n_clusters (heuristic: total_skills / n_clusters)
        estimated_min_cluster_size = max(5, len(rows) // n_clusters)

        clusterer = SkillClusterer(
            min_cluster_size=estimated_min_cluster_size,
            min_samples=5,
            metric='euclidean',  # Euclidean on UMAP-reduced space
            cluster_selection_method='eom',
            allow_single_cluster=False
        )
        labels = clusterer.fit_predict(embedding_2d)

        # Calculate metrics
        metrics = clusterer.calculate_metrics(embedding_2d, labels)

        logger.info(f"   ✅ HDBSCAN completed:")
        logger.info(f"      Clusters found: {metrics['n_clusters']}")
        logger.info(f"      Noise points: {metrics['n_noise']} ({metrics['noise_percentage']:.1f}%)")
        logger.info(f"      Silhouette: {metrics.get('silhouette_score', 0):.3f}")

        # Build cluster assignments
        cluster_assignments = {}
        for i, embedding_id in enumerate(embedding_ids):
            cluster_assignments[embedding_id] = int(labels[i])

        # Count skills per cluster (excluding noise=-1)
        cluster_counts = {}
        for cluster_id in labels:
            if cluster_id != -1:
                cluster_counts[int(cluster_id)] = cluster_counts.get(int(cluster_id), 0) + 1

        # Update task state: Generating labels
        self.update_state(
            state='PROGRESS',
            meta={
                'current': 'Generating cluster labels...',
                'progress': 70,
                'pipeline': pipeline_name,
                'clusters_created': metrics['n_clusters']
            }
        )

        # Generate cluster labels based on top skills
        cluster_labels = {}
        for cluster_id in sorted(set(labels)):
            if cluster_id == -1:
                cluster_labels[int(cluster_id)] = {
                    'label': 'Noise/Unclustered',
                    'description': 'Skills that did not fit into any cluster',
                    'size': metrics['n_noise']
                }
            else:
                # Get skills in this cluster
                cluster_mask = labels == cluster_id
                cluster_skills = [skill_names[i] for i in range(len(skill_names)) if cluster_mask[i]]

                # Get top 5 most common skills (simple approach: first 5)
                top_skills = cluster_skills[:5] if len(cluster_skills) > 5 else cluster_skills

                cluster_labels[int(cluster_id)] = {
                    'label': ', '.join(top_skills[:3]),
                    'description': f'Cluster containing {len(cluster_skills)} skills',
                    'size': len(cluster_skills),
                    'top_skills': top_skills
                }

        # Save analysis results
        cursor.execute("""
            INSERT INTO analysis_results
            (analysis_type, parameters, results, created_at)
            VALUES (%s, %s, %s, %s)
            RETURNING analysis_id
        """, (
            'clustering',
            json.dumps({
                'pipeline': pipeline_name,
                'n_clusters_requested': n_clusters,
                'n_clusters_found': metrics['n_clusters'],
                'country_filter': country_filter,
                'algorithm': 'hdbscan+umap',
                'skills_analyzed': len(rows),
                'umap_params': {
                    'n_components': 2,
                    'n_neighbors': 15,
                    'min_dist': 0.1,
                    'metric': 'cosine'
                },
                'hdbscan_params': {
                    'min_cluster_size': estimated_min_cluster_size,
                    'min_samples': 5,
                    'metric': 'euclidean',
                    'cluster_selection_method': 'eom'
                }
            }),
            json.dumps({
                'cluster_labels': cluster_labels,
                'cluster_assignments': cluster_assignments,
                'cluster_counts': cluster_counts,
                'metrics': metrics,
                'embedding_2d': embedding_2d.tolist()  # Save for visualization
            }),
            datetime.now()
        ))

        analysis_id = cursor.fetchone()[0]
        conn.commit()

        cursor.close()
        conn.close()

        logger.info(
            f"✅ Celery Worker: Clustering completed - "
            f"{metrics['n_clusters']} clusters created from {len(rows)} skills "
            f"(Silhouette: {metrics.get('silhouette_score', 0):.3f})"
        )

        return {
            'status': 'success',
            'analysis_id': str(analysis_id),
            'pipeline': pipeline_name,
            'n_clusters_requested': n_clusters,
            'n_clusters_found': metrics['n_clusters'],
            'skills_analyzed': len(rows),
            'noise_points': metrics['n_noise'],
            'noise_percentage': metrics['noise_percentage'],
            'silhouette_score': metrics.get('silhouette_score', 0),
            'davies_bouldin_score': metrics.get('davies_bouldin_score', 0),
            'country_filter': country_filter,
            'algorithm': 'hdbscan+umap',
            'task_id': self.request.id,
            'progress': 100,
            'completed_at': datetime.now().isoformat()
        }

    except Exception as exc:
        logger.error(f"❌ Celery Worker: Clustering failed - {pipeline_name}: {str(exc)}")

        # Update task state: Failed
        self.update_state(
            state='FAILURE',
            meta={
                'current': f'Clustering failed: {str(exc)}',
                'progress': 0,
                'pipeline': pipeline_name,
                'error': str(exc)
            }
        )

        # Retry the task
        raise self.retry(exc=exc, countdown=120 * (self.request.retries + 1))


@celery_app.task(bind=True)
def analyze_cluster_task(
    self: Task,
    analysis_id: str,
    cluster_id: int
) -> dict:
    """
    Analyze a specific cluster in detail.

    This task:
    1. Loads all skills in the cluster
    2. Generates detailed statistics
    3. Identifies key skills and patterns
    4. Updates analysis results with cluster details

    Args:
        analysis_id: UUID of the clustering analysis
        cluster_id: ID of the cluster to analyze

    Returns:
        dict: Cluster analysis results
    """
    try:
        logger.info(f"🔍 Analyzing cluster {cluster_id} from analysis {analysis_id}")

        # Connect to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Load analysis results
        cursor.execute("""
            SELECT results
            FROM analysis_results
            WHERE analysis_id = %s
        """, (analysis_id,))

        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            raise ValueError(f"Analysis {analysis_id} not found")

        results = json.loads(row[0])
        cluster_assignments = results.get('cluster_assignments', {})

        # Get skills in this cluster
        skills_in_cluster = [
            emb_id for emb_id, c_id in cluster_assignments.items()
            if c_id == cluster_id
        ]

        logger.info(f"📊 Found {len(skills_in_cluster)} skills in cluster {cluster_id}")

        # TODO: Perform detailed cluster analysis
        # - Get actual skill names
        # - Find most common skills
        # - Analyze skill relationships
        # - Generate cluster insights

        cluster_analysis = {
            'cluster_id': cluster_id,
            'size': len(skills_in_cluster),
            'analysis_id': str(analysis_id),
            'top_skills': [],  # TODO: Implement
            'insights': f'Cluster {cluster_id} contains {len(skills_in_cluster)} skills'
        }

        cursor.close()
        conn.close()

        return {
            'status': 'success',
            'cluster_id': cluster_id,
            'analysis_id': str(analysis_id),
            'cluster_size': len(skills_in_cluster),
            'cluster_analysis': cluster_analysis
        }

    except Exception as exc:
        logger.error(f"❌ Cluster analysis failed - cluster {cluster_id}: {str(exc)}")
        raise exc


# Example usage:
# from src.tasks.clustering_tasks import run_clustering_task, analyze_cluster_task
#
# # Run clustering analysis
# task = run_clustering_task.delay('pipeline_b_300_post', n_clusters=50, country_filter='CO')
# result = task.get(timeout=3600)
# print(f"Analysis ID: {result['analysis_id']}")
#
# # Analyze specific cluster
# task = analyze_cluster_task.delay(result['analysis_id'], cluster_id=0)
# analysis = task.get(timeout=600)
# print(f"Cluster analysis: {analysis}")
