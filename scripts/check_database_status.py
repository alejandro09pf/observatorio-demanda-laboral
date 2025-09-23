#!/usr/bin/env python3
"""
Check current database status and job counts.
"""

import psycopg2

def check_database_status():
    """Check current database status."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="labor_observatory",
            user="labor_user",
            password="your_password"
        )
        cursor = conn.cursor()
        
        # Get total count
        cursor.execute("SELECT COUNT(*) FROM raw_jobs;")
        total_count = cursor.fetchone()[0]
        print(f"📊 Total jobs in database: {total_count}")
        
        # Get count by portal
        cursor.execute("SELECT portal, COUNT(*) FROM raw_jobs GROUP BY portal ORDER BY COUNT(*) DESC;")
        portal_counts = cursor.fetchall()
        print("\n📈 Jobs by portal:")
        for portal, count in portal_counts:
            print(f"  {portal}: {count}")
        
        # Get count by country
        cursor.execute("SELECT country, COUNT(*) FROM raw_jobs GROUP BY country ORDER BY COUNT(*) DESC;")
        country_counts = cursor.fetchall()
        print("\n🌍 Jobs by country:")
        for country, count in country_counts:
            print(f"  {country}: {count}")
        
        # Get recent jobs
        cursor.execute("""
            SELECT portal, country, title, scraped_at 
            FROM raw_jobs 
            ORDER BY scraped_at DESC 
            LIMIT 5;
        """)
        recent_jobs = cursor.fetchall()
        print("\n🕒 Recent jobs:")
        for portal, country, title, scraped_at in recent_jobs:
            print(f"  {portal} ({country}): {title[:50]}... - {scraped_at}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to check database status: {e}")
        return False

if __name__ == "__main__":
    check_database_status()

