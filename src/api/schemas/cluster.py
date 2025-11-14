"""
Pydantic schemas for clustering endpoints.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class ClusterInfo(BaseModel):
    """Individual cluster information."""
    cluster_id: int
    size: int
    label: str
    top_skills: List[str]
    mean_frequency: float
    all_skills: Optional[List[str]] = None


class ClusterMetrics(BaseModel):
    """Clustering metrics."""
    n_clusters: int
    n_samples: int
    n_noise: int
    noise_percentage: float
    silhouette_score: float
    davies_bouldin_score: float
    largest_cluster_size: int
    smallest_cluster_size: int
    mean_cluster_size: float


class ClusterMetadata(BaseModel):
    """Clustering metadata."""
    created_at: str
    n_skills: int
    algorithm: str
    parameters: Dict[str, Any]


class ClusteringResponse(BaseModel):
    """Full clustering results response."""
    config: str
    metadata: ClusterMetadata
    metrics: ClusterMetrics
    clusters: List[ClusterInfo]
