#!/usr/bin/env python3
"""
Monitor scraping progress and database insertions in real-time.
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

def monitor_progress():
    """Monitor scraping progress."""
    print("🚀 Starting scraping progress monitor...")
    print("=" * 80)
    
    start_time = datetime.now()
    initial_total = get_total_jobs()
    initial_stats = get_database_stats()
    
    print(f"📊 Initial state:")
    print(f"   Total jobs: {initial_total}")
    print(f"   By portal: {initial_stats}")
    print()
    
    last_total = initial_total
    last_stats = initial_stats.copy()
    
    while True:
        try:
            current_total = get_total_jobs()
            current_stats = get_database_stats()
            
            # Calculate changes
            total_change = current_total - last_total
            stats_changes = {}
            for portal in current_stats:
                old_count = last_stats.get(portal, 0)
                new_count = current_stats[portal]
                change = new_count - old_count
                if change > 0:
                    stats_changes[portal] = change
            
            # Display progress
            elapsed = datetime.now() - start_time
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')} | Elapsed: {elapsed}")
            print(f"📈 Total jobs: {current_total} (+{total_change})")
            
            if stats_changes:
                print("📊 New jobs by portal:")
                for portal, change in stats_changes.items():
                    print(f"   {portal}: +{change} (total: {current_stats[portal]})")
            else:
                print("📊 No new jobs in this check")
            
            print(f"🎯 Progress to 100k: {current_total:,}/100,000 ({current_total/1000:.1f}%)")
            print("-" * 80)
            
            # Update for next iteration
            last_total = current_total
            last_stats = current_stats.copy()
            
            # Check if we've reached the target
            if current_total >= 100000:
                print("🎉 TARGET REACHED! 100,000+ jobs collected!")
                break
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
            
        except KeyboardInterrupt:
            print("\n⏹️ Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error during monitoring: {e}")
            time.sleep(10)

if __name__ == "__main__":
    monitor_progress()
