#!/usr/bin/env python3
"""
Test script for Computrabajo spider with real data scraping.
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from src.scraper.spiders.computrabajo_spider import ComputrabajoSpider

def main():
    """Run the Computrabajo spider with real data scraping."""
    
    # Configure settings for standalone execution
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            'outputs/computrabajo_real.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'overwrite': True,
            }
        },
        'LOG_LEVEL': 'INFO',
        'DOWNLOAD_DELAY': 1.5,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        'DOWNLOAD_TIMEOUT': 60,
        'ROBOTSTXT_OBEY': True,
        # Disable database pipeline for standalone testing
        'ITEM_PIPELINES': {},
    })
    
    # Create crawler process
    process = CrawlerProcess(settings)
    
    # Add the spider with country and optional keyword/city parameters
    process.crawl(ComputrabajoSpider, country='CO', keyword='sistemas', city='bogota-dc')
    
    # Start the crawling process
    process.start()
    
    print("Computrabajo spider execution completed!")

if __name__ == "__main__":
    main()
