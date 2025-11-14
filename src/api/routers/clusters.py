"""
Clusters Router - Clustering results and analysis.
"""
from fastapi import APIRouter, HTTPException, Path as PathParam
from typing import Optional, List, Dict, Any
import logging
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.schemas.cluster import ClusterInfo, ClusterMetrics, ClusterMetadata, ClusteringResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def load_clustering_results(config: str = "clustering_results") -> Dict[str, Any]:
    """
    Load clustering results from JSON file.

    Args:
        config: Configuration name (e.g., "clustering_results", "pipeline_b_300_post")

    Returns:
        Dict with clustering results
    """
    project_root = Path(__file__).parent.parent.parent.parent
    results_path = project_root / "outputs" / "clustering" / f"{config}.json"

    # Fallback to main file
    if not results_path.exists():
        results_path = project_root / "outputs" / "clustering" / "clustering_results.json"

    if not results_path.exists():
        raise FileNotFoundError(f"Clustering results not found: {results_path}")

    with open(results_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@router.get("/clusters", response_model=ClusteringResponse)
def get_clusters(
    config: Optional[str] = "clustering_results"
) -> ClusteringResponse:
    """
    Get clustering results.

    Args:
        config: Configuration name (default: "clustering_results")

    Returns:
        ClusteringResponse with clusters, metrics, and metadata
    """
    try:
        data = load_clustering_results(config)

        # Parse metadata
        metadata = ClusterMetadata(**data.get("metadata", {}))

        # Parse metrics
        metrics = ClusterMetrics(**data.get("metrics", {}))

        # Parse clusters
        clusters = [
            ClusterInfo(
                cluster_id=c["cluster_id"],
                size=c["size"],
                label=c.get("auto_label", ""),
                top_skills=c.get("top_skills", []),
                mean_frequency=c.get("mean_frequency", 0.0),
                all_skills=c.get("all_skills", None)
            )
            for c in data.get("clusters", [])
        ]

        return ClusteringResponse(
            config=config,
            metadata=metadata,
            metrics=metrics,
            clusters=clusters
        )

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting clusters: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving clustering results: {str(e)}")


@router.get("/clusters/{cluster_id}", response_model=ClusterInfo)
def get_cluster_detail(
    cluster_id: int = PathParam(..., ge=0, description="Cluster ID"),
    config: Optional[str] = "clustering_results"
) -> ClusterInfo:
    """
    Get detailed information about a specific cluster.

    Args:
        cluster_id: ID of the cluster
        config: Configuration name

    Returns:
        ClusterInfo with all skills in the cluster
    """
    try:
        data = load_clustering_results(config)

        # Find cluster
        cluster = next(
            (c for c in data.get("clusters", []) if c["cluster_id"] == cluster_id),
            None
        )

        if not cluster:
            raise HTTPException(status_code=404, detail=f"Cluster {cluster_id} not found")

        return ClusterInfo(
            cluster_id=cluster["cluster_id"],
            size=cluster["size"],
            label=cluster.get("auto_label", ""),
            top_skills=cluster.get("top_skills", []),
            mean_frequency=cluster.get("mean_frequency", 0.0),
            all_skills=cluster.get("all_skills", [])
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cluster detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/configs/available")
def list_available_configs():
    """
    List all available clustering configurations.

    Returns:
        List of available config names
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        clustering_dir = project_root / "outputs" / "clustering"

        if not clustering_dir.exists():
            return {"configs": []}

        # Find all JSON files
        json_files = list(clustering_dir.glob("*.json"))
        configs = [f.stem for f in json_files]

        return {
            "count": len(configs),
            "configs": sorted(configs)
        }

    except Exception as e:
        logger.error(f"Error listing configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))
