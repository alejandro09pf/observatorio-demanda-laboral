"""
Dimensionality reduction module using UMAP.

This module provides UMAP-based dimensionality reduction for skill embeddings,
reducing high-dimensional vectors (768D) to 2D/3D for visualization and clustering.
"""

from typing import Dict, Any, Optional
import logging
import numpy as np
import umap

from config.settings import get_settings

logger = logging.getLogger(__name__)


class DimensionReducer:
    """
    Reduce embedding dimensions using UMAP.

    UMAP (Uniform Manifold Approximation and Projection) is a dimensionality
    reduction technique that preserves both local and global structure of data.

    Parameters for clustering optimization:
    - n_components=2: Output dimensions (2D for visualization)
    - n_neighbors=15: Balance between local/global structure
    - min_dist=0.1: Minimum distance between points in low-dimensional space
    - metric='cosine': Distance metric (ideal for normalized embeddings)
    """

    def __init__(
        self,
        n_components: int = 2,
        n_neighbors: int = 15,
        min_dist: float = 0.1,
        metric: str = 'cosine',
        random_state: int = 42,
        verbose: bool = False
    ):
        """
        Initialize UMAP dimension reducer.

        Args:
            n_components: Output dimensions (2 for 2D visualization, 3 for 3D)
            n_neighbors: Number of neighbors to consider (5-50)
                - Lower values (5-10): Preserve fine details, many small clusters
                - Higher values (30-50): Preserve global structure, fewer large clusters
                - Default 15: Good balance for skill clustering
            min_dist: Minimum distance between points in embedding (0.0-0.5)
                - 0.0: Very tight clusters
                - 0.1: Default, good separation
                - 0.5: Very spread out
            metric: Distance metric for UMAP
                - 'cosine': Best for normalized embeddings (our case)
                - 'euclidean': For non-normalized vectors
            random_state: Random seed for reproducibility
            verbose: Print detailed UMAP progress
        """
        self.n_components = n_components
        self.n_neighbors = n_neighbors
        self.min_dist = min_dist
        self.metric = metric
        self.random_state = random_state
        self.verbose = verbose

        self.settings = get_settings()

        # Initialize UMAP reducer
        self.reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=n_neighbors,
            min_dist=min_dist,
            metric=metric,
            random_state=random_state,
            verbose=verbose
        )

        self.is_fitted = False
        self.embedding_ = None

        logger.info(
            f"DimensionReducer initialized: "
            f"n_components={n_components}, n_neighbors={n_neighbors}, "
            f"min_dist={min_dist}, metric={metric}"
        )

    def fit_transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Fit UMAP and transform embeddings to lower dimensions.

        Args:
            embeddings: Array of shape (n_samples, n_features)
                Example: (400, 768) for 400 skills with 768D embeddings

        Returns:
            coordinates: Array of shape (n_samples, n_components)
                Example: (400, 2) for 2D visualization

        Raises:
            ValueError: If embeddings shape is invalid
        """
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        if embeddings.ndim != 2:
            raise ValueError(
                f"Embeddings must be 2D array, got shape {embeddings.shape}"
            )

        n_samples, n_features = embeddings.shape

        logger.info(f"Fitting UMAP on {n_samples} samples with {n_features} features")
        logger.info(
            f"Parameters: n_neighbors={self.n_neighbors}, "
            f"min_dist={self.min_dist}, metric={self.metric}"
        )

        # Fit and transform
        coordinates = self.reducer.fit_transform(embeddings)

        self.is_fitted = True
        self.embedding_ = coordinates

        # Log statistics
        logger.info(f"UMAP transformation complete")
        logger.info(f"Output shape: {coordinates.shape}")

        if self.n_components == 2:
            x_min, x_max = coordinates[:, 0].min(), coordinates[:, 0].max()
            y_min, y_max = coordinates[:, 1].min(), coordinates[:, 1].max()
            logger.info(
                f"Coordinate ranges: "
                f"X=[{x_min:.2f}, {x_max:.2f}], "
                f"Y=[{y_min:.2f}, {y_max:.2f}]"
            )
        elif self.n_components == 3:
            x_min, x_max = coordinates[:, 0].min(), coordinates[:, 0].max()
            y_min, y_max = coordinates[:, 1].min(), coordinates[:, 1].max()
            z_min, z_max = coordinates[:, 2].min(), coordinates[:, 2].max()
            logger.info(
                f"Coordinate ranges: "
                f"X=[{x_min:.2f}, {x_max:.2f}], "
                f"Y=[{y_min:.2f}, {y_max:.2f}], "
                f"Z=[{z_min:.2f}, {z_max:.2f}]"
            )

        return coordinates

    def transform(self, embeddings: np.ndarray) -> np.ndarray:
        """
        Transform new embeddings using fitted UMAP model.

        This is useful for adding new skills to an existing embedding space.

        Args:
            embeddings: Array of shape (n_samples, n_features)

        Returns:
            coordinates: Array of shape (n_samples, n_components)

        Raises:
            RuntimeError: If UMAP has not been fitted yet
        """
        if not self.is_fitted:
            raise RuntimeError(
                "DimensionReducer must be fitted before transform(). "
                "Use fit_transform() first."
            )

        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)

        coordinates = self.reducer.transform(embeddings)

        logger.info(
            f"Transformed {embeddings.shape[0]} new samples to "
            f"{coordinates.shape[1]}D space"
        )

        return coordinates

    def get_parameters(self) -> Dict[str, Any]:
        """
        Get UMAP parameters for documentation and reproducibility.

        Returns:
            Dictionary with all UMAP parameters
        """
        return {
            'n_components': self.n_components,
            'n_neighbors': self.n_neighbors,
            'min_dist': self.min_dist,
            'metric': self.metric,
            'random_state': self.random_state,
            'is_fitted': self.is_fitted
        }

    def get_embedding(self) -> Optional[np.ndarray]:
        """
        Get the reduced embeddings from the last fit_transform.

        Returns:
            Coordinates array if fitted, None otherwise
        """
        return self.embedding_
