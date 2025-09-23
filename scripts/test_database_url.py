#!/usr/bin/env python3
"""
Test DATABASE_URL loading.
"""

import os
from dotenv import load_dotenv

def test_database_url():
    """Test DATABASE_URL loading."""
    # Load .env file
    load_dotenv()
    
    print("DATABASE_URL:", os.getenv('DATABASE_URL'))
    
    # Test if it's None
    if os.getenv('DATABASE_URL') is None:
        print("❌ DATABASE_URL is None")
        return False
    else:
        print("✅ DATABASE_URL loaded successfully")
        return True

if __name__ == "__main__":
    test_database_url()

