"""
Computrabajo spider for Labor Market Observatory.
Scrapes job postings from computrabajo.com.co
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional

class ComputrabajoSpider(BaseSpider):
    """Spider for Computrabajo Colombia."""
    
    name = "computrabajo"
    allowed_domains = ["computrabajo.com.co"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set start URLs based on country
        if self.country == "CO":
            self.start_urls = [
                "https://co.computrabajo.com/trabajo-de-programador",
                "https://co.computrabajo.com/trabajo-de-desarrollador",
                "https://co.computrabajo.com/trabajo-de-ingeniero-sistemas",
                "https://co.computrabajo.com/trabajo-de-analista-programador"
            ]
        elif self.country == "MX":
            self.start_urls = [
                "https://mx.computrabajo.com/trabajo-de-programador",
                "https://mx.computrabajo.com/trabajo-de-desarrollador"
            ]
        elif self.country == "AR":
            self.start_urls = [
                "https://ar.computrabajo.com/trabajo-de-programador",
                "https://ar.computrabajo.com/trabajo-de-desarrollador"
            ]
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        })
    
    def parse_search_results(self, response):
        """Parse search results page."""
        logger.info(f"Parsing search results: {response.url}")
        
        # Extract job listings
        job_cards = response.css("article.box_offer")
        
        if not job_cards:
            logger.warning("No job cards found on page")
            return
        
        logger.info(f"Found {len(job_cards)} job cards")
        
        for i, job_card in enumerate(job_cards):
            try:
                # Extract job URL
                job_url = job_card.css("h2 a::attr(href)").get()
                if not job_url:
                    continue
                
                job_url = self.build_absolute_url(job_url, response.url)
                
                # Follow job detail page
                yield scrapy.Request(
                    url=job_url,
                    callback=self.parse_job,
                    meta={'job_card': job_card}
                )
                
                # Log progress
                self.log_progress(i + 1, len(job_cards))
                
            except Exception as e:
                logger.error(f"Error processing job card {i}: {e}")
                continue
        
        # Handle pagination
        next_page = self.handle_pagination(response, "a[rel='next']::attr(href)")
        if next_page:
            yield next_page
    
    def parse_job(self, response):
        """Parse individual job posting."""
        try:
            logger.info(f"Parsing job: {response.url}")
            
            # Create job item
            item = JobItem()
            
            # Basic information
            item['portal'] = 'computrabajo'
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract title
            title = response.css("h1::text").get()
            item['title'] = self.clean_text(title) if title else ""
            
            # Extract company
            company = response.css(".company-name::text, .company::text").get()
            item['company'] = self.clean_text(company) if company else ""
            
            # Extract location
            location = response.css(".location::text, .place::text").get()
            item['location'] = self.clean_text(location) if location else ""
            
            # Extract description
            description_selectors = [
                ".description::text",
                ".job-description::text",
                ".content-description::text"
            ]
            
            description_parts = []
            for selector in description_selectors:
                text = response.css(selector).get()
                if text:
                    description_parts.append(self.clean_text(text))
            
            item['description'] = " ".join(description_parts) if description_parts else ""
            
            # Extract requirements
            requirements_selectors = [
                ".requirements::text",
                ".skills::text",
                ".profile::text"
            ]
            
            requirements_parts = []
            for selector in requirements_selectors:
                text = response.css(selector).get()
                if text:
                    requirements_parts.append(self.clean_text(text))
            
            item['requirements'] = " ".join(requirements_parts) if requirements_parts else ""
            
            # Extract salary
            salary = response.css(".salary::text, .wage::text").get()
            item['salary_raw'] = self.clean_text(salary) if salary else ""
            
            # Extract contract type
            contract_type = response.css(".contract-type::text, .type::text").get()
            item['contract_type'] = self.clean_text(contract_type) if contract_type else ""
            
            # Extract remote type
            remote_info = response.css(".remote::text, .work-mode::text").get()
            item['remote_type'] = self.clean_text(remote_info) if remote_info else ""
            
            # Extract posted date
            date_text = response.css(".date::text, .posted::text").get()
            item['posted_date'] = self.parse_date(date_text) if date_text else None
            
            # Validate item
            if not self.validate_job_item(item):
                logger.warning(f"Invalid job item: {item['title']}")
                return
            
            # Clean and normalize all text fields
            for field in ['title', 'company', 'location', 'description', 'requirements']:
                if item.get(field):
                    item[field] = self.clean_text(item[field])
            
            logger.info(f"Successfully parsed job: {item['title']}")
            yield item
            
        except Exception as e:
            logger.error(f"Error parsing job {response.url}: {e}")
            return
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse Computrabajo date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in Computrabajo
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'hace' in pattern:
                        # Handle relative dates
                        return datetime.today().date().isoformat()
                    else:
                        # Handle absolute dates
                        day, month, year = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # If no pattern matches, return today's date
            return datetime.today().date().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return datetime.today().date().isoformat()
