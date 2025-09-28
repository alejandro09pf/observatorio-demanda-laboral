#!/usr/bin/env python3
"""
Simple mass scraping script to collect 200k+ job ads
"""

import subprocess
import time
import sys
from pathlib import Path

def run_spider(spider_name, country="CO", limit=10000, max_pages=100):
    """Run a spider with high limits."""
    print(f"🚀 Starting {spider_name} with limit {limit}, max_pages {max_pages}")
    
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", spider_name,
        "-a", f"country={country}",
        "-a", f"limit={limit}",
        "-a", f"max_pages={max_pages}",
        "-L", "INFO"
    ]
    
    try:
        result = subprocess.run(cmd, timeout=3600)  # 1 hour timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏰ {spider_name} timed out")
        return False
    except Exception as e:
        print(f"❌ {spider_name} failed: {e}")
        return False

def main():
    """Run multiple scraping sessions to collect 200k+ jobs."""
    print("🚀 MASS SCRAPING - TARGET: 200,000+ JOBS")
    print("=" * 60)
    
    # Run multiple sessions of the best working scrapers
    sessions = [
        # Magneto - works well, fast
        ("magneto", 50000, 500),
        ("magneto", 50000, 500),
        ("magneto", 50000, 500),
        ("magneto", 50000, 500),
        
        # Bumeran - good volume
        ("bumeran", 30000, 300),
        ("bumeran", 30000, 300),
        
        # Indeed - working
        ("indeed", 20000, 200),
        ("indeed", 20000, 200),
        ("indeed", 20000, 200),
        
        # Computrabajo - high volume potential
        ("computrabajo", 30000, 300),
        ("computrabajo", 30000, 300),
    ]
    
    successful_sessions = 0
    total_sessions = len(sessions)
    
    for i, (spider, limit, max_pages) in enumerate(sessions, 1):
        print(f"\n📊 Session {i}/{total_sessions}: {spider}")
        print(f"   Limit: {limit:,} jobs, Max pages: {max_pages}")
        
        success = run_spider(spider, "CO", limit, max_pages)
        if success:
            successful_sessions += 1
            print(f"✅ Session {i} completed successfully")
        else:
            print(f"❌ Session {i} failed")
        
        # Small delay between sessions
        time.sleep(10)
    
    print(f"\n🏁 MASS SCRAPING COMPLETED")
    print(f"📊 Successful sessions: {successful_sessions}/{total_sessions}")
    
    return successful_sessions > 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
