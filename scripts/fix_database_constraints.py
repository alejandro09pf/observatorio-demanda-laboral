#!/usr/bin/env python3
"""
Fix database constraints to support all scraper portal names and country codes.
"""

import psycopg2
import sys
from pathlib import Path

def fix_database_constraints():
    """Update database constraints to support all scraper outputs."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="labor_observatory",
            user="labor_user",
            password="your_password"
        )
        cursor = conn.cursor()
        
        print("🔧 Fixing database constraints...")
        
        # Fix portal constraint
        print("1. Updating portal constraint...")
        cursor.execute("ALTER TABLE raw_jobs DROP CONSTRAINT IF EXISTS chk_portal;")
        cursor.execute("""
            ALTER TABLE raw_jobs ADD CONSTRAINT chk_portal 
            CHECK (portal IN ('computrabajo', 'bumeran', 'elempleo', 'indeed', 'zonajobs', 'hiring_cafe', 'magneto', 'test_portal'));
        """)
        print("   ✅ Portal constraint updated")
        
        # Fix country constraint  
        print("2. Updating country constraint...")
        cursor.execute("ALTER TABLE raw_jobs DROP CONSTRAINT IF EXISTS chk_country;")
        cursor.execute("""
            ALTER TABLE raw_jobs ADD CONSTRAINT chk_country 
            CHECK (country IN ('CO', 'MX', 'AR', 'US', 'CA'));
        """)
        print("   ✅ Country constraint updated")
        
        # Commit changes
        conn.commit()
        print("✅ Database constraints updated successfully!")
        
        # Verify constraints
        print("\n3. Verifying constraints...")
        cursor.execute("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'raw_jobs'::regclass 
            AND contype = 'c';
        """)
        constraints = cursor.fetchall()
        
        for constraint_name, constraint_def in constraints:
            print(f"   {constraint_name}: {constraint_def}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix database constraints: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    success = fix_database_constraints()
    if success:
        print("\n🎉 Database constraints fixed successfully!")
        print("Scrapers should now be able to insert data without constraint violations.")
    else:
        print("\n⚠️  Failed to fix database constraints.")
        sys.exit(1)
