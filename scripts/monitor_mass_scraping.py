#!/usr/bin/env python3
"""
Monitor mass scraping progress in real-time
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

def get_total_count():
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
        print(f"Error getting total count: {e}")
    return 0

def main():
    """Monitor scraping progress."""
    print("🚀 Mass Scraping Monitor Started")
    print("=" * 60)
    
    start_time = datetime.now()
    last_total = 0
    
    while True:
        try:
            current_time = datetime.now()
            elapsed = current_time - start_time
            
            # Get current stats
            portal_stats = get_database_stats()
            total_count = get_total_count()
            
            # Calculate rate
            if elapsed.total_seconds() > 0:
                rate = (total_count - last_total) / elapsed.total_seconds() * 60  # jobs per minute
            else:
                rate = 0
            
            # Display stats
            print(f"\n📊 [{current_time.strftime('%H:%M:%S')}] Progress Update")
            print(f"⏱️  Elapsed: {elapsed}")
            print(f"📈 Total Jobs: {total_count:,}")
            print(f"🚀 Rate: {rate:.1f} jobs/min")
            print(f"🎯 Target: 200,000 jobs")
            print(f"📊 Progress: {(total_count/200000)*100:.1f}%")
            
            if portal_stats:
                print("\n📋 By Portal:")
                for portal, count in portal_stats.items():
                    print(f"   {portal}: {count:,}")
            
            # Check if we've reached the target
            if total_count >= 200000:
                print(f"\n🎉 TARGET REACHED! {total_count:,} jobs collected!")
                break
            
            last_total = total_count
            time.sleep(30)  # Update every 30 seconds
            
        except KeyboardInterrupt:
            print("\n⏹️  Monitoring stopped by user")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
