"""
Labor Market Observatory

An automated system for collecting, processing, and analyzing job market data
from Latin American job portals to provide insights into skill demand trends.
"""

__version__ = "1.0.0"
__author__ = "Nicolás Francisco Camacho Alarcón y Alejandro Pinzón"
__description__ = "Automated Labor Market Observatory for Latin America"

# Import main components for easy access
try:
    from .orchestrator import app
    from .database.operations import DatabaseOperations
    from .config.settings import get_settings
except ImportError:
    # Handle import errors gracefully during development
    pass

__all__ = [
    "app",
    "DatabaseOperations", 
    "get_settings",
    "__version__",
    "__author__",
    "__description__"
]
