#!/usr/bin/env python3
"""
Simple test script to verify the scraper module works correctly.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    
    try:
        from src.scraper.items import JobItem
        print("✅ JobItem imported successfully")
    except Exception as e:
        print(f"❌ Failed to import JobItem: {e}")
        return False
    
    try:
        from src.scraper.pipelines import JobPostgresPipeline
        print("✅ JobPostgresPipeline imported successfully")
    except Exception as e:
        print(f"❌ Failed to import JobPostgresPipeline: {e}")
        return False
    
    try:
        from src.scraper.middlewares import UserAgentRotationMiddleware, ProxyRotationMiddleware, RetryWithBackoffMiddleware
        print("✅ Middlewares imported successfully")
    except Exception as e:
        print(f"❌ Failed to import middlewares: {e}")
        return False
    
    try:
        from src.scraper.spiders.base_spider import BaseSpider
        print("✅ BaseSpider imported successfully")
    except Exception as e:
        print(f"❌ Failed to import BaseSpider: {e}")
        return False
    
    try:
        from src.scraper.spiders.infojobs_spider import InfoJobsSpider
        print("✅ InfoJobsSpider imported successfully")
    except Exception as e:
        print(f"❌ Failed to import InfoJobsSpider: {e}")
        return False
    
    try:
        from src.scraper.spiders.elempleo_spider import ElempleoSpider
        print("✅ ElempleoSpider imported successfully")
    except Exception as e:
        print(f"❌ Failed to import ElempleoSpider: {e}")
        return False
    
    try:
        from src.scraper.spiders.bumeran_spider import BumeranSpider
        print("✅ BumeranSpider imported successfully")
    except Exception as e:
        print(f"❌ Failed to import BumeranSpider: {e}")
        return False
    
    try:
        from src.orchestrator import app
        print("✅ Orchestrator imported successfully")
    except Exception as e:
        print(f"❌ Failed to import orchestrator: {e}")
        return False
    
    return True


def test_job_item():
    """Test JobItem creation and validation."""
    print("\nTesting JobItem...")
    
    try:
        from src.scraper.items import JobItem
        
        item = JobItem()
        item['portal'] = 'test'
        item['country'] = 'CO'
        item['url'] = 'https://example.com/job1'
        item['title'] = 'Software Engineer'
        item['description'] = 'We are looking for a software engineer'
        
        print("✅ JobItem created successfully")
        print(f"   Portal: {item['portal']}")
        print(f"   Country: {item['country']}")
        print(f"   Title: {item['title']}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to create JobItem: {e}")
        return False


def test_middlewares():
    """Test middleware functionality."""
    print("\nTesting middlewares...")
    
    try:
        from src.scraper.middlewares import UserAgentRotationMiddleware, ProxyRotationMiddleware
        from unittest.mock import MagicMock
        
        # Test UserAgentRotationMiddleware
        ua_middleware = UserAgentRotationMiddleware()
        assert len(ua_middleware.user_agents) > 0
        print("✅ UserAgentRotationMiddleware created successfully")
        
        # Test ProxyRotationMiddleware
        proxy_middleware = ProxyRotationMiddleware()
        print("✅ ProxyRotationMiddleware created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test middlewares: {e}")
        return False


def test_spiders():
    """Test spider creation."""
    print("\nTesting spiders...")
    
    try:
        from src.scraper.spiders.infojobs_spider import InfoJobsSpider
        from src.scraper.spiders.elempleo_spider import ElempleoSpider
        from src.scraper.spiders.bumeran_spider import BumeranSpider
        
        # Test spider creation
        infojobs = InfoJobsSpider(country='CO')
        assert infojobs.name == 'infojobs'
        assert infojobs.country == 'CO'
        print("✅ InfoJobsSpider created successfully")
        
        elempleo = ElempleoSpider(country='CO')
        assert elempleo.name == 'elempleo'
        assert elempleo.country == 'CO'
        print("✅ ElempleoSpider created successfully")
        
        bumeran = BumeranSpider(country='CO')
        assert bumeran.name == 'bumeran'
        assert bumeran.country == 'CO'
        print("✅ BumeranSpider created successfully")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test spiders: {e}")
        return False


def test_orchestrator():
    """Test orchestrator functionality."""
    print("\nTesting orchestrator...")
    
    try:
        from src.orchestrator import AVAILABLE_SPIDERS, SUPPORTED_COUNTRIES
        
        assert 'infojobs' in AVAILABLE_SPIDERS
        assert 'elempleo' in AVAILABLE_SPIDERS
        assert 'bumeran' in AVAILABLE_SPIDERS
        assert 'CO' in SUPPORTED_COUNTRIES
        assert 'MX' in SUPPORTED_COUNTRIES
        assert 'AR' in SUPPORTED_COUNTRIES
        
        print("✅ Orchestrator configuration is correct")
        print(f"   Available spiders: {AVAILABLE_SPIDERS}")
        print(f"   Supported countries: {SUPPORTED_COUNTRIES}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to test orchestrator: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("SCRAPER MODULE TEST")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_job_item,
        test_middlewares,
        test_spiders,
        test_orchestrator
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All tests passed! The scraper module is ready to use.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
