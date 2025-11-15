"""
Clusters Router - Clustering results and analysis.
"""
from fastapi import APIRouter, HTTPException, Path as PathParam
from fastapi.responses import FileResponse
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
        config: Configuration name (e.g., "pipeline_b_300_post", "manual_300_pre")

    Returns:
        Dict with clustering results
    """
    project_root = Path(__file__).parent.parent.parent.parent

    # Try loading from final/ directory first (new structure)
    final_path = project_root / "outputs" / "clustering" / "final" / config / f"{config}_final_results.json"
    if final_path.exists():
        with open(final_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Fallback to legacy paths
    results_path = project_root / "outputs" / "clustering" / f"{config}.json"
    if results_path.exists():
        with open(results_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Final fallback to main file
    main_path = project_root / "outputs" / "clustering" / "clustering_results.json"
    if main_path.exists():
        with open(main_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    raise FileNotFoundError(f"Clustering results not found for config: {config}")


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
        List of available config names with metadata
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        final_dir = project_root / "outputs" / "clustering" / "final"

        configs = []

        if final_dir.exists():
            # List all directories in final/
            for config_dir in final_dir.iterdir():
                if config_dir.is_dir():
                    config_name = config_dir.name

                    # Check if results file exists
                    results_file = config_dir / f"{config_name}_final_results.json"
                    metrics_file = config_dir / "metrics_summary.json"

                    if results_file.exists():
                        # Count images
                        images = list(config_dir.glob("*.png"))

                        # Parse config name to extract metadata
                        # Formats: manual_300_post, pipeline_a_300_post, pipeline_b_300_pre, pipeline_a_30k_post
                        parts = config_name.split('_')

                        if config_name.startswith("manual"):
                            pipeline_type = "manual"
                            dataset_size = parts[1] if len(parts) > 1 else "unknown"
                            esco_stage = parts[2] if len(parts) > 2 else "unknown"
                        elif config_name.startswith("pipeline_a"):
                            pipeline_type = "pipeline_a"
                            dataset_size = parts[2] if len(parts) > 2 else "unknown"
                            esco_stage = parts[3] if len(parts) > 3 else "unknown"
                        elif config_name.startswith("pipeline_b"):
                            pipeline_type = "pipeline_b"
                            dataset_size = parts[2] if len(parts) > 2 else "unknown"
                            esco_stage = parts[3] if len(parts) > 3 else "unknown"
                        else:
                            pipeline_type = parts[0] if len(parts) > 0 else "unknown"
                            dataset_size = parts[1] if len(parts) > 1 else "unknown"
                            esco_stage = parts[2] if len(parts) > 2 else "unknown"

                        config_info = {
                            "name": config_name,
                            "pipeline": pipeline_type,  # manual, pipeline_a, pipeline_b
                            "size": dataset_size,       # 300, 30k
                            "esco_stage": esco_stage,   # pre, post
                            "has_results": True,
                            "has_metrics": metrics_file.exists(),
                            "image_count": len(images),
                            "images": [img.name for img in images]
                        }
                        configs.append(config_info)

        return {
            "count": len(configs),
            "configs": sorted(configs, key=lambda x: x["name"])
        }

    except Exception as e:
        logger.error(f"Error listing configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/images/{config}")
def list_config_images(config: str = PathParam(..., description="Configuration name")):
    """
    List all images available for a specific clustering configuration.

    Args:
        config: Configuration name (e.g., "pipeline_b_300_post")

    Returns:
        List of available image filenames
    """
    try:
        project_root = Path(__file__).parent.parent.parent.parent
        config_dir = project_root / "outputs" / "clustering" / "final" / config

        if not config_dir.exists():
            raise HTTPException(status_code=404, detail=f"Configuration {config} not found")

        # Find all PNG images
        images = list(config_dir.glob("*.png"))

        return {
            "config": config,
            "count": len(images),
            "images": [
                {
                    "filename": img.name,
                    "url": f"/api/clusters/image/{config}/{img.name}",
                    "size_kb": round(img.stat().st_size / 1024, 2)
                }
                for img in sorted(images)
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing images for config {config}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/clusters/image/{config}/{filename}")
def serve_cluster_image(
    config: str = PathParam(..., description="Configuration name"),
    filename: str = PathParam(..., description="Image filename")
):
    """
    Serve a specific clustering image file.

    Args:
        config: Configuration name
        filename: Image filename (must be .png)

    Returns:
        Image file
    """
    try:
        # Validate filename to prevent directory traversal
        if not filename.endswith('.png') or '/' in filename or '\\' in filename:
            raise HTTPException(status_code=400, detail="Invalid filename")

        project_root = Path(__file__).parent.parent.parent.parent
        image_path = project_root / "outputs" / "clustering" / "final" / config / filename

        if not image_path.exists():
            raise HTTPException(status_code=404, detail=f"Image {filename} not found for config {config}")

        # Verify it's actually in the allowed directory (security check)
        allowed_dir = project_root / "outputs" / "clustering" / "final" / config
        if not str(image_path.resolve()).startswith(str(allowed_dir.resolve())):
            raise HTTPException(status_code=403, detail="Access denied")

        return FileResponse(
            path=str(image_path),
            media_type="image/png",
            filename=filename
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving image {filename} for config {config}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
