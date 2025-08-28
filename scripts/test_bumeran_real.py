#!/usr/bin/env python3
"""
Test script for the production-ready Bumeran spider.
"""

import sys
import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Import the spider
from src.scraper.spiders.bumeran_spider import BumeranSpider

def main():
    """Run the Bumeran spider test."""
    print("=== Testing Bumeran Spider (Production) ===")
    
    # Get Scrapy settings
    settings = get_project_settings()
    
    # Update settings for standalone testing
    settings.update({
        'FEEDS': {
            'outputs/bumeran_real.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            }
        },
        'ITEM_PIPELINES': {},  # Disable database pipeline for testing
        'LOG_LEVEL': 'INFO',
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add the spider to the process
    process.crawl(BumeranSpider, country='MX', max_pages=3)
    
    print("Starting Bumeran spider...")
    print("Country: MX")
    print("Max pages: 3")
    print("Output: outputs/bumeran_real.json")
    
    # Start the crawling process
    process.start()
    
    print("\n=== Test Complete ===")
    print("Check outputs/bumeran_real.json for results")

if __name__ == "__main__":
    main()
