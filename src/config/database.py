"""
Database configuration utilities for Labor Market Observatory.
"""

import os
from urllib.parse import urlparse
from typing import Dict, Any

def get_database_url() -> str:
    """Get database URL from environment variables."""
    return os.getenv('DATABASE_URL', 'postgresql://labor_user:your_password@localhost:5433/labor_observatory')

def get_database_config() -> Dict[str, Any]:
    """Parse database URL and return configuration dictionary."""
    database_url = get_database_url()
    parsed = urlparse(database_url)
    
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5433,
        'user': parsed.username or 'labor_user',
        'password': parsed.password or 'your_password',
        'database': parsed.path.lstrip('/') or 'labor_observatory'
    } 