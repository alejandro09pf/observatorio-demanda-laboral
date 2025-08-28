"""
Computrabajo spider for Labor Market Observatory.
Scrapes job postings from co.computrabajo.com using static listing pages
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

class ComputrabajoSpider(BaseSpider):
    """Spider for Computrabajo Colombia using static listing pages."""
    
    name = "computrabajo"
    allowed_domains = ["co.computrabajo.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "computrabajo"
        
        # Get keyword and city parameters
        self.keyword = kwargs.get('keyword', 'sistemas')
        self.city = kwargs.get('city', 'bogota-dc')
        
        # Build start URL using SEO-friendly format
        if self.country == "CO":
            self.start_url = f"https://co.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        elif self.country == "MX":
            self.start_url = f"https://mx.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        elif self.country == "AR":
            self.start_url = f"https://ar.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        else:
            # Default to Colombia
            self.start_url = f"https://co.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 1.5,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
            'ROBOTSTXT_OBEY': False,  # Disable robots.txt for anti-bot protection
            'DOWNLOADER_MIDDLEWARES': {
                'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
            }
        })
    
    def start_requests(self):
        """Start with the first page."""
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_search_results,
            meta={'page': 1},
            headers=self.get_headers()
        )
    
    def get_headers(self):
        """Get headers to avoid anti-bot detection."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def parse_search_results(self, response):
        """Parse search results page."""
        logger.info(f"Parsing search results: {response.url}")
        
        # Extract job listings using structural selectors
        job_cards = response.css("article")
        
        if not job_cards:
            logger.warning("No job cards found on page")
            return
        
        logger.info(f"Found {len(job_cards)} job cards")
        
        for i, job_card in enumerate(job_cards):
            try:
                # Extract job URL from article h2 a
                job_url = job_card.css("h2 a::attr(href)").get()
                if not job_url:
                    continue
                
                job_url = self.build_absolute_url(job_url, response.url)
                
                # Extract basic info from listing for fallback
                title = job_card.css("h2 a::text").get()
                # Company is actually in the first paragraph (location field)
                company = job_card.css("p:nth-of-type(1)::text").get()
                # Location is actually in the second paragraph (salary field)
                location = job_card.css("p:nth-of-type(2)::text").get()
                # Salary might be in a different field or not available
                salary_raw = job_card.css("p:nth-of-type(3)::text").get()
                posted_date = job_card.css("p:last-of-type::text").get()
                
                # Follow job detail page
                yield scrapy.Request(
                    url=job_url,
                    callback=self.parse_job,
                    meta={
                        'job_card': job_card,
                        'listing_title': title,
                        'listing_company': company,
                        'listing_location': location,
                        'listing_salary': salary_raw,
                        'listing_date': posted_date
                    },
                    headers=self.get_headers()
                )
                
                # Log progress
                self.log_progress(i + 1, len(job_cards))
                
            except Exception as e:
                logger.error(f"Error processing job card {i}: {e}")
                continue
        
        # Handle pagination - go up to 5 pages
        current_page = response.meta.get('page', 1)
        if current_page < 5:
            next_page = current_page + 1
            next_url = f"{self.start_url}?p={next_page}"
            
            logger.info(f"Following pagination to page {next_page}: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={'page': next_page},
                headers=self.get_headers()
            )
    
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
            
            # Extract title from h1
            title = response.css("h1::text").get()
            if not title:
                # Fallback to listing title
                title = response.meta.get('listing_title', '')
            item['title'] = self.clean_text(title) if title else ""
            
            # Extract company from h1 + p (split on "–")
            company_line = response.css("h1 + p::text").get()
            if company_line:
                # Split on "–" to separate company and location
                parts = company_line.split('–')
                if len(parts) >= 2:
                    company = parts[0].strip()
                    location = parts[1].strip()
                else:
                    company = company_line.strip()
                    location = ""
            else:
                # Fallback to listing data
                company = response.meta.get('listing_company', '')
                location = response.meta.get('listing_location', '')
            
            item['company'] = self.clean_text(company) if company else ""
            item['location'] = self.clean_text(location) if location else ""
            
            # Extract description from h3:contains("Descripción de la oferta") + p tags
            description_parts = []
            
            # Find the description section
            desc_section = response.xpath("//h3[contains(text(), 'Descripción de la oferta')]")
            if desc_section:
                # Get all p tags following the description heading
                desc_paragraphs = desc_section.xpath("following-sibling::p[following-sibling::h3 or not(following-sibling::h3)]")
                for p in desc_paragraphs:
                    text = p.get()
                    if text:
                        description_parts.append(self.clean_text(text))
            
            # If no structured description found, try alternative selectors
            if not description_parts:
                desc_selectors = [
                    ".description::text",
                    ".job-description::text",
                    ".content-description::text",
                    "div[class*='description']::text"
                ]
                
                for selector in desc_selectors:
                    text = response.css(selector).get()
                    if text:
                        description_parts.append(self.clean_text(text))
            
            item['description'] = " ".join(description_parts) if description_parts else ""
            
            # Extract requirements from h3:contains("Requerimientos") + ul li
            requirements_parts = []
            
            req_section = response.xpath("//h3[contains(text(), 'Requerimientos')]")
            if req_section:
                req_items = req_section.xpath("following-sibling::ul[1]/li/text()").getall()
                for item_text in req_items:
                    if item_text:
                        requirements_parts.append(self.clean_text(item_text))
            
            # If no structured requirements found, try alternative selectors
            if not requirements_parts:
                req_selectors = [
                    ".requirements::text",
                    ".skills::text",
                    ".profile::text",
                    "div[class*='requirements']::text"
                ]
                
                for selector in req_selectors:
                    text = response.css(selector).get()
                    if text:
                        requirements_parts.append(self.clean_text(text))
            
            item['requirements'] = " ".join(requirements_parts) if requirements_parts else ""
            
            # Extract salary from h3:contains("Descripción de la oferta") + p or fallback
            salary_raw = ""
            
            if desc_section:
                salary_p = desc_section.xpath("following-sibling::p[1]/text()").get()
                if salary_p:
                    salary_raw = self.clean_text(salary_p)
            
            # If no salary found, use fallback from listing
            if not salary_raw:
                salary_raw = response.meta.get('listing_salary', '')
            
            item['salary_raw'] = self.clean_text(salary_raw) if salary_raw else ""
            
            # Extract contract type and remote type from salary_raw or description
            contract_type = self.extract_contract_from_text(item['salary_raw'] + " " + item['description'])
            item['contract_type'] = contract_type
            
            remote_type = self.extract_remote_from_text(item['salary_raw'] + " " + item['description'])
            item['remote_type'] = remote_type
            
            # Extract posted date from p:contains("Hace") or fallback
            posted_date = ""
            
            date_elements = response.xpath("//p[contains(text(), 'Hace')]/text()").getall()
            for date_elem in date_elements:
                if 'hace' in date_elem.lower():
                    posted_date = date_elem.strip()
                    break
            
            # If no date found, use fallback from listing
            if not posted_date:
                posted_date = response.meta.get('listing_date', '')
            
            item['posted_date'] = self.parse_date(posted_date) if posted_date else None
            
            # Validate item
            if not self.validate_job_item(item):
                logger.warning(f"Invalid job item: {item.get('title', 'No title')}")
                return
            
            logger.info(f"Successfully parsed job: {item.get('title', 'No title')}")
            yield item
            
        except Exception as e:
            logger.error(f"Error parsing job {response.url}: {e}")
            return
    
    def extract_contract_from_text(self, text: str) -> str:
        """Extract contract type from text heuristically."""
        if not text:
            return ""
        
        # Look for contract type keywords
        contract_keywords = {
            'tiempo completo': 'Tiempo completo',
            'tiempo parcial': 'Tiempo parcial',
            'contrato': 'Contrato',
            'permanente': 'Permanente',
            'temporal': 'Temporal',
            'indefinido': 'Indefinido',
            'determinado': 'Determinado',
            'freelance': 'Freelance',
            'independiente': 'Independiente',
            'plazo fijo': 'Plazo fijo',
            'obra labor': 'Obra labor'
        }
        
        text_lower = text.lower()
        for keyword, value in contract_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
    
    def extract_remote_from_text(self, text: str) -> str:
        """Extract remote work type from text heuristically."""
        if not text:
            return ""
        
        # Look for remote work keywords
        remote_keywords = {
            'remoto': 'Remoto',
            'teletrabajo': 'Remoto',
            'home office': 'Remoto',
            'presencial': 'Presencial',
            'híbrido': 'Híbrido',
            'hibrido': 'Híbrido',
            'mixto': 'Híbrido',
            'a distancia': 'Remoto'
        }
        
        text_lower = text.lower()
        for keyword, value in remote_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse Computrabajo date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in Computrabajo
            date_patterns = [
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'hace (\d+) semanas?',  # "hace X semanas"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'hace' in pattern:
                        # Handle relative dates - return today's date
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
            
