"""
Test deduplication functionality.
"""

import pytest
import psycopg2
import hashlib
from unittest.mock import patch, MagicMock
from src.scraper.pipelines import JobPostgresPipeline
from src.scraper.items import JobItem


class TestDeduplication:
    """Test deduplication functionality."""
    
    @pytest.fixture
    def pipeline(self):
        """Create a pipeline instance for testing."""
        pipeline = JobPostgresPipeline()
        pipeline.connection = MagicMock()
        pipeline.cursor = MagicMock()
        return pipeline
    
    @pytest.fixture
    def sample_item(self):
        """Create a sample job item."""
        item = JobItem()
        item['portal'] = 'test'
        item['country'] = 'CO'
        item['url'] = 'https://example.com/job1'
        item['title'] = 'Software Engineer'
        item['company'] = 'Test Company'
        item['location'] = 'Bogotá'
        item['description'] = 'We are looking for a software engineer'
        item['requirements'] = 'Python, Django, PostgreSQL'
        item['salary_raw'] = '50000'
        item['contract_type'] = 'Full-time'
        item['remote_type'] = 'Hybrid'
        item['posted_date'] = '2024-01-01'
        return item
    
    def test_content_hash_generation(self, pipeline, sample_item):
        """Test that content hash is generated correctly."""
        # Process item
        result = pipeline.process_item(sample_item, MagicMock())
        
        # Verify cursor was called with correct parameters
        pipeline.cursor.execute.assert_called_once()
        
        # Get the call arguments
        call_args = pipeline.cursor.execute.call_args
        sql = call_args[0][0]
        params = call_args[0][1]
        
        # Verify SQL contains ON CONFLICT
        assert 'ON CONFLICT (content_hash) DO NOTHING' in sql
        
        # Verify content_hash is in parameters
        assert len(params) == 13  # All fields + content_hash
        content_hash = params[12]
        
        # Verify hash is correct
        expected_content = f"{sample_item['title']}{sample_item['description']}{sample_item['requirements']}"
        expected_hash = hashlib.sha256(expected_content.encode("utf-8")).hexdigest()
        assert content_hash == expected_hash
    
    def test_duplicate_detection(self, pipeline, sample_item):
        """Test that duplicates are detected and skipped."""
        # Mock cursor to simulate duplicate (rowcount = 0)
        pipeline.cursor.rowcount = 0
        
        # Process item
        result = pipeline.process_item(sample_item, MagicMock())
        
        # Verify item is returned (not dropped)
        assert result == sample_item
        
        # Verify cursor was called
        pipeline.cursor.execute.assert_called_once()
    
    def test_new_item_insertion(self, pipeline, sample_item):
        """Test that new items are inserted successfully."""
        # Mock cursor to simulate successful insertion (rowcount = 1)
        pipeline.cursor.rowcount = 1
        
        # Process item
        result = pipeline.process_item(sample_item, MagicMock())
        
        # Verify item is returned
        assert result == sample_item
        
        # Verify cursor was called
        pipeline.cursor.execute.assert_called_once()
    
    def test_database_error_handling(self, pipeline, sample_item):
        """Test that database errors are handled properly."""
        # Mock cursor to raise an exception
        pipeline.cursor.execute.side_effect = psycopg2.Error("Database error")
        
        # Process item should raise DropItem
        with pytest.raises(Exception) as exc_info:
            pipeline.process_item(sample_item, MagicMock())
        
        assert "Database error" in str(exc_info.value)
    
    def test_missing_fields_handling(self, pipeline):
        """Test handling of items with missing fields."""
        item = JobItem()
        item['portal'] = 'test'
        item['country'] = 'CO'
        item['url'] = 'https://example.com/job1'
        item['title'] = 'Software Engineer'
        item['description'] = 'We are looking for a software engineer'
        # Missing requirements field
        
        # Mock cursor to simulate successful insertion
        pipeline.cursor.rowcount = 1
        
        # Process item should work with missing optional fields
        result = pipeline.process_item(item, MagicMock())
        
        # Verify item is returned
        assert result == item
        
        # Verify cursor was called
        pipeline.cursor.execute.assert_called_once()
        
        # Get parameters and verify requirements is None
        call_args = pipeline.cursor.execute.call_args
        params = call_args[0][1]
        requirements_index = 7  # requirements is the 8th parameter
        assert params[requirements_index] is None
