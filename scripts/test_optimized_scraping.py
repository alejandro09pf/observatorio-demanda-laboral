#!/usr/bin/env python3
"""
Test script to verify the optimized mass scraping fixes
"""

import subprocess
import sys
import time
from pathlib import Path

def test_single_spider(spider_name, limit=100, max_pages=10):
    """Test a single spider with optimized settings."""
    print(f"🧪 Testing {spider_name} with optimized settings...")
    print(f"   Limit: {limit}, Max pages: {max_pages}")
    
    cmd = [
        sys.executable, "-m", "src.orchestrator", "run-once", spider_name,
        "--country", "CO",
        "--limit", str(limit),
        "--max-pages", str(max_pages),
        "--verbose"
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(cmd, timeout=300, capture_output=True, text=True)
        elapsed = time.time() - start_time
        
        print(f"✅ {spider_name} completed in {elapsed:.1f}s")
        print(f"   Return code: {result.returncode}")
        
        # Check for duplicate filter issues
        if "dupefilter/filtered" in result.stdout:
            print("⚠️  Duplicate filter still active!")
        else:
            print("✅ Duplicate filter disabled")
            
        # Check for proxy issues
        if "403" in result.stdout and "proxy" in result.stdout.lower():
            print("⚠️  Proxy issues detected!")
        else:
            print("✅ No proxy issues")
            
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print(f"⏰ {spider_name} timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"❌ {spider_name} failed: {e}")
        return False

def main():
    """Test the optimized scraping fixes."""
    print("🚀 Testing Optimized Mass Scraping Fixes")
    print("=" * 50)
    
    # Test with a fast spider first
    test_spiders = [
        ("magneto", 50, 5),
        ("indeed", 50, 5),
    ]
    
    results = {}
    for spider, limit, max_pages in test_spiders:
        results[spider] = test_single_spider(spider, limit, max_pages)
        print()
    
    print("📊 Test Results Summary:")
    print("=" * 30)
    for spider, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {spider}: {status}")
    
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Ready for mass scraping.")
    else:
        print("\n⚠️  Some tests failed. Check the issues above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
