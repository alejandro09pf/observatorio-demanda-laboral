#!/usr/bin/env python3
"""
Test environment variables loading.
"""

import os
from dotenv import load_dotenv

def test_env_vars():
    """Test environment variables loading."""
    # Load .env file
    load_dotenv()
    
    print("Environment variables:")
    print(f"DB_HOST: {os.getenv('DB_HOST')}")
    print(f"DB_PORT: {os.getenv('DB_PORT')}")
    print(f"DB_NAME: {os.getenv('DB_NAME')}")
    print(f"DB_USER: {os.getenv('DB_USER')}")
    print(f"DB_PASSWORD: {os.getenv('DB_PASSWORD')}")
    
    # Test database connection
    import psycopg2
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5433)),
            database=os.getenv('DB_NAME', 'labor_observatory'),
            user=os.getenv('DB_USER', 'labor_user'),
            password=os.getenv('DB_PASSWORD', 'your_password')
        )
        print("✅ Database connection successful with environment variables")
        conn.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

if __name__ == "__main__":
    test_env_vars()

