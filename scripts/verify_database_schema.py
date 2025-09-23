#!/usr/bin/env python3
"""
Verify database schema and table structure.
"""

import psycopg2
import json
from datetime import datetime

def verify_database_schema():
    """Verify database schema and table structure."""
    try:
        conn = psycopg2.connect(
            host="localhost",
            port=5433,
            database="labor_observatory",
            user="labor_user",
            password="your_password"
        )
        cursor = conn.cursor()
        
        print("🔍 Verifying database schema...")
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\n📋 Tables found: {len(tables)}")
        for table in tables:
            print(f"  - {table}")
        
        # Get detailed schema for raw_jobs table
        print(f"\n🔍 Detailed schema for 'raw_jobs' table:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'raw_jobs' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        schema_info = {
            "table": "raw_jobs",
            "columns": [],
            "constraints": []
        }
        
        for col in columns:
            col_info = {
                "name": col[0],
                "type": col[1],
                "nullable": col[2] == "YES",
                "default": col[3],
                "max_length": col[4]
            }
            schema_info["columns"].append(col_info)
            print(f"  {col[0]}: {col[1]} {'(nullable)' if col[2] == 'YES' else '(NOT NULL)'}")
        
        # Get constraints
        cursor.execute("""
            SELECT conname, pg_get_constraintdef(oid) 
            FROM pg_constraint 
            WHERE conrelid = 'raw_jobs'::regclass 
            AND contype = 'c';
        """)
        constraints = cursor.fetchall()
        
        print(f"\n🔒 Constraints:")
        for constraint_name, constraint_def in constraints:
            schema_info["constraints"].append({
                "name": constraint_name,
                "definition": constraint_def
            })
            print(f"  {constraint_name}: {constraint_def}")
        
        # Save schema info
        with open("debug_database_schema.json", "w") as f:
            json.dump(schema_info, f, indent=2, default=str)
        
        print(f"\n✅ Database schema verification completed")
        print(f"📄 Schema details saved to: debug_database_schema.json")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to verify database schema: {e}")
        return False

if __name__ == "__main__":
    verify_database_schema()

