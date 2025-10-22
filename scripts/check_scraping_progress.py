"""
Check scraping progress by analyzing log files.
"""
import os
import re
from pathlib import Path
from datetime import datetime

def parse_log_file(log_path):
    """Parse a log file to extract scraping statistics."""
    if not os.path.exists(log_path):
        return None

    stats = {
        "file": log_path,
        "file_size_kb": os.path.getsize(log_path) / 1024,
        "last_modified": datetime.fromtimestamp(os.path.getmtime(log_path)),
        "items_scraped": 0,
        "pages_processed": 0,
        "errors": 0,
        "status": "unknown"
    }

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

            # Count items scraped
            items_match = re.findall(r'item_scraped_count/(\d+)', content)
            if items_match:
                stats["items_scraped"] = int(items_match[-1])

            # Check for completion
            if "Spider closed" in content:
                stats["status"] = "completed"
            elif "Traceback" in content or "ERROR" in content:
                stats["status"] = "error"
                stats["errors"] = content.count("ERROR")
            elif stats["items_scraped"] > 0:
                stats["status"] = "running"
            else:
                stats["status"] = "started"

            # Count pages
            pages_match = re.findall(r'page (\d+)', content, re.IGNORECASE)
            if pages_match:
                stats["pages_processed"] = int(pages_match[-1])

    except Exception as e:
        stats["status"] = f"error reading: {e}"

    return stats

def main():
    logs_dir = Path("logs")

    if not logs_dir.exists():
        print("No logs directory found!")
        return

    print("\n" + "="*120)
    print("SCRAPING PROGRESS MONITOR")
    print("="*120 + "\n")

    log_files = list(logs_dir.glob("*_massive.log"))

    if not log_files:
        print("No massive scraping logs found in logs/ directory")
        return

    results = []
    for log_file in log_files:
        stats = parse_log_file(log_file)
        if stats:
            results.append(stats)

    # Sort by items scraped (descending)
    results.sort(key=lambda x: x["items_scraped"], reverse=True)

    # Print table
    print(f"{'Spider':<30} {'Status':<12} {'Items':<8} {'Pages':<8} {'Errors':<8} {'Size (KB)':<12} {'Last Modified':<20}")
    print("-" * 120)

    total_items = 0
    for stat in results:
        spider_name = Path(stat["file"]).stem.replace("_massive", "")
        total_items += stat["items_scraped"]

        last_mod = stat["last_modified"].strftime("%Y-%m-%d %H:%M")

        print(f"{spider_name:<30} {stat['status']:<12} {stat['items_scraped']:<8} "
              f"{stat['pages_processed']:<8} {stat['errors']:<8} {stat['file_size_kb']:<12.1f} {last_mod:<20}")

    print("-" * 120)
    print(f"{'TOTAL':<30} {'':<12} {total_items:<8}")
    print("="*120 + "\n")

    # Identify problematic scrapers
    print("\nPROBLEMATIC SCRAPERS (0 items or errors):")
    print("-" * 120)

    problematic = [s for s in results if s["items_scraped"] == 0 or s["status"] == "error"]

    if problematic:
        for stat in problematic:
            spider_name = Path(stat["file"]).stem.replace("_massive", "")
            print(f"  - {spider_name}: {stat['status']} ({stat['errors']} errors)")
    else:
        print("  All scrapers working properly!")

    print("="*120 + "\n")

if __name__ == "__main__":
    main()
