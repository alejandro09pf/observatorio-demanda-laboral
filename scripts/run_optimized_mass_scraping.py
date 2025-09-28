#!/usr/bin/env python3
"""
Optimized Mass Scraping Runner for Labor Market Observatory
All issues have been fixed for efficient 200k+ job collection
"""

import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path

def run_mass_scraping():
    """Run all scrapers with optimized settings."""
    print("🚀 Starting Optimized Mass Scraping")
    print("=" * 50)
    print("✅ Duplicate filtering: DISABLED")
    print("✅ Proxy issues: FIXED")
    print("✅ Scraper speed: OPTIMIZED")
    print("✅ Scraper logic: FIXED")
    print("=" * 50)
    
    # All scrapers to run
    scrapers = [
        "bumeran", "computrabajo", "elempleo", "hiring_cafe", 
        "indeed", "magneto", "occmundial", "zonajobs"
    ]
    
    # Optimized parameters for mass collection
    country = "CO"
    limit = 100000  # High limit per scraper
    max_pages = 1000  # High page limit
    
    print(f"🎯 Target: 200,000+ job ads")
    print(f"🌍 Country: {country}")
    print(f"📊 Limit per scraper: {limit:,}")
    print(f"📄 Max pages per scraper: {max_pages:,}")
    print()
    
    # Run the orchestrator with all scrapers
    cmd = [
        sys.executable, "-m", "src.orchestrator", "run",
        ",".join(scrapers),
        "--country", country,
        "--limit", str(limit),
        "--max-pages", str(max_pages),
        "--verbose"
    ]
    
    print("🚀 Starting mass scraping...")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    start_time = time.time()
    
    try:
        # Run the mass scraping
        result = subprocess.run(cmd)
        
        elapsed = time.time() - start_time
        print(f"\n⏱️  Total execution time: {elapsed/3600:.1f} hours")
        
        if result.returncode == 0:
            print("✅ Mass scraping completed successfully!")
        else:
            print("⚠️  Mass scraping completed with some issues")
            
        return result.returncode == 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Mass scraping stopped by user")
        return False
    except Exception as e:
        print(f"\n❌ Mass scraping failed: {e}")
        return False

def monitor_progress():
    """Monitor progress in a separate thread."""
    while True:
        try:
            # Get database stats
            result = subprocess.run([
                "docker", "exec", "observatorio-demanda-laboral-postgres-1",
                "psql", "-U", "labor_user", "-d", "labor_observatory",
                "-c", "SELECT COUNT(*) as total FROM raw_jobs;"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'total' in line and '|' in line:
                        total = line.split('|')[1].strip()
                        if total.isdigit():
                            print(f"📊 Current total: {int(total):,} jobs")
                            break
            
            time.sleep(60)  # Check every minute
            
        except Exception as e:
            print(f"⚠️  Monitoring error: {e}")
            time.sleep(60)

def main():
    """Main function."""
    print("🎯 Optimized Mass Scraping for Labor Market Observatory")
    print("=" * 60)
    print("All critical issues have been fixed:")
    print("  ✅ Duplicate filtering disabled")
    print("  ✅ Proxy issues resolved")
    print("  ✅ Scraper speed optimized")
    print("  ✅ Scraper logic improved")
    print("=" * 60)
    print()
    
    # Start monitoring in background
    monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
    monitor_thread.start()
    
    # Run mass scraping
    success = run_mass_scraping()
    
    # Final database check
    print("\n📊 Final Database Check:")
    try:
        result = subprocess.run([
            "docker", "exec", "observatorio-demanda-laboral-postgres-1",
            "psql", "-U", "labor_user", "-d", "labor_observatory",
            "-c", "SELECT portal, COUNT(*) as count FROM raw_jobs GROUP BY portal ORDER BY count DESC;"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("❌ Could not get final database stats")
    except Exception as e:
        print(f"❌ Error getting final stats: {e}")
    
    if success:
        print("\n🎉 Mass scraping completed successfully!")
        print("📊 Check the database for collected job ads")
    else:
        print("\n⚠️  Mass scraping had issues")
        print("📊 Check the logs for details")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
