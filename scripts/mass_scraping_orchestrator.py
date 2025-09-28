#!/usr/bin/env python3
"""
Mass Scraping Orchestrator for Labor Market Observatory
Designed to collect 200k+ job ads from all available scrapers
"""

import os
import sys
import subprocess
import time
import json
from datetime import datetime
from pathlib import Path
import threading
import queue

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
    except Exception as e:
        print(f"Error getting database stats: {e}")
    return 0

def get_portal_stats():
    """Get statistics by portal."""
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
    except Exception as e:
        print(f"Error getting portal stats: {e}")
    return {}

def run_spider_mass(spider_name, country="CO", limit=50000, max_pages=200):
    """Run a single spider with mass scraping settings."""
    print(f"🚀 Starting mass scraping for {spider_name}...")
    
    # Build scrapy command with mass scraping settings
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", spider_name,
        "-a", f"country={country}",
        "-a", f"limit={limit}",
        "-a", f"max_pages={max_pages}",
        "-s", "SETTINGS_MODULE=src.scraper.mass_scraping_settings",
        "-L", "INFO"
    ]
    
    # Change to project root directory
    os.chdir(project_root)
    
    # Set environment variables
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    env["ORCHESTRATOR_EXECUTION"] = "1"
    env["SCRAPY_ORCHESTRATOR_RUN"] = "1"
    env["ORCHESTRATOR_MODE"] = "1"
    env["MASS_SCRAPING_MODE"] = "1"
    
    try:
        # Run the spider
        result = subprocess.run(
            cmd,
            env=env,
            cwd=project_root,
            timeout=7200,  # 2 hour timeout
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {spider_name} completed successfully")
            return {"success": True, "output": result.stdout, "error": result.stderr}
        else:
            print(f"❌ {spider_name} failed with return code: {result.returncode}")
            return {"success": False, "output": result.stdout, "error": result.stderr}
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {spider_name} timed out after 2 hours")
        return {"success": False, "error": "Timeout after 2 hours"}
    except Exception as e:
        print(f"❌ {spider_name} failed with exception: {e}")
        return {"success": False, "error": str(e)}

def run_spider_thread(spider_name, results_queue, country="CO", limit=50000, max_pages=200):
    """Run spider in a separate thread."""
    result = run_spider_mass(spider_name, country, limit, max_pages)
    results_queue.put((spider_name, result))

def monitor_progress():
    """Monitor scraping progress in real-time."""
    print("📊 Starting progress monitor...")
    start_time = datetime.now()
    initial_count = get_database_stats()
    
    print(f"📈 Initial job count: {initial_count:,}")
    print(f"🎯 Target: 200,000+ jobs")
    print("=" * 80)
    
    while True:
        try:
            current_count = get_database_stats()
            portal_stats = get_portal_stats()
            
            elapsed = datetime.now() - start_time
            new_jobs = current_count - initial_count
            
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Elapsed: {elapsed}")
            print(f"📊 Total jobs: {current_count:,} (+{new_jobs:,})")
            print(f"🎯 Progress: {current_count/2000:.1f}% of 200k target")
            
            if portal_stats:
                print("📋 By portal:")
                for portal, count in portal_stats.items():
                    print(f"   {portal}: {count:,}")
            
            print("-" * 80)
            
            if current_count >= 200000:
                print("🎉 TARGET REACHED! 200,000+ jobs collected!")
                break
                
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            print("\n⏹️ Monitoring stopped")
            break
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(30)

def main():
    """Main mass scraping function."""
    print("🚀 MASS SCRAPING ORCHESTRATOR")
    print("=" * 80)
    print("Target: 200,000+ job ads")
    print("Strategy: Run all scrapers simultaneously with optimized settings")
    print("=" * 80)
    
    # Available scrapers
    scrapers = [
        "magneto",      # Fast, works well
        "bumeran",      # Good volume, needs Chrome
        "computrabajo", # High volume potential
        "elempleo",     # Additional source
        "indeed",       # International jobs
        "zonajobs",     # Additional source
        "occmundial"    # Additional source
    ]
    
    # Start monitoring in background
    monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
    monitor_thread.start()
    
    # Results queue for thread communication
    results_queue = queue.Queue()
    
    # Start all spiders in parallel
    spider_threads = []
    for spider in scrapers:
        thread = threading.Thread(
            target=run_spider_thread,
            args=(spider, results_queue, "CO", 50000, 200),
            daemon=True
        )
        thread.start()
        spider_threads.append(thread)
        print(f"🔄 Started {spider} spider")
        time.sleep(5)  # Stagger starts
    
    # Wait for all spiders to complete
    print("\n⏳ Waiting for all spiders to complete...")
    for thread in spider_threads:
        thread.join()
    
    # Collect results
    results = {}
    while not results_queue.empty():
        spider_name, result = results_queue.get()
        results[spider_name] = result
    
    # Final statistics
    final_count = get_database_stats()
    final_portal_stats = get_portal_stats()
    
    print("\n" + "=" * 80)
    print("🏁 MASS SCRAPING COMPLETED")
    print("=" * 80)
    print(f"📊 Final job count: {final_count:,}")
    print(f"🎯 Target achieved: {'✅ YES' if final_count >= 200000 else '❌ NO'}")
    
    print("\n📋 Results by spider:")
    for spider, result in results.items():
        status = "✅ SUCCESS" if result["success"] else "❌ FAILED"
        print(f"   {spider}: {status}")
        if not result["success"] and "error" in result:
            print(f"      Error: {result['error']}")
    
    print("\n📊 Final statistics by portal:")
    for portal, count in final_portal_stats.items():
        print(f"   {portal}: {count:,}")
    
    # Save results to file
    results_file = project_root / "mass_scraping_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "final_count": final_count,
            "target_achieved": final_count >= 200000,
            "portal_stats": final_portal_stats,
            "spider_results": results
        }, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    return final_count >= 200000

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
