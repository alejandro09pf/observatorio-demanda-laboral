"""
ZonaJobs spider for Labor Market Observatory.
Scrapes job postings from zonajobs.com.ar
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ZonaJobsSpider(BaseSpider):
    """Spider for ZonaJobs job portal."""
    
    name = "zonajobs"
    allowed_domains = ["zonajobs.com.ar"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "zonajobs"
        
        # Set start URLs based on country with specific job categories
        if self.country == "AR":
            self.start_urls = [
                "https://www.zonajobs.com.ar/empleos",
                "https://www.zonajobs.com.ar/empleos/sistemas-y-tecnologia",
                "https://www.zonajobs.com.ar/empleos/administracion",
                "https://www.zonajobs.com.ar/empleos/ventas",
                "https://www.zonajobs.com.ar/empleos/ingenieria"
            ]
        elif self.country == "CO":
            # ZonaJobs Colombia (if available)
            self.start_urls = [
                "https://co.zonajobs.com/empleos",
                "https://co.zonajobs.com/empleos/sistemas-y-tecnologia"
            ]
        elif self.country == "MX":
            # ZonaJobs Mexico (if available)
            self.start_urls = [
                "https://mx.zonajobs.com/empleos",
                "https://mx.zonajobs.com/empleos/sistemas-y-tecnologia"
            ]
        else:
            # Default to Argentina
            self.start_urls = [
                "https://www.zonajobs.com.ar/empleos",
                "https://www.zonajobs.com.ar/empleos/sistemas-y-tecnologia"
            ]
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        })
    
    def parse_search_results(self, response):
        """Parse search results page."""
        logger.info(f"Parsing search results: {response.url}")
        
        # Extract job listings - ZonaJobs specific selectors
        # ZonaJobs typically uses cards with job information
        job_cards = response.css("div[class*='job-card'], article[class*='job-item'], div[class*='offer'], .job-listing, .job-result")
        
        if not job_cards:
            # Try alternative selectors for ZonaJobs structure
            job_cards = response.css("div:has(h2), article:has(h2), .job-card, .job-item")
            logger.info(f"Trying alternative selectors, found {len(job_cards)} cards")
        
        if not job_cards:
            # Try more generic selectors
            job_cards = response.css("div[class*='card'], div[class*='item'], div[class*='listing']")
            logger.info(f"Trying generic selectors, found {len(job_cards)} cards")
        
        if not job_cards:
            logger.warning("No job cards found on page")
            return
        
        logger.info(f"Found {len(job_cards)} job cards")
        
        for i, job_card in enumerate(job_cards):
            try:
                # Extract job URL - ZonaJobs specific patterns
                job_url = (
                    job_card.css("h2 a::attr(href)").get() or
                    job_card.css("a[href*='/empleo/']::attr(href)").get() or
                    job_card.css("a[href*='/trabajo/']::attr(href)").get() or
                    job_card.css("a[href*='/job/']::attr(href)").get() or
                    job_card.css("a[href*='/oferta/']::attr(href)").get() or
                    job_card.css("a::attr(href)").get()
                )
                
                if not job_url:
                    continue
                
                job_url = self.build_absolute_url(job_url, response.url)
                
                # Skip if not a job detail URL
                if not any(keyword in job_url for keyword in ['/empleo/', '/trabajo/', '/job/', '/oferta/', '/puesto/']):
                    continue
                
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
        
        # Handle pagination - ZonaJobs specific patterns
        # Look for pagination links, "Siguiente" button, or page parameters
        next_page = self.handle_pagination(response, "a[rel='next']::attr(href), a:contains('Siguiente')::attr(href), .pagination a:last-child::attr(href), a[href*='page=']::attr(href)")
        if next_page:
            yield next_page
    
    def parse_job(self, response):
        """Parse individual job posting."""
        try:
            logger.info(f"Parsing job: {response.url}")
            
            # Create job item
            item = JobItem()
            
            # Basic information
            item['portal'] = 'zonajobs'
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract title - ZonaJobs specific selectors
            title_selectors = [
                "h1::text",
                "h1.job-title::text",
                ".job-title::text",
                "h2::text",
                ".title::text",
                ".job-name::text",
                ".position-title::text",
                "h1[class*='title']::text"
            ]
            
            title = None
            for selector in title_selectors:
                title = response.css(selector).get()
                if title:
                    break
            
            item['title'] = self.clean_text(title) if title else ""
            
            # Extract company - ZonaJobs specific selectors
            company_selectors = [
                ".company-name::text",
                ".company::text",
                ".employer::text",
                "span:contains('Empresa') + span::text",
                ".business-name::text",
                ".company-info::text",
                ".employer-name::text",
                "div[class*='company']::text"
            ]
            
            company = None
            for selector in company_selectors:
                company = response.css(selector).get()
                if company:
                    break
            
            item['company'] = self.clean_text(company) if company else ""
            
            # Extract location - ZonaJobs specific selectors
            location_selectors = [
                ".location::text",
                ".place::text",
                ".city::text",
                "span:contains('Ubicación') + span::text",
                ".job-location::text",
                ".location-info::text",
                ".place-info::text",
                "div[class*='location']::text"
            ]
            
            location = None
            for selector in location_selectors:
                location = response.css(selector).get()
                if location:
                    break
            
            item['location'] = self.clean_text(location) if location else ""
            
            # Extract description - ZonaJobs specific selectors
            description_selectors = [
                ".description::text",
                ".job-description::text",
                ".content-description::text",
                ".offer-description::text",
                "div[class*='description']::text",
                "div[class*='content']::text",
                ".job-details::text",
                ".job-content::text",
                "div[class*='job-details']::text"
            ]
            
            description_parts = []
            for selector in description_selectors:
                text = response.css(selector).get()
                if text:
                    description_parts.append(self.clean_text(text))
            
            # If no specific description found, try to get all text content
            if not description_parts:
                all_text = response.css("body *::text").getall()
                description_parts = [self.clean_text(text) for text in all_text if text.strip()]
            
            item['description'] = " ".join(description_parts) if description_parts else ""
            
            # Extract requirements - ZonaJobs specific selectors
            requirements_selectors = [
                ".requirements::text",
                ".skills::text",
                ".profile::text",
                ".qualifications::text",
                "div:contains('Requisitos') *::text",
                "div:contains('Perfil') *::text",
                ".job-requirements::text",
                ".requirements-list::text",
                "div[class*='requirements']::text"
            ]
            
            requirements_parts = []
            for selector in requirements_selectors:
                text = response.css(selector).get()
                if text:
                    requirements_parts.append(self.clean_text(text))
            
            item['requirements'] = " ".join(requirements_parts) if requirements_parts else ""
            
            # Extract salary - ZonaJobs specific selectors
            salary_selectors = [
                ".salary::text",
                ".wage::text",
                ".payment::text",
                "span:contains('Salario') + span::text",
                ".job-salary::text",
                ".salary-info::text",
                ".compensation::text",
                "div[class*='salary']::text"
            ]
            
            salary = None
            for selector in salary_selectors:
                salary = response.css(selector).get()
                if salary:
                    break
            
            item['salary_raw'] = self.clean_text(salary) if salary else ""
            
            # Extract contract type - ZonaJobs specific selectors
            contract_selectors = [
                ".contract-type::text",
                ".type::text",
                ".contract::text",
                "span:contains('Tipo de contrato') + span::text",
                ".job-type::text",
                ".employment-type::text",
                "div[class*='contract']::text"
            ]
            
            contract_type = None
            for selector in contract_selectors:
                contract_type = response.css(selector).get()
                if contract_type:
                    break
            
            item['contract_type'] = self.clean_text(contract_type) if contract_type else ""
            
            # Extract remote type - ZonaJobs specific selectors
            remote_selectors = [
                ".remote::text",
                ".work-mode::text",
                ".modality::text",
                "span:contains('Modalidad') + span::text",
                "span:contains('Trabajo') + span::text",
                ".work-type::text",
                ".work-mode-info::text",
                "div[class*='remote']::text"
            ]
            
            remote_info = None
            for selector in remote_selectors:
                remote_info = response.css(selector).get()
                if remote_info:
                    break
            
            item['remote_type'] = self.clean_text(remote_info) if remote_info else ""
            
            # Extract posted date - ZonaJobs specific selectors
            date_selectors = [
                ".date::text",
                ".posted::text",
                ".publication-date::text",
                "span:contains('Publicado') + span::text",
                ".job-date::text",
                ".posting-date::text",
                ".date-info::text",
                "div[class*='date']::text"
            ]
            
            date_text = None
            for selector in date_selectors:
                date_text = response.css(selector).get()
                if date_text:
                    break
            
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
        """Parse ZonaJobs date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in ZonaJobs
            date_patterns = [
                r'Publicado (\d{1,2}) (\w+) (\d{4})',  # "Publicado 23 Ago 2025"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'(\d{1,2}) (\w+) (\d{4})',  # "23 Ago 2025"
                r'(\d{1,2}) de (\w+) de (\d{4})',  # "23 de Agosto de 2025"
                r'(\d{1,2})/(\d{1,2})/(\d{2})',  # DD/MM/YY
            ]
            
            # Spanish month mappings
            month_map = {
                'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12',
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'hace' in pattern:
                        # Handle relative dates
                        return datetime.today().date().isoformat()
                    elif len(match.groups()) == 3:
                        # Handle absolute dates
                        if pattern == r'Publicado (\d{1,2}) (\w+) (\d{4})':
                            day, month, year = match.groups()
                        elif pattern == r'(\d{1,2}) (\w+) (\d{4})':
                            day, month, year = match.groups()
                        elif pattern == r'(\d{1,2}) de (\w+) de (\d{4})':
                            day, month, year = match.groups()
                        elif pattern == r'(\d{1,2})/(\d{1,2})/(\d{2})':
                            day, month, year = match.groups()
                            # Convert 2-digit year to 4-digit
                            year = f"20{year}" if int(year) < 50 else f"19{year}"
                        else:
                            day, month, year = match.groups()
                        
                        # Convert month name to number
                        month_lower = month.lower()[:3]
                        if month_lower in month_map:
                            month_num = month_map[month_lower]
                            return f"{year}-{month_num}-{day.zfill(2)}"
            
            # If no pattern matches, return today's date
            return datetime.today().date().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return datetime.today().date().isoformat()
