"""
Skill clustering module using HDBSCAN.

This module provides HDBSCAN-based clustering for skills in reduced UMAP space,
detecting natural skill groupings and identifying noise/outliers.
"""

from typing import Dict, Any, List, Optional, Tuple
from collections import Counter
import logging
import numpy as np
import hdbscan
from sklearn.metrics import silhouette_score, davies_bouldin_score

logger = logging.getLogger(__name__)


class SkillClusterer:
    """
    Cluster skills using HDBSCAN in UMAP-reduced space.

    HDBSCAN (Hierarchical Density-Based Spatial Clustering of Applications with Noise)
    is a clustering algorithm that:
    - Finds clusters of varying densities
    - Automatically determines number of clusters
    - Identifies noise points (outliers)
    - Doesn't require specifying K (number of clusters)

    Best parameters for skill clustering:
    - min_cluster_size=5-10: Minimum skills per cluster (prototype)
    - min_cluster_size=15-20: For production (more robust)
    - min_samples=5: Minimum density
    - metric='euclidean': Distance in UMAP space
    """

    def __init__(
        self,
        min_cluster_size: int = 5,
        min_samples: Optional[int] = None,
        metric: str = 'euclidean',
        cluster_selection_method: str = 'eom',
        allow_single_cluster: bool = False
    ):
        """
        Initialize HDBSCAN clusterer.

        Args:
            min_cluster_size: Minimum number of samples in a cluster
                - Prototype: 5-10 (flexible, find small clusters)
                - Production: 15-20 (robust, meaningful clusters)
            min_samples: Minimum density (defaults to min_cluster_size if None)
                - Controls how conservative clustering is
                - Higher = fewer, denser clusters
            metric: Distance metric ('euclidean' for UMAP space)
            cluster_selection_method: How to select clusters
                - 'eom': Excess of Mass (default, good for varied densities)
                - 'leaf': More clusters, more granular
            allow_single_cluster: Allow all points in one cluster
                - Usually False (we want multiple clusters)
        """
        self.min_cluster_size = min_cluster_size
        self.min_samples = min_samples if min_samples is not None else min_cluster_size
        self.metric = metric
        self.cluster_selection_method = cluster_selection_method
        self.allow_single_cluster = allow_single_cluster

        # Initialize HDBSCAN
        self.clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=self.min_samples,
            metric=metric,
            cluster_selection_method=cluster_selection_method,
            allow_single_cluster=allow_single_cluster
        )

        self.labels_ = None
        self.probabilities_ = None
        self.is_fitted = False

        logger.info(
            f"SkillClusterer initialized: "
            f"min_cluster_size={min_cluster_size}, min_samples={self.min_samples}, "
            f"metric={metric}"
        )

    def fit_predict(self, coordinates: np.ndarray) -> np.ndarray:
        """
        Cluster skills in UMAP-reduced space.

        Args:
            coordinates: UMAP coordinates (n_samples, 2 or 3)
                Example: (400, 2) for 400 skills in 2D space

        Returns:
            labels: Cluster labels for each sample
                - 0, 1, 2, ...: Cluster IDs
                - -1: Noise points (skills that don't fit any cluster)

        Note:
            Noise points (-1) are expected and normal (10-30% is typical)
        """
        if not isinstance(coordinates, np.ndarray):
            coordinates = np.array(coordinates)

        if coordinates.ndim != 2:
            raise ValueError(
                f"Coordinates must be 2D array, got shape {coordinates.shape}"
            )

        n_samples, n_dims = coordinates.shape

        logger.info(f"Clustering {n_samples} samples in {n_dims}D space")
        logger.info(
            f"Parameters: min_cluster_size={self.min_cluster_size}, "
            f"min_samples={self.min_samples}"
        )

        # Fit and predict
        self.labels_ = self.clusterer.fit_predict(coordinates)
        self.probabilities_ = self.clusterer.probabilities_

        self.is_fitted = True

        # Log results
        n_clusters = len(set(self.labels_)) - (1 if -1 in self.labels_ else 0)
        n_noise = (self.labels_ == -1).sum()
        pct_noise = n_noise / len(self.labels_) * 100

        logger.info(f"Clustering complete")
        logger.info(f"Clusters detected: {n_clusters}")
        logger.info(f"Noise points: {n_noise} ({pct_noise:.1f}%)")

        # Cluster sizes
        if n_clusters > 0:
            cluster_sizes = Counter(self.labels_[self.labels_ != -1])
            logger.info(f"Cluster sizes: {dict(cluster_sizes)}")

        return self.labels_

    def analyze_clusters(
        self,
        labels: np.ndarray,
        skill_texts: List[str],
        skill_frequencies: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Analyze cluster composition and generate automatic labels.

        Args:
            labels: Cluster labels from fit_predict
            skill_texts: List of skill names
            skill_frequencies: Optional skill frequencies for weighting
                - If provided, top skills are selected by frequency
                - If None, all skills weighted equally

        Returns:
            List of cluster info dicts:
                {
                    'cluster_id': int,
                    'size': int,
                    'auto_label': str,  # "Python, AWS, Docker"
                    'top_skills': List[str],
                    'total_frequency': int
                }
        """
        if skill_frequencies is None:
            skill_frequencies = [1] * len(skill_texts)

        if len(labels) != len(skill_texts):
            raise ValueError(
                f"Labels length ({len(labels)}) != skill_texts length ({len(skill_texts)})"
            )

        cluster_info = []
        unique_labels = sorted(set(labels) - {-1})  # Exclude noise

        logger.info(f"Analyzing {len(unique_labels)} clusters...")

        for cluster_id in unique_labels:
            mask = labels == cluster_id

            # Get skills in this cluster
            cluster_skills = [skill_texts[i] for i in range(len(skill_texts)) if mask[i]]
            cluster_freqs = [skill_frequencies[i] for i in range(len(skill_texts)) if mask[i]]

            # Sort by frequency
            skill_freq_pairs = list(zip(cluster_skills, cluster_freqs))
            skill_freq_pairs.sort(key=lambda x: x[1], reverse=True)

            # Top 5 skills
            top_skills = [s for s, f in skill_freq_pairs[:5]]

            # Auto-label: top 3 skills
            auto_label = ", ".join(top_skills[:3])

            cluster_info.append({
                'cluster_id': int(cluster_id),
                'size': int(mask.sum()),
                'auto_label': auto_label,
                'top_skills': top_skills,
                'total_frequency': int(sum(cluster_freqs)),
                'mean_frequency': float(np.mean(cluster_freqs)),
                'all_skills': cluster_skills  # Include all for reference
            })

            logger.info(
                f"Cluster {cluster_id}: {mask.sum()} skills, "
                f"label='{auto_label[:50]}...'"
            )

        # Add noise cluster if exists
        if -1 in labels:
            mask = labels == -1
            noise_skills = [skill_texts[i] for i in range(len(skill_texts)) if mask[i]]

            cluster_info.append({
                'cluster_id': -1,
                'size': int(mask.sum()),
                'auto_label': 'Noise (unclustered)',
                'top_skills': noise_skills[:5] if noise_skills else [],
                'total_frequency': 0,
                'mean_frequency': 0.0,
                'all_skills': noise_skills
            })

            logger.info(f"Noise cluster: {mask.sum()} skills (outliers)")

        return cluster_info

    def calculate_metrics(
        self,
        coordinates: np.ndarray,
        labels: np.ndarray
    ) -> Dict[str, float]:
        """
        Calculate clustering quality metrics.

        Args:
            coordinates: UMAP coordinates
            labels: Cluster labels

        Returns:
            Dictionary with metrics:
                - silhouette_score: [-1, 1], higher is better (>0.5 = good)
                - davies_bouldin_score: [0, inf), lower is better (<1.0 = good)
                - n_clusters: Number of clusters found
                - noise_percentage: % of noise points
                - largest_cluster_size: Size of largest cluster
                - smallest_cluster_size: Size of smallest cluster (excluding noise)

        Note:
            Metrics are only calculated for non-noise points
        """
        # Filter out noise points for metrics
        mask = labels != -1
        n_noise = (labels == -1).sum()
        pct_noise = n_noise / len(labels) * 100

        # Basic stats
        metrics = {
            'n_clusters': int(len(set(labels)) - (1 if -1 in labels else 0)),
            'n_samples': int(len(labels)),
            'n_noise': int(n_noise),
            'noise_percentage': float(pct_noise)
        }

        # If too few clusters or too much noise, skip quality metrics
        if metrics['n_clusters'] < 2:
            logger.warning("Less than 2 clusters found, skipping quality metrics")
            metrics['silhouette_score'] = 0.0
            metrics['davies_bouldin_score'] = 0.0
            return metrics

        if mask.sum() < 10:
            logger.warning("Too few non-noise points, skipping quality metrics")
            metrics['silhouette_score'] = 0.0
            metrics['davies_bouldin_score'] = 0.0
            return metrics

        # Filter data
        filtered_coords = coordinates[mask]
        filtered_labels = labels[mask]

        # Silhouette Score: [-1, 1], higher is better
        # >0.7: Strong structure
        # >0.5: Reasonable structure
        # >0.25: Weak structure
        # <0.25: No substantial structure
        try:
            silhouette = silhouette_score(filtered_coords, filtered_labels)
            metrics['silhouette_score'] = float(silhouette)
        except Exception as e:
            logger.warning(f"Could not calculate silhouette score: {e}")
            metrics['silhouette_score'] = 0.0

        # Davies-Bouldin Score: [0, inf), lower is better
        # <1.0: Good separation
        # 1.0-2.0: Moderate separation
        # >2.0: Poor separation
        try:
            davies_bouldin = davies_bouldin_score(filtered_coords, filtered_labels)
            metrics['davies_bouldin_score'] = float(davies_bouldin)
        except Exception as e:
            logger.warning(f"Could not calculate Davies-Bouldin score: {e}")
            metrics['davies_bouldin_score'] = 0.0

        # Cluster size stats
        if metrics['n_clusters'] > 0:
            cluster_sizes = Counter(filtered_labels)
            metrics['largest_cluster_size'] = int(max(cluster_sizes.values()))
            metrics['smallest_cluster_size'] = int(min(cluster_sizes.values()))
            metrics['mean_cluster_size'] = float(np.mean(list(cluster_sizes.values())))
        else:
            metrics['largest_cluster_size'] = 0
            metrics['smallest_cluster_size'] = 0
            metrics['mean_cluster_size'] = 0.0

        logger.info(f"Quality metrics calculated:")
        logger.info(f"  Silhouette: {metrics['silhouette_score']:.3f}")
        logger.info(f"  Davies-Bouldin: {metrics['davies_bouldin_score']:.3f}")

        return metrics

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get HDBSCAN parameters for documentation.

        Returns:
            Dictionary with all clustering parameters
        """
        return {
            'min_cluster_size': self.min_cluster_size,
            'min_samples': self.min_samples,
            'metric': self.metric,
            'cluster_selection_method': self.cluster_selection_method,
            'allow_single_cluster': self.allow_single_cluster,
            'is_fitted': self.is_fitted
        }

    def get_cluster_probabilities(self) -> Optional[np.ndarray]:
        """
        Get cluster membership probabilities for each sample.

        Returns:
            Array of probabilities [0, 1] for each sample
            - 1.0: Strong cluster membership
            - 0.0: Noise point
        """
        return self.probabilities_
