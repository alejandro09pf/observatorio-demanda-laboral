"""
Magneto spider for Labor Market Observatory.
Scrapes job postings from Magneto365 Colombia using JSON-LD structured data.
"""

import scrapy
import json
import re
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import Optional, Dict, Any
from .base_spider import BaseSpider
from ..items import JobItem
import logging

logger = logging.getLogger(__name__)


class MagnetoSpider(BaseSpider):
    """Spider for Magneto365 job portal using JSON-LD structured data."""

    name = "magneto"
    allowed_domains = ["magneto365.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "magneto"
        self.max_pages = int(kwargs.get('max_pages', 10))
        self.current_page = 0
        
        # Set start URLs based on country
        if self.country == "CO":
            self.start_urls = ["https://www.magneto365.com/co/empleos"]
        elif self.country == "MX":
            logger.warning("Magneto spider is disabled for Mexico as the target URL is no longer available.")
            return
        elif self.country == "AR":
            self.start_urls = ["https://www.magneto365.com/ar/empleos"]
        else:
            # Default to Colombia
            self.start_urls = ["https://www.magneto365.com/co/empleos"]

        # Override custom settings for this spider - optimized for mass scraping
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 0.1,  # Minimal delay for mass scraping
            'CONCURRENT_REQUESTS_PER_DOMAIN': 32,  # Increased for mass scraping
            'ROBOTSTXT_OBEY': False,
            'DOWNLOAD_TIMEOUT': 10,  # Reduced timeout for faster failures
            'LOG_LEVEL': 'INFO',  # Reduced logging for performance
            'DUPEFILTER_CLASS': None,  # Disable duplicate filtering
        })

    async def start(self):
        """Start coroutine for listing pages."""
        logger.info(f"Starting Magneto spider for country: {self.country}")
        logger.info(f"Max pages: {self.max_pages}")

        if not self.start_urls:
            logger.warning("No start URLs available. Exiting spider.")
            return

        # Start with the first page
        yield scrapy.Request(
            url=self.start_urls[0],
            callback=self.parse_listing_page,
            meta={'page': 1}
        )

    def parse_listing_page(self, response):
        """Parse listing page and extract job URLs from JSON-LD ItemList."""
        if response.status == 410:
            logger.warning(f"Received HTTP 410 for URL: {response.url}. Skipping.")
            return

        current_page = response.meta.get('page', 1)
        logger.info(f"Parsing listing page {current_page}: {response.url}")

        # Find JSON-LD scripts
        json_ld_scripts = response.css('script[type="application/ld+json"]')
        
        job_urls = []
        
        for script in json_ld_scripts:
            try:
                # Get script content - extract text from within script tags
                script_content = script.xpath('text()').get()
                if not script_content:
                    continue
                
                json_data = json.loads(script_content)
                
                # Look for ItemList with job URLs
                if json_data.get('@type') == 'ItemList':
                    item_list = json_data.get('itemListElement', [])
                    logger.info(f"Found ItemList with {len(item_list)} items")
                    
                    for item in item_list:
                        if isinstance(item, dict) and item.get('@type') == 'ListItem':
                            job_url = item.get('url')
                            if job_url:
                                job_urls.append(job_url)
                                logger.debug(f"Found job URL: {job_url}")
                    
                    break  # Found ItemList, no need to check other scripts
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Error parsing JSON-LD script: {e}")
                continue

        logger.info(f"Extracted {len(job_urls)} job URLs from page {current_page}")

        # Follow each job URL to get detailed information
        for job_url in job_urls:
            yield scrapy.Request(
                url=job_url,
                callback=self.parse_job_detail,
                meta={'source_page': current_page}
            )

        # Handle pagination
        if current_page < self.max_pages and job_urls:
            next_page = current_page + 1
            next_url = f"{self.start_urls[0]}?page={next_page}"
            
            logger.info(f"Following to page {next_page}: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_listing_page,
                meta={'page': next_page}
            )

    def parse_job_detail(self, response):
        """Parse job detail page and extract information from JSON-LD JobPosting."""
        source_page = response.meta.get('source_page', 1)
        logger.info(f"Parsing job detail: {response.url} (from page {source_page})")

        # Find JSON-LD JobPosting script
        json_ld_scripts = response.css('script[type="application/ld+json"]')
        
        job_data = None
        
        for script in json_ld_scripts:
            try:
                # Get script content - extract text from within script tags
                script_content = script.xpath('text()').get()
                if not script_content:
                    continue
                
                json_data = json.loads(script_content)
                
                # Look for JobPosting
                if json_data.get('@type') == 'JobPosting':
                    job_data = json_data
                    logger.debug(f"Found JobPosting: {job_data.get('title', 'No title')}")
                    break
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Error parsing JSON-LD script: {e}")
                continue

        if not job_data:
            logger.warning(f"No JobPosting JSON-LD found for: {response.url}")
            return

        # Create job item
        item = JobItem()
        
        # Basic information
        item['portal'] = 'magneto'
        item['country'] = self.country
        item['url'] = response.url

        # Extract title
        item['title'] = self.clean_text(job_data.get('title', ''))

        # Extract company
        hiring_org = job_data.get('hiringOrganization', {})
        item['company'] = self.clean_text(hiring_org.get('name', ''))

        # Extract location
        job_location = job_data.get('jobLocation', {})
        
        # Handle case where jobLocation might be a list
        if isinstance(job_location, list):
            job_location = job_location[0] if job_location else {}
        
        address = job_location.get('address', {})
        
        # Handle location arrays (Magneto sometimes uses arrays for location)
        city = address.get('addressLocality', '')
        region = address.get('addressRegion', '')
        
        if isinstance(city, list):
            city = ', '.join(city) if city else ''
        if isinstance(region, list):
            region = ', '.join(region) if region else ''
        
        # Combine city and region
        location_parts = []
        if city:
            location_parts.append(city)
        if region:
            location_parts.append(region)
        
        item['location'] = ', '.join(location_parts) if location_parts else ''

        # Extract description
        description = job_data.get('description', '')
        if description:
            # Clean HTML tags from description
            description = self.clean_html(description)
        item['description'] = description

        # Extract requirements (from qualifications field)
        requirements = job_data.get('qualifications', '')
        if requirements:
            requirements = self.clean_text(requirements)
        item['requirements'] = requirements

        # Extract salary information
        salary_raw = self.extract_salary_from_json(job_data)
        item['salary_raw'] = salary_raw

        # Extract contract type
        employment_type = job_data.get('employmentType', '')
        contract_type = self.map_employment_type(employment_type)
        item['contract_type'] = contract_type

        # Extract remote type from description
        remote_type = self.extract_remote_type_from_description(description)
        item['remote_type'] = remote_type

        # Extract posted date
        posted_date = job_data.get('datePosted', '')
        if posted_date:
            # Convert to ISO format if needed
            posted_date = self.parse_date(posted_date)
        item['posted_date'] = posted_date

        # Validate item
        if not self.validate_job_item(item):
            logger.warning(f"Invalid job item: {item['title']}")
            return

        logger.info(f"Successfully parsed job: {item['title']} at {item['company']}")
        yield item

    def extract_salary_from_json(self, job_data: Dict[str, Any]) -> str:
        """Extract salary information from JobPosting JSON-LD."""
        base_salary = job_data.get('baseSalary', {})
        if not base_salary:
            return ''

        currency = base_salary.get('currency', '')
        value = base_salary.get('value', {})
        unit_text = base_salary.get('unitText', '')

        if not value:
            return ''

        # Extract min and max values
        min_value = value.get('minValue', '')
        max_value = value.get('maxValue', '')
        
        # Build salary string
        salary_parts = []
        
        if min_value and max_value:
            if min_value == max_value:
                salary_parts.append(str(min_value))
            else:
                salary_parts.append(f"{min_value} - {max_value}")
        elif min_value:
            salary_parts.append(f"{min_value}+")
        elif max_value:
            salary_parts.append(f"Up to {max_value}")
        
        if currency:
            salary_parts.append(currency)
        
        if unit_text:
            salary_parts.append(f"per {unit_text.lower()}")

        return ' '.join(salary_parts) if salary_parts else ''

    def map_employment_type(self, employment_type: str) -> str:
        """Map employment type from JSON-LD to standardized format."""
        if not employment_type:
            return ''
        
        employment_type = employment_type.upper()
        
        mapping = {
            'FULL_TIME': 'Tiempo completo',
            'PART_TIME': 'Tiempo parcial',
            'CONTRACTOR': 'Contrato',
            'TEMPORARY': 'Temporal',
            'INTERN': 'Pasantía',
            'VOLUNTEER': 'Voluntario',
            'PER_DIEM': 'Por día',
            'OTHER': 'Otro'
        }
        
        return mapping.get(employment_type, employment_type)

    def extract_remote_type_from_description(self, description: str) -> str:
        """Extract remote work type from job description."""
        if not description:
            return ''
        
        description_lower = description.lower()
        
        # Check for remote work indicators
        if any(term in description_lower for term in ['remoto', 'remote', 'teletrabajo', 'home office']):
            return 'Remoto'
        elif any(term in description_lower for term in ['híbrido', 'hybrid', 'mixto']):
            return 'Híbrido'
        elif any(term in description_lower for term in ['presencial', 'on-site', 'oficina']):
            return 'Presencial'
        else:
            return ''

    def clean_html(self, html_text: str) -> str:
        """Clean HTML tags from text while preserving line breaks."""
        if not html_text:
            return ''
        
        # Replace common HTML tags with appropriate text
        html_text = re.sub(r'<br\s*/?>', '\n', html_text, flags=re.IGNORECASE)
        html_text = re.sub(r'<p[^>]*>', '\n', html_text, flags=re.IGNORECASE)
        html_text = re.sub(r'</p>', '\n', html_text, flags=re.IGNORECASE)
        html_text = re.sub(r'<[^>]+>', '', html_text)
        
        # Clean up extra whitespace and line breaks
        html_text = re.sub(r'\n\s*\n', '\n\n', html_text)
        html_text = html_text.strip()
        
        return html_text

    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse date from various formats to ISO format."""
        if not date_string:
            return None
        
        try:
            # If it's already in ISO format (YYYY-MM-DD)
            if re.match(r'^\d{4}-\d{2}-\d{2}$', date_string):
                return date_string
            
            # Try to parse other formats
            # Add more date parsing logic here if needed
            # For now, return as is if it's a valid date string
            return date_string
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return None
