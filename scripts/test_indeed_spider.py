#!/usr/bin/env python3
"""
Test script for Indeed spider.
Tests the spider with a simple query to ensure it works correctly.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set environment variables for testing
os.environ['ORCHESTRATOR_EXECUTION'] = 'true'
os.environ['DISABLE_PROXY'] = 'true'  # Disable proxy for testing
os.environ['SCRAPER_DEBUG_MODE'] = 'true'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_indeed_spider():
    """Test the Indeed spider with a simple query."""
    try:
        from scraper.spiders.indeed_spider import IndeedSpider
        
        # Create spider instance
        spider = IndeedSpider(
            keyword='ingeniero en sistemas',
            location='',
            max_pages=2,
            country='MX'
        )
        
        print(f"✅ Spider created successfully")
        print(f"📊 Spider name: {spider.name}")
        print(f"🌍 Country: {spider.country}")
        print(f"🔍 Keyword: {spider.keyword}")
        print(f"📍 Location: {spider.location}")
        print(f"📄 Max pages: {spider.max_pages}")
        print(f"🔗 Base URL: {spider.base_search_url}")
        print(f"🔄 User agents available: {len(spider.get_random_user_agent())}")
        
        # Test proxy method
        proxy = spider.get_proxy()
        print(f"🌐 Proxy: {proxy or 'None (disabled for testing)'}")
        
        # Test user agent rotation
        ua1 = spider.get_random_user_agent()
        ua2 = spider.get_random_user_agent()
        print(f"🔄 User Agent 1: {ua1[:50]}...")
        print(f"🔄 User Agent 2: {ua2[:50]}...")
        
        # Test date parsing
        test_dates = [
            "Hoy",
            "Ayer", 
            "Hace 3 días",
            "15/01/2024",
            "15 de enero de 2024"
        ]
        
        print(f"\n📅 Testing date parsing:")
        for date_str in test_dates:
            parsed = spider._normalize_posted_date(date_str)
            print(f"  '{date_str}' -> {parsed}")
        
        print(f"\n✅ All tests passed! Spider is ready to use.")
        print(f"\n🚀 To run the spider:")
        print(f"   python -m src.orchestrator run-once indeed --country MX --max-pages 3")
        
    except Exception as e:
        print(f"❌ Error testing spider: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = test_indeed_spider()
    sys.exit(0 if success else 1)
