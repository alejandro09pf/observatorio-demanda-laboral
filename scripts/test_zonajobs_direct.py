#!/usr/bin/env python3
"""
Direct test of ZonaJobs spider to see detailed logs.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for orchestrator execution
os.environ['ORCHESTRATOR_EXECUTION'] = 'true'

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_zonajobs_spider():
    """Test ZonaJobs spider directly."""
    try:
        from src.scraper.spiders.zonajobs_spider import ZonaJobsSpider
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        
        logger.info("🔧 Testing ZonaJobs spider directly...")
        
        # Create crawler process
        process = CrawlerProcess(get_project_settings())
        
        # Add spider class to process
        process.crawl(ZonaJobsSpider)
        
        # Start crawling
        process.start()
        
        logger.info("✅ Spider test completed")
        
    except Exception as e:
        logger.error(f"❌ Spider test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_zonajobs_spider()
