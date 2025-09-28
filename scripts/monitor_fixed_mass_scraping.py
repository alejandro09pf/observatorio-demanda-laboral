#!/usr/bin/env python3
"""
Monitor the fixed mass scraping progress in real-time
"""

import time
import subprocess
import json
from datetime import datetime
from pathlib import Path

def get_database_stats():
    """Get current database statistics."""
    try:
        result = subprocess.run([
            "docker", "exec", "observatorio-demanda-laboral-postgres-1",
            "psql", "-U", "labor_user", "-d", "labor_observatory",
            "-c", "SELECT portal, COUNT(*) as count FROM raw_jobs GROUP BY portal ORDER BY count DESC;"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            # Parse the table output
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
        print(f"Error getting database stats: {e}")
    return {}

def get_total_jobs():
    """Get total job count."""
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
        print(f"Error getting total jobs: {e}")
    return 0

def main():
    """Monitor mass scraping progress."""
    print("🚀 Monitoring Fixed Mass Scraping Progress")
    print("=" * 60)
    print("✅ Duplicate filtering: DISABLED")
    print("✅ Proxies: DISABLED") 
    print("✅ Mass scraping pipeline: ACTIVE")
    print("✅ Optimized settings: APPLIED")
    print("=" * 60)
    
    start_time = datetime.now()
    last_total = 0
    
    while True:
        try:
            current_time = datetime.now()
            elapsed = current_time - start_time
            
            # Get current stats
            stats = get_database_stats()
            total = get_total_jobs()
            
            # Calculate new jobs
            new_jobs = total - last_total
            last_total = total
            
            # Display progress
            print(f"\n⏰ {current_time.strftime('%H:%M:%S')} | Elapsed: {elapsed}")
            print(f"📈 Total jobs: {total} (+{new_jobs})")
            print(f"🎯 Progress to 200k: {total}/200,000 ({total/200000*100:.1f}%)")
            
            if stats:
                print("📋 By portal:")
                for portal, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {portal}: {count}")
            
            print("-" * 60)
            
            # Check if we've reached the target
            if total >= 200000:
                print("🎉 TARGET REACHED! 200,000+ jobs collected!")
                break
                
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
