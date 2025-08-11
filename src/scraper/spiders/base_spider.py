"""
Base spider class for Labor Market Observatory job portals.
"""

import scrapy
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from urllib.parse import urljoin, urlparse
from datetime import datetime
import logging
from ..items import JobItem

logger = logging.getLogger(__name__)

class BaseSpider(scrapy.Spider, ABC):
    """Abstract base class for all job spiders."""
    
    # Spider configuration
    custom_settings = {
        'DOWNLOAD_DELAY': 1,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 4,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1,
        'AUTOTHROTTLE_MAX_DELAY': 3,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 1.0,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.country = kwargs.get('country', 'CO')
        self.portal = kwargs.get('portal', 'computrabajo')
        self.max_pages = int(kwargs.get('max_pages', 1))
        self.current_page = 0
        
        # Validate country
        if self.country not in ['CO', 'MX', 'AR']:
            raise ValueError(f"Unsupported country: {self.country}")
    
    @abstractmethod
    def parse_job(self, response) -> JobItem:
        """Parse individual job posting. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def parse_search_results(self, response) -> None:
        """Parse search results page. Must be implemented by subclasses."""
        pass
    
    def extract_text(self, selector, default: str = "") -> str:
        """Extract and clean text from CSS selector."""
        text = selector.get(default=default)
        if text:
            return text.strip()
        return default
    
    def build_absolute_url(self, relative_url: str, base_url: str) -> str:
        """Build absolute URL from relative URL."""
        if not relative_url:
            return ""
        return urljoin(base_url, relative_url)
    
    def log_progress(self, current: int, total: int) -> None:
        """Log scraping progress."""
        if total > 0:
            percentage = (current / total) * 100
            logger.info(f"Progress: {current}/{total} ({percentage:.1f}%)")
    
    def validate_job_item(self, item: JobItem) -> bool:
        """Validate that job item has required fields."""
        required_fields = ['title', 'description', 'url']
        
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common HTML artifacts
        text = text.replace('\xa0', ' ')  # Non-breaking space
        text = text.replace('\u200b', '')  # Zero-width space
        
        return text.strip()
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse date string to ISO format."""
        if not date_string:
            return None
        
        try:
            # Add common date parsing logic here
            # This is a simplified version - subclasses can override
            return datetime.today().date().isoformat()
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return None
    
    def handle_pagination(self, response, next_page_selector: str) -> Optional[scrapy.Request]:
        """Handle pagination if available."""
        if self.current_page >= self.max_pages:
            logger.info(f"Reached maximum pages limit: {self.max_pages}")
            return None
        
        next_page = response.css(next_page_selector).get()
        if next_page:
            self.current_page += 1
            next_url = self.build_absolute_url(next_page, response.url)
            logger.info(f"Moving to page {self.current_page}: {next_url}")
            return scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={'page': self.current_page}
            )
        
        return None
    
    def start_requests(self):
        """Start requests for the spider."""
        logger.info(f"Starting {self.name} spider for {self.country}/{self.portal}")
        
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_search_results,
                meta={'page': 1}
            )
    
    def closed(self, reason):
        """Called when spider is closed."""
        logger.info(f"Spider {self.name} closed: {reason}")
        logger.info(f"Total pages processed: {self.current_page}")
