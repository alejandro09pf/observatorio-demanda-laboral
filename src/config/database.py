import os
from urllib.parse import urlparse

def get_database_url() -> str:
    """Get database URL from environment or construct from components."""
    if os.getenv('DATABASE_URL'):
        return os.getenv('DATABASE_URL')
    
    # Construct from individual components
    user = os.getenv('DB_USER', 'labor_user')
    password = os.getenv('DB_PASSWORD', 'password')
    host = os.getenv('DB_HOST', 'localhost')
    port = os.getenv('DB_PORT', '5432')
    name = os.getenv('DB_NAME', 'labor_observatory')
    
    return f"postgresql://{user}:{password}@{host}:{port}/{name}"

def get_database_config() -> dict:
    """Parse database URL into components."""
    url = get_database_url()
    parsed = urlparse(url)
    
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/')
    } 