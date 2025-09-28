#!/usr/bin/env python3
"""
Mass Scraping Runner for Labor Market Observatory
Designed to efficiently collect 200k+ job ads from all available scrapers
"""

import os
import sys
import subprocess
import time
import threading
import queue
from datetime import datetime
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def get_database_stats():
    """Get current database statistics."""
    try:
        result = subprocess.run([
            "docker", "exec", "observatorio-demanda-laboral-postgres-1",
            "psql", "-U", "labor_user", "-d", "labor_observatory",
            "-c", "SELECT COUNT(*) as total FROM raw_jobs;"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                if line.strip().isdigit():
                    return int(line.strip())
        return 0
    except Exception as e:
        print(f"Error getting database stats: {e}")
        return 0

def get_portal_stats():
    """Get job count by portal."""
    try:
        result = subprocess.run([
            "docker", "exec", "observatorio-demanda-laboral-postgres-1",
            "psql", "-U", "labor_user", "-d", "labor_observatory",
            "-c", "SELECT portal, COUNT(*) as count FROM raw_jobs GROUP BY portal ORDER BY count DESC;"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            stats = {}
            for line in lines:
                if '|' in line and not line.startswith('-') and not line.startswith('portal'):
                    parts = line.split('|')
                    if len(parts) >= 2:
                        portal = parts[0].strip()
                        count = parts[1].strip()
                        if portal and count.isdigit():
                            stats[portal] = int(count)
            return stats
        return {}
    except Exception as e:
        print(f"Error getting portal stats: {e}")
        return {}

def run_spider(spider_name, country="CO", limit=50000, max_pages=500):
    """Run a spider with mass scraping settings."""
    print(f"🚀 Starting {spider_name} with limit {limit}, max_pages {max_pages}")
    
    cmd = [
        sys.executable, "-m", "src.orchestrator", "run-once", spider_name,
        "--country", country,
        "--limit", str(limit),
        "--max-pages", str(max_pages),
        "--verbose"
    ]
    
    try:
        # Run with mass scraping settings
        env = os.environ.copy()
        env['SCRAPY_SETTINGS_MODULE'] = 'src.scraper.mass_scraping_settings'
        
        result = subprocess.run(cmd, env=env, timeout=7200)  # 2 hour timeout
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"⏰ {spider_name} timed out")
        return False
    except Exception as e:
        print(f"❌ {spider_name} failed: {e}")
        return False

def monitor_progress(target_jobs=200000, check_interval=60):
    """Monitor scraping progress."""
    start_time = datetime.now()
    start_count = get_database_stats()
    
    print(f"📊 Starting monitoring - Target: {target_jobs:,} jobs")
    print(f"📈 Initial count: {start_count:,} jobs")
    
    while True:
        current_count = get_database_stats()
        portal_stats = get_portal_stats()
        elapsed = datetime.now() - start_time
        
        new_jobs = current_count - start_count
        progress = (current_count / target_jobs) * 100
        
        print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} | Elapsed: {elapsed}")
        print(f"📈 Total jobs: {current_count:,} (+{new_jobs:,})")
        print(f"🎯 Progress: {progress:.1f}% of {target_jobs:,} target")
        
        if portal_stats:
            print("📋 By portal:")
            for portal, count in list(portal_stats.items())[:5]:  # Top 5
                print(f"   {portal}: {count:,}")
        
        print("-" * 80)
        
        if current_count >= target_jobs:
            print(f"🎉 TARGET REACHED! Collected {current_count:,} jobs")
            break
            
        time.sleep(check_interval)

def run_all_scrapers_mass():
    """Run all scrapers simultaneously for mass data collection."""
    print("🚀 MASS SCRAPING ORCHESTRATOR")
    print("=" * 80)
    print("Target: 200,000+ job ads")
    print("Strategy: Run all scrapers simultaneously with optimized settings")
    print("=" * 80)
    
    # Available scrapers
    scrapers = [
        "bumeran",
        "computrabajo", 
        "elempleo",
        "hiring_cafe",
        "indeed",
        "magneto",
        "occmundial",
        "zonajobs"
    ]
    
    # Start monitoring in background
    monitor_thread = threading.Thread(
        target=monitor_progress, 
        args=(200000, 60),
        daemon=True
    )
    monitor_thread.start()
    
    # Start all scrapers
    threads = []
    for spider in scrapers:
        thread = threading.Thread(
            target=run_spider,
            args=(spider, "CO", 50000, 500),
            daemon=True
        )
        thread.start()
        threads.append(thread)
        time.sleep(5)  # Stagger starts by 5 seconds
    
    # Wait for all spiders to complete
    print("⏳ Waiting for all spiders to complete...")
    for thread in threads:
        thread.join()
    
    # Final statistics
    final_count = get_database_stats()
    final_stats = get_portal_stats()
    
    print("\n" + "=" * 80)
    print("🎉 MASS SCRAPING COMPLETED!")
    print("=" * 80)
    print(f"📊 Final job count: {final_count:,}")
    print(f"📋 By portal:")
    for portal, count in final_stats.items():
        print(f"   {portal}: {count:,}")
    print("=" * 80)

if __name__ == "__main__":
    run_all_scrapers_mass()
