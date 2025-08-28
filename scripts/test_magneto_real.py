#!/usr/bin/env python3
"""
Test script for Magneto spider with real data.
"""

import sys
import os
from pathlib import Path
import json
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_magneto_spider():
    """Test the Magneto spider with real data."""
    
    # Import the spider
    from src.scraper.spiders.magneto_spider import MagnetoSpider
    
    # Configure settings for testing
    settings = get_project_settings()
    
    # Override settings for testing
    settings.update({
        'FEEDS': {
            'outputs/magneto_real.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            }
        },
        'ITEM_PIPELINES': {},  # Disable pipelines for testing
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'ROBOTSTXT_OBEY': False,
        'LOG_LEVEL': 'INFO',
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add the spider to the process
    process.crawl(
        MagnetoSpider,
        country='CO',
        max_pages=3  # Test with 3 pages
    )
    
    # Start the crawling process
    process.start()
    
    # Check results
    output_file = "outputs/magneto_real.json"
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n✓ Magneto spider completed successfully!")
        print(f"  Total jobs scraped: {len(data)}")
        
        if data:
            print(f"  Sample job: {data[0].get('title', 'No title')}")
            print(f"  Company: {data[0].get('company', 'No company')}")
            print(f"  Location: {data[0].get('location', 'No location')}")
            print(f"  Portal: {data[0].get('portal', 'No portal')}")
            print(f"  Country: {data[0].get('country', 'No country')}")
        
        print(f"  Results saved to: {output_file}")
    else:
        print("✗ No output file found. Spider may have failed.")

if __name__ == "__main__":
    print("Testing Magneto spider with real data...")
    test_magneto_spider()
    print("\nTest complete!")
