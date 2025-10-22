"""
Quick script to get detailed job statistics by portal and country.
"""
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

# Get database URL
database_url = os.getenv('DATABASE_URL')

# Create engine
engine = create_engine(database_url, pool_pre_ping=True)

# Query for statistics grouped by portal and country
query = text("""
    SELECT
        portal,
        country,
        COUNT(*) as job_count,
        COUNT(DISTINCT CASE WHEN is_processed = true THEN job_id END) as processed_count,
        MIN(scraped_at) as first_scraped,
        MAX(scraped_at) as last_scraped
    FROM raw_jobs
    WHERE portal != 'computrabajo'  -- Excluding computrabajo as requested
    GROUP BY portal, country
    ORDER BY job_count DESC;
""")

print("\n" + "="*100)
print("📊 DATABASE STATISTICS BY PORTAL AND COUNTRY (excluding Computrabajo)")
print("="*100 + "\n")

with engine.connect() as conn:
    result = conn.execute(query)

    print(f"{'Portal':<15} {'Country':<10} {'Total Jobs':<12} {'Processed':<12} {'First Scraped':<20} {'Last Scraped':<20}")
    print("-" * 100)

    total_jobs = 0
    for row in result:
        portal, country, job_count, processed_count, first_scraped, last_scraped = row
        total_jobs += job_count

        first_str = first_scraped.strftime("%Y-%m-%d %H:%M") if first_scraped else "N/A"
        last_str = last_scraped.strftime("%Y-%m-%d %H:%M") if last_scraped else "N/A"

        print(f"{portal:<15} {country:<10} {job_count:<12} {processed_count:<12} {first_str:<20} {last_str:<20}")

    print("-" * 100)
    print(f"{'TOTAL':<15} {'':<10} {total_jobs:<12}")
    print("="*100)

# Also get Computrabajo stats separately for comparison
query_computrabajo = text("""
    SELECT
        portal,
        country,
        COUNT(*) as job_count,
        COUNT(DISTINCT CASE WHEN is_processed = true THEN job_id END) as processed_count,
        MIN(scraped_at) as first_scraped,
        MAX(scraped_at) as last_scraped
    FROM raw_jobs
    WHERE portal = 'computrabajo'
    GROUP BY portal, country
    ORDER BY job_count DESC;
""")

print("\n📌 COMPUTRABAJO STATS (for reference - currently being repaired):")
print("-" * 100)

with engine.connect() as conn:
    result = conn.execute(query_computrabajo)

    computrabajo_total = 0
    for row in result:
        portal, country, job_count, processed_count, first_scraped, last_scraped = row
        computrabajo_total += job_count

        first_str = first_scraped.strftime("%Y-%m-%d %H:%M") if first_scraped else "N/A"
        last_str = last_scraped.strftime("%Y-%m-%d %H:%M") if last_scraped else "N/A"

        print(f"{portal:<15} {country:<10} {job_count:<12} {processed_count:<12} {first_str:<20} {last_str:<20}")

    print(f"{'TOTAL':<15} {'':<10} {computrabajo_total:<12}")
    print("="*100 + "\n")
