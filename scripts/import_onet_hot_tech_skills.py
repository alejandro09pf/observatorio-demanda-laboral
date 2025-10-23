#!/usr/bin/env python3
"""
Import O*NET Hot Technology Skills into esco_skills table.

This script filters and imports only "Hot Technologies" from O*NET's
Technology Skills database for IT occupations (SOC codes 15-xxxx).
"""

import pandas as pd
import psycopg2
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings

def import_onet_hot_technologies():
    """Import O*NET Hot Technologies into esco_skills table."""

    settings = get_settings()

    # Normalize database URL
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    print("=" * 70)
    print("O*NET HOT TECHNOLOGY SKILLS IMPORT")
    print("=" * 70)

    # Load O*NET Technology Skills
    data_file = Path(__file__).parent.parent / 'data' / 'onet' / 'Technology_Skills.txt'

    if not data_file.exists():
        print(f"❌ ERROR: File not found: {data_file}")
        print(f"   Please ensure Technology_Skills.txt is in data/onet/")
        return

    print(f"📂 Loading O*NET data from: {data_file}")

    df = pd.read_csv(data_file, delimiter='\t', encoding='utf-8')
    print(f"   Total records: {len(df):,}")

    # Filter: IT occupations (15-xxxx) + Hot Technology only
    hot_tech_df = df[
        (df['O*NET-SOC Code'].str.startswith('15-')) &
        (df['Hot Technology'] == 'Y')
    ]

    print(f"   IT Hot Technologies: {len(hot_tech_df):,}")

    # Get unique technologies
    unique_techs = hot_tech_df[['Example', 'Commodity Title', 'In Demand']].drop_duplicates(subset=['Example'])
    unique_techs = unique_techs.sort_values('Example')

    print(f"   Unique technologies: {len(unique_techs):,}")
    print()

    # Connect to database
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Check current skills count
    cursor.execute("SELECT COUNT(*) FROM esco_skills")
    before_count = cursor.fetchone()[0]
    print(f"📊 Current esco_skills count: {before_count:,}")
    print()

    inserted = 0
    skipped = 0
    errors = 0

    # Generic terms to skip (too vague)
    skip_patterns = [
        'software',
        'Software',
        'system',
        'System',
        'tool',
        'Tool',
        'application',
        'Application'
    ]

    print("🚀 Starting import...")
    print()

    for idx, row in unique_techs.iterrows():
        tech_name = row['Example'].strip()
        tech_category = row['Commodity Title'].strip()
        in_demand = row['In Demand'] == 'Y'

        # Skip generic/vague names (e.g., "Database software", "Email software")
        # Allow if it's a single word or brand name
        words = tech_name.split()
        if len(words) > 2 and any(pattern in tech_name for pattern in skip_patterns):
            skipped += 1
            continue

        skill_uri = f"onet:hot:{inserted:04d}"
        skill_type = 'onet_in_demand' if in_demand else 'onet_hot_tech'

        try:
            cursor.execute("""
                INSERT INTO esco_skills (
                    skill_uri, skill_id,
                    preferred_label_en, preferred_label_es,
                    description_es, description_en,
                    skill_type, skill_group, skill_family,
                    is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (skill_uri) DO NOTHING
            """, (
                skill_uri,
                f"hot:{inserted:04d}",
                tech_name,
                tech_name,  # No traducir nombres técnicos
                f"Tecnología: {tech_category}",
                f"Technology: {tech_category}",
                skill_type,
                tech_category,
                'IT & Software Development',
                True
            ))

            inserted += 1

            if inserted % 50 == 0:
                print(f"   ✓ Inserted {inserted} skills...")
                conn.commit()

        except Exception as e:
            errors += 1
            print(f"   ❌ Error with '{tech_name}': {e}")
            continue

    conn.commit()

    # Final stats
    cursor.execute("SELECT COUNT(*) FROM esco_skills")
    after_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM esco_skills
        WHERE skill_type IN ('onet_hot_tech', 'onet_in_demand')
    """)
    onet_count = cursor.fetchone()[0]

    print()
    print("=" * 70)
    print("✅ IMPORT COMPLETED")
    print("=" * 70)
    print(f"   Inserted:       {inserted:,}")
    print(f"   Skipped:        {skipped:,} (generic terms)")
    print(f"   Errors:         {errors:,}")
    print()
    print(f"📊 Database Stats:")
    print(f"   Before:         {before_count:,}")
    print(f"   After:          {after_count:,}")
    print(f"   O*NET skills:   {onet_count:,}")
    print(f"   ESCO skills:    {before_count:,}")
    print()

    # Show sample of imported skills
    print("📋 Sample of imported skills:")
    cursor.execute("""
        SELECT preferred_label_en, skill_group, skill_type
        FROM esco_skills
        WHERE skill_type IN ('onet_hot_tech', 'onet_in_demand')
        ORDER BY preferred_label_en
        LIMIT 20
    """)

    for label, group, stype in cursor.fetchall():
        marker = "⭐⭐" if stype == 'onet_in_demand' else "⭐"
        print(f"   {marker} {label:<30} ({group})")

    cursor.close()
    conn.close()

    print()
    print("✅ Done!")

if __name__ == '__main__':
    import_onet_hot_technologies()
