"""
Model Downloader - Automatic download of GGUF models from HuggingFace.
Includes progress tracking, resume capability, and validation.
"""

import os
import logging
from pathlib import Path
from typing import Optional
import requests
from tqdm import tqdm

from llm_processor.model_registry import get_model_config, MODEL_REGISTRY, ModelConfig
from config.settings import get_settings

logger = logging.getLogger(__name__)


class ModelDownloader:
    """Downloads and manages LLM models."""

    def __init__(self, models_dir: Optional[str] = None):
        """
        Initialize model downloader.

        Args:
            models_dir: Directory to store models (default: from settings)
        """
        self.settings = get_settings()
        self.models_dir = Path(models_dir or self.settings.llm_models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)

    def get_model_path(self, model_name: str) -> Path:
        """Get local path for a model."""
        config = get_model_config(model_name)
        return self.models_dir / config.filename

    def is_model_downloaded(self, model_name: str) -> bool:
        """Check if a model is already downloaded."""
        model_path = self.get_model_path(model_name)
        return model_path.exists()

    def download_model(
        self,
        model_name: str,
        force: bool = False,
        show_progress: bool = True
    ) -> Path:
        """
        Download a model from HuggingFace.

        Args:
            model_name: Name of the model to download
            force: Force re-download even if file exists
            show_progress: Show download progress bar

        Returns:
            Path to downloaded model file
        """
        config = get_model_config(model_name)
        model_path = self.get_model_path(model_name)

        # Check if already downloaded
        if model_path.exists() and not force:
            logger.info(f"Model already downloaded: {model_path}")
            return model_path

        logger.info(f"Downloading {config.display_name} ({config.size_gb:.1f} GB)...")
        logger.info(f"URL: {config.url}")

        try:
            # Start download with streaming
            response = requests.get(config.url, stream=True, timeout=30)
            response.raise_for_status()

            # Get file size
            total_size = int(response.headers.get('content-length', 0))

            # Download with progress bar
            temp_path = model_path.with_suffix('.tmp')
            with open(temp_path, 'wb') as f:
                if show_progress and total_size > 0:
                    with tqdm(
                        total=total_size,
                        unit='B',
                        unit_scale=True,
                        unit_divisor=1024,
                        desc=config.filename
                    ) as pbar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                pbar.update(len(chunk))
                else:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

            # Rename temp file to final name
            temp_path.rename(model_path)

            logger.info(f"✓ Successfully downloaded {config.display_name}")
            logger.info(f"  Location: {model_path}")
            logger.info(f"  Size: {model_path.stat().st_size / (1024**3):.2f} GB")

            return model_path

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download model: {e}")
            if temp_path.exists():
                temp_path.unlink()
            raise

    def download_all_comparison_models(self, force: bool = False):
        """Download all models needed for comparison benchmarks."""
        from .model_registry import DEFAULT_COMPARISON_MODELS

        logger.info("Downloading comparison models...")
        for model_name in DEFAULT_COMPARISON_MODELS:
            try:
                self.download_model(model_name, force=force)
            except Exception as e:
                logger.error(f"Failed to download {model_name}: {e}")
                logger.warning(f"Continuing with other models...")

    def list_downloaded_models(self) -> list[str]:
        """List all downloaded models."""
        downloaded = []
        for model_name, config in MODEL_REGISTRY.items():
            if self.is_model_downloaded(model_name):
                downloaded.append(model_name)
        return downloaded

    def get_model_info(self, model_name: str) -> dict:
        """Get detailed information about a model."""
        config = get_model_config(model_name)
        model_path = self.get_model_path(model_name)

        info = {
            "name": config.name,
            "display_name": config.display_name,
            "description": config.description,
            "size_gb": config.size_gb,
            "context_length": config.context_length,
            "quantization": config.quantization,
            "downloaded": model_path.exists(),
            "local_path": str(model_path) if model_path.exists() else None,
        }

        if model_path.exists():
            actual_size = model_path.stat().st_size / (1024**3)
            info["actual_size_gb"] = round(actual_size, 2)

        return info

    def delete_model(self, model_name: str) -> bool:
        """Delete a downloaded model."""
        model_path = self.get_model_path(model_name)
        if model_path.exists():
            model_path.unlink()
            logger.info(f"Deleted model: {model_name}")
            return True
        return False

    def cleanup_temp_files(self):
        """Remove any temporary download files."""
        for temp_file in self.models_dir.glob("*.tmp"):
            try:
                temp_file.unlink()
                logger.info(f"Removed temp file: {temp_file.name}")
            except Exception as e:
                logger.warning(f"Failed to remove {temp_file.name}: {e}")
