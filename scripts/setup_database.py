#!/usr/bin/env python3
"""
Database setup script for Labor Market Observatory.
Creates database, extensions, and initial schema.
"""

import os
import sys
import psycopg2
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from config.database import get_database_config

def setup_database():
    """Set up the database with required extensions and schema."""
    
    # Get database configuration
    db_config = get_database_config()
    
    # Connect to PostgreSQL server (not specific database)
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        user=db_config['user'],
        password=db_config['password'],
        database='postgres'  # Connect to default database
    )
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        # Create database if it doesn't exist
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_config['database'],))
        if not cursor.fetchone():
            print(f"Creating database: {db_config['database']}")
            cursor.execute(f"CREATE DATABASE {db_config['database']}")
            print("Database created successfully!")
        else:
            print(f"Database {db_config['database']} already exists.")
        
        # Close connection to postgres database
        cursor.close()
        conn.close()
        
        # Connect to the new database
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config['database']
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Enable required extensions
        print("Enabling required extensions...")
        cursor.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
        print("✅ uuid-ossp extension enabled successfully!")
        
        # Note: pgvector extension is not available in the current PostgreSQL image
        # It will be added later when we upgrade to a compatible image
        print("⚠️  pgvector extension skipped - not available in current image")
        
        # Run migration script
        migration_file = Path(__file__).parent.parent / "src" / "database" / "migrations" / "001_initial_schema.sql"
        
        if migration_file.exists():
            print(f"Running migration: {migration_file}")
            with open(migration_file, 'r') as f:
                migration_sql = f.read()
            
            # Split and execute SQL statements
            statements = migration_sql.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                    except Exception as e:
                        print(f"Warning: Could not execute statement: {e}")
                        print(f"Statement: {statement[:100]}...")
            
            print("✅ Migration completed successfully!")
        else:
            print(f"Warning: Migration file not found: {migration_file}")
        
        print("\n🎉 Database setup completed successfully!")
        
    except Exception as e:
        print(f"Error setting up database: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    setup_database() 