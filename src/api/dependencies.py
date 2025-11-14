"""
FastAPI dependencies for database sessions, configuration, etc.
"""
from typing import Generator
from sqlalchemy.orm import Session
from functools import lru_cache

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.operations import DatabaseOperations
from config.settings import get_settings, Settings


# Database operations instance
db_ops = DatabaseOperations()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a database session.
    Automatically closes session after request.
    """
    session = db_ops.get_session()
    try:
        yield session
    finally:
        session.close()


@lru_cache()
def get_settings_cached() -> Settings:
    """
    Dependency that provides cached application settings.
    """
    return get_settings()
