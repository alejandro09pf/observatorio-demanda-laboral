#!/usr/bin/env python3
"""
Monitor progress of parallel workers in real-time.
Shows aggregate stats across all workers.
"""

import sys
import os
from pathlib import Path
import time
import re
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import psycopg2
from config.settings import get_settings

def get_db_stats():
    """Get current extraction stats from database."""
    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    try:
        with psycopg2.connect(db_url) as conn:
            cursor = conn.cursor()

            # Get status counts
            cursor.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE extraction_status = 'completed') as completed,
                    COUNT(*) FILTER (WHERE extraction_status = 'processing') as processing,
                    COUNT(*) FILTER (WHERE extraction_status = 'pending') as pending,
                    COUNT(*) FILTER (WHERE extraction_status = 'failed') as failed,
                    COUNT(*) as total
                FROM raw_jobs
                WHERE is_usable = TRUE
            """)

            stats = cursor.fetchone()

            # Get skill counts
            cursor.execute("""
                SELECT
                    COUNT(*) as total_skills,
                    COUNT(*) FILTER (WHERE esco_uri IS NOT NULL) as esco_matches
                FROM extracted_skills
            """)

            skill_stats = cursor.fetchone()

            return {
                'completed': stats[0],
                'processing': stats[1],
                'pending': stats[2],
                'failed': stats[3],
                'total': stats[4],
                'total_skills': skill_stats[0] if skill_stats else 0,
                'esco_matches': skill_stats[1] if skill_stats else 0
            }

    except Exception as e:
        print(f"❌ Error getting DB stats: {e}")
        return None


def parse_worker_logs():
    """Parse worker log files to get per-worker stats."""
    worker_stats = {}

    for worker_id in range(11):  # 0-10
        log_file = f"/tmp/pipeline_worker_{worker_id}.log" if worker_id > 0 else "/tmp/pipeline_a_scale_30k.log"

        if not os.path.exists(log_file):
            continue

        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()

            # Find last progress line
            success_count = 0
            last_line = ""

            for line in reversed(lines):
                if f"Worker {worker_id + 1}:" in line or f"W{worker_id + 1}" in line:
                    # Extract job count
                    match = re.search(r'(\d+) jobs', line)
                    if match:
                        success_count = int(match.group(1))
                        last_line = line.strip()
                        break

                # Also check for "✅ Job" lines
                if "✅ Job" in line:
                    success_count += 1

            if success_count > 0 or last_line:
                worker_stats[worker_id] = {
                    'success': success_count,
                    'last_activity': last_line
                }

        except Exception as e:
            pass

    return worker_stats


def display_progress(db_stats, worker_stats, start_time):
    """Display formatted progress report."""
    os.system('clear')

    print("=" * 80)
    print("📊 PARALLEL PIPELINE A - LIVE PROGRESS MONITOR")
    print("=" * 80)
    print()

    # Database stats
    if db_stats:
        total = db_stats['total']
        completed = db_stats['completed']
        processing = db_stats['processing']
        pending = db_stats['pending']
        failed = db_stats['failed']

        progress_pct = (completed / total * 100) if total > 0 else 0

        print(f"🎯 OVERALL PROGRESS:")
        print(f"   Total jobs: {total:,}")
        print(f"   ✅ Completed: {completed:,} ({progress_pct:.2f}%)")
        print(f"   🔄 Processing: {processing:,}")
        print(f"   ⏳ Pending: {pending:,}")
        print(f"   ❌ Failed: {failed:,}")
        print()

        # Progress bar
        bar_length = 50
        filled = int(bar_length * progress_pct / 100)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"   [{bar}] {progress_pct:.1f}%")
        print()

        # Skills extracted
        print(f"📚 SKILLS EXTRACTED:")
        print(f"   Total: {db_stats['total_skills']:,}")
        print(f"   ESCO matches: {db_stats['esco_matches']:,}")
        if db_stats['total_skills'] > 0:
            esco_pct = db_stats['esco_matches'] / db_stats['total_skills'] * 100
            print(f"   ESCO coverage: {esco_pct:.1f}%")
            print(f"   Emergent skills: {db_stats['total_skills'] - db_stats['esco_matches']:,} ({100-esco_pct:.1f}%)")
        print()

        # Timing estimate
        elapsed = time.time() - start_time
        if completed > 0:
            avg_time = elapsed / completed
            remaining_jobs = total - completed
            eta_seconds = avg_time * remaining_jobs
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)

            print(f"⏱️  TIMING:")
            print(f"   Elapsed: {elapsed/60:.1f} min ({elapsed/3600:.2f} hours)")
            print(f"   Speed: {completed/(elapsed/60):.1f} jobs/min ({avg_time:.2f}s/job)")
            print(f"   ETA: {eta_seconds/60:.1f} min (~{eta_time.strftime('%H:%M')})")
            print()

    # Worker stats
    if worker_stats:
        print(f"👷 ACTIVE WORKERS ({len(worker_stats)} running):")
        for worker_id in sorted(worker_stats.keys()):
            stats = worker_stats[worker_id]
            print(f"   Worker {worker_id + 1:2d}: {stats['success']:4d} jobs")

        print()

    print("=" * 80)
    print("Press Ctrl+C to exit | Refreshing every 5 seconds...")
    print("=" * 80)


def main():
    """Monitor progress continuously."""
    print("🚀 Starting parallel progress monitor...")
    print("   Database stats will update every 5 seconds")
    print()

    start_time = time.time()

    try:
        while True:
            db_stats = get_db_stats()
            worker_stats = parse_worker_logs()

            display_progress(db_stats, worker_stats, start_time)

            # Check if complete
            if db_stats and db_stats['pending'] == 0 and db_stats['processing'] == 0:
                print()
                print("🎉 ALL JOBS COMPLETED!")
                break

            time.sleep(5)

    except KeyboardInterrupt:
        print()
        print("👋 Monitoring stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
