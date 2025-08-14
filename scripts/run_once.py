#!/usr/bin/env python3
"""
Stateless execution script for running spiders once.
Suitable for cron or Windows Task Scheduler integration.
"""

import argparse
import logging
import sys
from pathlib import Path
import subprocess
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import get_settings
from config.logging_config import setup_logging

# Setup logging
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

# Available spiders
AVAILABLE_SPIDERS = ['infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo']
SUPPORTED_COUNTRIES = ['CO', 'MX', 'AR']


def validate_spiders(spiders: list) -> list:
    """Validate spider names."""
    invalid_spiders = [s for s in spiders if s not in AVAILABLE_SPIDERS]
    if invalid_spiders:
        raise ValueError(f"Invalid spiders: {invalid_spiders}. Available: {AVAILABLE_SPIDERS}")
    return spiders


def validate_country(country: str) -> str:
    """Validate country code."""
    if country not in SUPPORTED_COUNTRIES:
        raise ValueError(f"Invalid country: {country}. Supported: {SUPPORTED_COUNTRIES}")
    return country


def run_spider(spider: str, country: str, limit: int = 100, max_pages: int = 5) -> dict:
    """Run a single spider and return results."""
    logger.info(f"Running spider: {spider} for {country}")
    
    try:
        # Build scrapy command
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "-a", f"country={country}",
            "-a", f"max_pages={max_pages}",
            "-s", f"CLOSESPIDER_ITEMCOUNT={limit}",
            "-L", "INFO"
        ]
        
        # Change to project directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Run scrapy command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        # Parse output to get item count
        items_scraped = 0
        for line in result.stdout.split('\n'):
            if 'Inserted new job:' in line:
                items_scraped += 1
        
        return {
            "spider": spider,
            "country": country,
            "items_scraped": items_scraped,
            "return_code": result.returncode,
            "success": result.returncode == 0,
            "error": result.stderr if result.returncode != 0 else None
        }
        
    except subprocess.TimeoutExpired:
        error_msg = f"Spider {spider} timed out after 1 hour"
        logger.error(error_msg)
        return {
            "spider": spider,
            "country": country,
            "items_scraped": 0,
            "return_code": -1,
            "success": False,
            "error": error_msg
        }
    except Exception as e:
        error_msg = f"Error running spider {spider}: {e}"
        logger.error(error_msg)
        return {
            "spider": spider,
            "country": country,
            "items_scraped": 0,
            "return_code": -1,
            "success": False,
            "error": error_msg
        }


def main():
    parser = argparse.ArgumentParser(description="Run spiders once (stateless execution)")
    parser.add_argument("--spiders", "-s", required=True,
                       help="Comma-separated list of spiders to run")
    parser.add_argument("--country", "-c", default="CO",
                       help="Country code (CO, MX, AR)")
    parser.add_argument("--limit", "-l", type=int, default=100,
                       help="Maximum number of jobs per spider")
    parser.add_argument("--max-pages", "-p", type=int, default=5,
                       help="Maximum pages to scrape per spider")
    parser.add_argument("--output", "-o",
                       help="Output file for results (JSON format)")
    
    args = parser.parse_args()
    
    # Validate inputs
    try:
        spider_list = [s.strip() for s in args.spiders.split(",")]
        spider_list = validate_spiders(spider_list)
        country = validate_country(args.country)
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    
    logger.info(f"Starting stateless execution for spiders: {spider_list} in {country}")
    
    # Run spiders
    results = []
    for spider in spider_list:
        result = run_spider(spider, country, args.limit, args.max_pages)
        results.append(result)
        
        # Log result
        if result["success"]:
            logger.info(f"✅ {spider}: {result['items_scraped']} items scraped")
        else:
            logger.error(f"❌ {spider}: {result['error']}")
    
    # Print summary
    print("\n" + "="*50)
    print("EXECUTION SUMMARY")
    print("="*50)
    total_items = 0
    successful_spiders = 0
    
    for result in results:
        if result["success"]:
            print(f"✅ {result['spider']}: {result['items_scraped']} items")
            total_items += result['items_scraped']
            successful_spiders += 1
        else:
            print(f"❌ {result['spider']}: {result['error']}")
    
    print(f"\nTotal: {successful_spiders}/{len(results)} spiders successful")
    print(f"Total items scraped: {total_items}")
    
    # Save results to file if requested
    if args.output:
        try:
            import json
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
            logger.info(f"Results saved to {args.output}")
        except Exception as e:
            logger.error(f"Failed to save results to {args.output}: {e}")
    
    # Exit with error code if any spider failed
    if successful_spiders < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
