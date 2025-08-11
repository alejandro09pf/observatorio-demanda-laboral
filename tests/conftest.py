import pytest
import os
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

@pytest.fixture
def test_database_url():
    """Test database URL."""
    return "postgresql://test_user:test_pass@localhost:5432/test_db"

@pytest.fixture
def sample_job_data():
    """Sample job data for testing."""
    return {
        "portal": "computrabajo",
        "country": "CO",
        "url": "https://example.com/job/1",
        "title": "Software Developer",
        "company": "Tech Corp",
        "description": "We are looking for a Python developer with Django experience.",
        "requirements": "Python, Django, PostgreSQL"
    } 