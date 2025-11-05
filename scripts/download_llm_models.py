#!/usr/bin/env python3
"""
Download LLM models for skill extraction.
Downloads Gemma 3 4B, Llama 3.2 3B, and Mistral 7B by default.
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from llm_processor.model_downloader import ModelDownloader
from llm_processor.model_registry import (
    MODEL_REGISTRY,
    DEFAULT_COMPARISON_MODELS,
    get_recommended_model
)


def main():
    parser = argparse.ArgumentParser(
        description="Download LLM models for skill extraction"
    )
    parser.add_argument(
        "models",
        nargs="*",
        help="Model names to download (default: comparison models)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all available models"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if model exists"
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        help="Directory to store models (default: from settings)"
    )

    args = parser.parse_args()

    downloader = ModelDownloader(models_dir=args.models_dir)

    # List models
    if args.list:
        print("\n=== Available Models ===\n")
        for name, config in MODEL_REGISTRY.items():
            downloaded = "✓" if downloader.is_model_downloaded(name) else " "
            print(f"[{downloaded}] {name}")
            print(f"    {config.display_name}")
            print(f"    Size: {config.size_gb} GB | Quantization: {config.quantization}")
            print(f"    {config.description}\n")

        print("\nRecommended models:")
        print(f"  - Fastest: {get_recommended_model('fastest')}")
        print(f"  - Best quality: {get_recommended_model('best_quality')}")
        print(f"  - Best balance: {get_recommended_model('best_balance')}")
        return

    # Determine which models to download
    if args.all:
        models_to_download = list(MODEL_REGISTRY.keys())
    elif args.models:
        models_to_download = args.models
    else:
        models_to_download = DEFAULT_COMPARISON_MODELS

    print(f"\nDownloading {len(models_to_download)} models...")
    print(f"Models: {', '.join(models_to_download)}\n")

    # Download each model
    for model_name in models_to_download:
        try:
            print(f"{'='*60}")
            downloader.download_model(model_name, force=args.force)
            print()
        except Exception as e:
            print(f"❌ Failed to download {model_name}: {e}\n")

    # Summary
    print("\n=== Download Summary ===")
    downloaded = downloader.list_downloaded_models()
    print(f"Total models downloaded: {len(downloaded)}")
    for model in downloaded:
        info = downloader.get_model_info(model)
        print(f"  ✓ {model} ({info['actual_size_gb']} GB)")


if __name__ == "__main__":
    main()
