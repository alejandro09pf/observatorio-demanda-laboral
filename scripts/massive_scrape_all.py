"""
Massive scraping launcher for all available spiders.
Runs all spiders in their respective countries and monitors progress.
"""
import subprocess
import time
from datetime import datetime

# Spider-to-Country mapping (based on portal availability)
SPIDER_CONFIGS = [
    # High priority - Latin America wide portals
    {"spider": "computrabajo", "countries": ["CO", "MX", "AR"], "priority": 1},
    {"spider": "occmundial", "countries": ["MX"], "priority": 1},
    {"spider": "elempleo", "countries": ["CO"], "priority": 1},

    # Medium priority - Regional portals
    {"spider": "bumeran", "countries": ["AR", "MX"], "priority": 2},
    {"spider": "zonajobs", "countries": ["AR"], "priority": 2},
    {"spider": "magneto", "countries": ["CO"], "priority": 2},

    # Lower priority - Specific portals (may have bot detection)
    {"spider": "hiring_cafe", "countries": ["MX"], "priority": 3},
    {"spider": "indeed", "countries": ["MX", "CO", "AR"], "priority": 3},
]

def launch_spider(spider_name, country, log_file):
    """Launch a spider in background with unlimited pages."""
    cmd = f'python -m src.orchestrator run-once {spider_name} -c {country} -v'

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Launching: {spider_name} ({country}) -> {log_file}")

    # Launch in background and redirect output to log file
    process = subprocess.Popen(
        cmd,
        shell=True,
        stdout=open(log_file, 'w', encoding='utf-8'),
        stderr=subprocess.STDOUT
    )

    return process

def main():
    print("="*100)
    print("MASSIVE SCRAPING OPERATION - ALL PORTALS")
    print("="*100)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    processes = []

    # Launch all spiders
    for config in SPIDER_CONFIGS:
        spider = config["spider"]
        countries = config["countries"]
        priority = config["priority"]

        print(f"\nPriority {priority}: {spider.upper()}")
        print("-" * 50)

        for country in countries:
            log_file = f"logs/{spider}_{country.lower()}_massive.log"
            process = launch_spider(spider, country, log_file)
            processes.append({
                "spider": spider,
                "country": country,
                "process": process,
                "log_file": log_file,
                "priority": priority
            })

            # Small delay to avoid overwhelming the system
            time.sleep(2)

    print("\n" + "="*100)
    print(f"Total scrapers launched: {len(processes)}")
    print("="*100)

    # Print summary
    print("\nSCRAPING JOBS LAUNCHED:")
    print("-" * 100)
    for p in processes:
        print(f"  - {p['spider']:<15} {p['country']:<5} (Priority {p['priority']})  -> {p['log_file']}")

    print("\n" + "="*100)
    print("All scrapers are running in background.")
    print("Monitor progress with:")
    print("  - python scripts/get_portal_stats.py")
    print("  - tail -f logs/<spider>_<country>_massive.log")
    print("="*100)

if __name__ == "__main__":
    main()
