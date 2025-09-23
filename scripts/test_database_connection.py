#!/usr/bin/env python3
"""
Test database connection and create debugging files for Docker PostgreSQL setup.
"""

import os
import sys
import psycopg2
import json
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_database_connection():
    """Test database connection and log results."""
    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "connection_tests": [],
        "database_structure": {},
        "errors": []
    }
    
    # Test different connection configurations
    connection_configs = [
        {
            "name": "Docker PostgreSQL (port 5433)",
            "host": "localhost",
            "port": 5433,
            "database": "labor_observatory",
            "user": "labor_user",
            "password": "your_password"
        },
        {
            "name": "Docker PostgreSQL (port 5432)",
            "host": "localhost", 
            "port": 5432,
            "database": "labor_observatory",
            "user": "labor_user",
            "password": "your_password"
        },
        {
            "name": "Environment DATABASE_URL",
            "url": os.getenv('DATABASE_URL', 'postgresql://labor_user:your_password@localhost:5433/labor_observatory')
        }
    ]
    
    successful_connection = None
    
    for config in connection_configs:
        test_result = {
            "config_name": config["name"],
            "success": False,
            "error": None,
            "tables": [],
            "table_schemas": {}
        }
        
        try:
            if "url" in config:
                conn = psycopg2.connect(config["url"])
            else:
                conn = psycopg2.connect(
                    host=config["host"],
                    port=config["port"],
                    database=config["database"],
                    user=config["user"],
                    password=config["password"]
                )
            
            cursor = conn.cursor()
            
            # Test basic connection
            cursor.execute("SELECT version();")
            version = cursor.fetchone()[0]
            test_result["postgres_version"] = version
            
            # List all tables
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row[0] for row in cursor.fetchall()]
            test_result["tables"] = tables
            
            # Get schema for each table
            for table in tables:
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = %s AND table_schema = 'public'
                    ORDER BY ordinal_position;
                """, (table,))
                
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == "YES",
                        "default": row[3]
                    })
                
                test_result["table_schemas"][table] = columns
            
            # Check if raw_jobs table exists and has data
            if "raw_jobs" in tables:
                cursor.execute("SELECT COUNT(*) FROM raw_jobs;")
                job_count = cursor.fetchone()[0]
                test_result["raw_jobs_count"] = job_count
                
                # Get sample data
                cursor.execute("SELECT * FROM raw_jobs LIMIT 3;")
                sample_jobs = cursor.fetchall()
                test_result["sample_jobs"] = sample_jobs
            
            test_result["success"] = True
            successful_connection = conn
            
        except Exception as e:
            test_result["error"] = str(e)
            debug_info["errors"].append(f"{config['name']}: {str(e)}")
        
        debug_info["connection_tests"].append(test_result)
        
        if "conn" in locals() and not conn.closed:
            conn.close()
    
    # Save debug information
    debug_file = Path("debug_database_connection.json")
    with open(debug_file, "w") as f:
        json.dump(debug_info, f, indent=2, default=str)
    
    print(f"Database connection test completed. Results saved to {debug_file}")
    
    if successful_connection:
        print("✅ Database connection successful!")
        return successful_connection
    else:
        print("❌ All database connection attempts failed!")
        return None

def test_insert_operation(conn):
    """Test inserting a sample job record."""
    if not conn:
        print("No database connection available for insert test")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Test insert with sample data
        test_job = {
            "portal": "test_portal",
            "country": "CO",
            "url": "https://test.com/job/123",
            "title": "Test Developer Position",
            "company": "Test Company",
            "location": "Test City",
            "description": "This is a test job description for database testing.",
            "requirements": "Python, SQL, Testing",
            "content_hash": "test_hash_12345"
        }
        
        insert_query = """
            INSERT INTO raw_jobs (portal, country, url, title, company, location, description, requirements, content_hash)
            VALUES (%(portal)s, %(country)s, %(url)s, %(title)s, %(company)s, %(location)s, %(description)s, %(requirements)s, %(content_hash)s)
            RETURNING job_id;
        """
        
        cursor.execute(insert_query, test_job)
        job_id = cursor.fetchone()[0]
        conn.commit()
        
        print(f"✅ Test job inserted successfully with ID: {job_id}")
        
        # Verify the insert
        cursor.execute("SELECT * FROM raw_jobs WHERE job_id = %s;", (job_id,))
        inserted_job = cursor.fetchone()
        
        if inserted_job:
            print("✅ Job verification successful - record found in database")
            return True
        else:
            print("❌ Job verification failed - record not found")
            return False
            
    except Exception as e:
        print(f"❌ Insert test failed: {e}")
        conn.rollback()
        return False

if __name__ == "__main__":
    print("Testing database connection...")
    conn = test_database_connection()
    
    if conn:
        print("\nTesting insert operation...")
        test_insert_operation(conn)
        conn.close()
