"""
Bumeran spider for Labor Market Observatory.
Scrapes job postings from bumeran.com
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional
import logging
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import json

logger = logging.getLogger(__name__)

class BumeranSpider(BaseSpider):
    """Spider for Bumeran job portal."""
    
    name = "bumeran"
    allowed_domains = ["bumeran.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "bumeran"
        
        # Set start URLs based on country with specific job categories
        if self.country == "CO":
            self.start_urls = [
                "https://www.bumeran.com.co/empleos",
                "https://www.bumeran.com.co/empleos/sistemas-y-tecnologia",
                "https://www.bumeran.com.co/empleos/administracion",
                "https://www.bumeran.com.co/empleos/ventas"
            ]
        elif self.country == "MX":
            self.start_urls = [
                "https://www.bumeran.com.mx/empleos",
                "https://www.bumeran.com.mx/empleos/sistemas-y-tecnologia",
                "https://www.bumeran.com.mx/empleos/administracion",
                "https://www.bumeran.com.mx/empleos/ventas"
            ]
        elif self.country == "AR":
            self.start_urls = [
                "https://www.bumeran.com.ar/empleos",
                "https://www.bumeran.com.ar/empleos/sistemas-y-tecnologia",
                "https://www.bumeran.com.ar/empleos/administracion",
                "https://www.bumeran.com.ar/empleos/ventas"
            ]
        elif self.country == "CL":
            self.start_urls = [
                "https://www.bumeran.cl/empleos",
                "https://www.bumeran.cl/empleos/sistemas-y-tecnologia"
            ]
        elif self.country == "PE":
            self.start_urls = [
                "https://www.bumeran.com.pe/empleos",
                "https://www.bumeran.com.pe/empleos/sistemas-y-tecnologia"
            ]
        elif self.country == "EC":
            self.start_urls = [
                "https://www.bumeran.com.ec/empleos",
                "https://www.bumeran.com.ec/empleos/sistemas-y-tecnologia"
            ]
        elif self.country == "PA":
            self.start_urls = [
                "https://www.bumeran.com.pa/empleos",
                "https://www.bumeran.com.pa/empleos/sistemas-y-tecnologia"
            ]
        elif self.country == "UY":
            self.start_urls = [
                "https://www.bumeran.com.uy/empleos",
                "https://www.bumeran.com.uy/empleos/sistemas-y-tecnologia"
            ]
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        })
        
        # Selenium setup
        self.driver = None
        self.wait_timeout = 15
        self.page_load_timeout = 30
        self.scraped_urls = set()
        
        # Set start URL for search functionality - use the correct URL that works
        self.start_url = "https://www.bumeran.com.mx/empleos.html"
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Anti-detection flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.set_page_load_timeout(self.page_load_timeout)
            return True
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            return False
    
    def start_requests(self):
        """Start requests by initializing Selenium and navigating to the start URL."""
        if not self.setup_driver():
            logger.error("Failed to setup Selenium driver")
            return
        
        logger.info(f"Starting Bumeran spider for country: {self.country}")
        logger.info(f"Start URL: {self.start_url}")
        
        # Navigate to start URL
        try:
            self.driver.get(self.start_url)
            time.sleep(5)  # Wait for initial load
            
            # Start scraping from page 1
            for item in self.parse_search_results_page(1):
                yield item
            
        except Exception as e:
            logger.error(f"Error navigating to start URL: {e}")
            self.cleanup_driver()
    
    def cleanup_driver(self):
        """Clean up Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error quitting driver: {e}")
            finally:
                self.driver = None
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.cleanup_driver()
        self.save_scraping_summary()
    
    def save_scraping_summary(self):
        """Save scraping summary to JSON file."""
        summary = {
            "spider": self.name,
            "country": self.country,
            "start_time": getattr(self, 'start_time', None),
            "end_time": datetime.now().isoformat(),
            "total_jobs_scraped": len(self.scraped_urls),
            "scraped_urls": list(self.scraped_urls)
        }
        
        try:
            with open(f"outputs/bumeran_scraping_summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Scraping summary saved to outputs/bumeran_scraping_summary.json")
        except Exception as e:
            logger.error(f"Error saving scraping summary: {e}")
    
    def parse_search_results_page(self, page):
        """Parse search results page using Selenium."""
        logger.info(f"Parsing search results page {page}")
        
        try:
            # Navigate to the page
            if page == 1:
                url = self.start_url
            else:
                url = f"{self.start_url}?page={page}"
            
            self.driver.get(url)
            time.sleep(5)  # Wait for page load
            
            # If this is page 1 and no job cards found, try to perform a search
            if page == 1:
                logger.info("Attempting to perform search to find job listings...")
                if self.perform_search():
                    time.sleep(5)  # Wait for search results to load
            
            # Wait for content to load
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            # Find job links directly - simpler approach based on actual site structure
            job_links = []
            
            # First try to find all links with job-related hrefs
            all_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo']")
            logger.info(f"Found {len(all_links)} total links with 'empleo'")
            
            # Filter for actual job postings
            for link in all_links:
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    
                    # Skip navigation/filter links
                    if any(nav_pattern in href for nav_pattern in [
                        'seniority-', 'landing-', 'relevantes=true', 'recientes=true',
                        'empleos-seniority-', 'empleos.html?', 'page='
                    ]):
                        continue
                    
                    # Only include actual job postings
                    if (href.endswith('.html') and 
                        '/empleos/' in href and 
                        len(text) > 10 and
                        not href.endswith('empleos.html')):
                        job_links.append(link)
                
                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue
            
            logger.info(f"Found {len(job_links)} actual job postings")
            
            if not job_links:
                logger.warning(f"No job links found on page {page}")
                return
            
            # Process job links
            job_data_list = []
            for i, job_link in enumerate(job_links):
                try:
                    # Extract job URL and title directly from the link
                    job_url = job_link.get_attribute('href')
                    job_title = job_link.text.strip()
                    
                    if not job_url or not job_title:
                        continue
                    
                    # Skip if already scraped
                    if job_url in self.scraped_urls:
                        continue
                    
                    # Extract basic info from the link text (which contains the job info)
                    # The link text contains: "Publicado X días\nJob Title\nCompany\nDescription..."
                    lines = job_title.split('\n')
                    
                    # Extract company and location from the text
                    company = ""
                    location = ""
                    description = ""
                    
                    if len(lines) >= 3:
                        # Skip the first line (posted date)
                        job_title_clean = lines[1] if len(lines) > 1 else job_title
                        company = lines[2] if len(lines) > 2 else ""
                        
                        # Look for location in the text (usually at the end)
                        for line in lines:
                            if any(loc_indicator in line.lower() for loc_indicator in ['mexico', 'cdmx', 'distrito federal', 'estado de mexico', 'jalisco', 'nuevo leon']):
                                location = line.strip()
                                break
                        
                        # Description is usually the longer text
                        description_lines = [line for line in lines if len(line) > 50]
                        if description_lines:
                            description = description_lines[0][:200] + "..." if len(description_lines[0]) > 200 else description_lines[0]
                    
                    job_data = {
                        'url': job_url,
                        'title': job_title_clean if 'job_title_clean' in locals() else job_title,
                        'company': company,
                        'location': location,
                        'description': description
                    }
                    
                    job_data_list.append(job_data)
                    self.scraped_urls.add(job_url)
                    
                except Exception as e:
                    logger.error(f"Error processing job card {i}: {e}")
                    continue
            
            # Process each job to get detailed information
            for job_data in job_data_list:
                try:
                    detailed_job = self.get_job_details(job_data['url'])
                    if detailed_job:
                        # Merge basic and detailed info
                        job_data.update(detailed_job)
                        
                        # Create JobItem
                        item = JobItem()
                        item['portal'] = 'bumeran'
                        item['country'] = self.country
                        item['url'] = job_data['url']
                        item['title'] = job_data.get('title', '')
                        item['company'] = job_data.get('company', '')
                        item['location'] = job_data.get('location', '')
                        item['description'] = job_data.get('description', '')
                        item['requirements'] = job_data.get('requirements', '')
                        item['salary_raw'] = job_data.get('salary_raw', '')
                        item['contract_type'] = job_data.get('contract_type', '')
                        item['remote_type'] = job_data.get('remote_type', '')
                        item['posted_date'] = job_data.get('posted_date')
                        
                        # Validate item
                        if self.validate_job_item(item):
                            yield item
                        else:
                            logger.warning(f"Invalid job item: {item['title']}")
                    
                except Exception as e:
                    logger.error(f"Error getting job details for {job_data['url']}: {e}")
                    continue
            
            # Check for next page
            if page < self.max_pages:
                next_page = page + 1
                logger.info(f"Moving to page {next_page}")
                for item in self.parse_search_results_page(next_page):
                    yield item
            
        except Exception as e:
            logger.error(f"Error parsing search results page {page}: {e}")
    
    def perform_search(self):
        """Perform a search to find job listings."""
        try:
            logger.info("Looking for search input...")
            
            # Look for search input
            search_selectors = [
                "input[type='text']",
                "input[placeholder*='empleo']",
                "input[placeholder*='trabajo']",
                "input[placeholder*='puesto']",
                "input[placeholder*='buscar']",
                ".search-input",
                "#busqueda",
                "input"
            ]
            
            search_input = None
            for selector in search_selectors:
                try:
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if inputs:
                        for inp in inputs:
                            try:
                                placeholder = inp.get_attribute('placeholder')
                                if placeholder and any(keyword in placeholder.lower() for keyword in ['empleo', 'trabajo', 'puesto', 'buscar']):
                                    search_input = inp
                                    logger.info(f"Found search input: {placeholder}")
                                    break
                            except:
                                continue
                        if search_input:
                            break
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue
            
            if not search_input:
                logger.warning("No search input found")
                return False
            
            # Perform search
            try:
                # Clear the input
                search_input.clear()
                time.sleep(1)
                
                # Type a search term
                search_term = "desarrollador"
                search_input.send_keys(search_term)
                logger.info(f"Typed search term: {search_term}")
                time.sleep(2)
                
                # Press Enter to search
                from selenium.webdriver.common.keys import Keys
                search_input.send_keys(Keys.RETURN)
                logger.info("Pressed Enter to search")
                time.sleep(5)
                
                # Check if URL changed
                logger.info(f"URL after search: {self.driver.current_url}")
                return True
                
            except Exception as e:
                logger.error(f"Error performing search: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Error in perform_search: {e}")
            return False
    
    def extract_company_from_card(self, job_card):
        """Extract company name from job card."""
        company_selectors = [
            "div:nth-of-type(2) span",
            "a[href*='/empresas/']",
            ".company",
            ".employer",
            "span[class*='company']",
            "span"
        ]
        
        for selector in company_selectors:
            try:
                company_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                company_text = company_elem.text.strip()
                if company_text and len(company_text) > 2:
                    return company_text
            except NoSuchElementException:
                continue
        
        return ""
    
    def extract_location_from_card(self, job_card):
        """Extract location from job card."""
        location_selectors = [
            "[aria-label='location']",
            ".location",
            ".place",
            ".city",
            "span[class*='location']",
            "span"
        ]
        
        for selector in location_selectors:
            try:
                location_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                location_text = location_elem.text.strip()
                if location_text and len(location_text) > 2:
                    return location_text
            except NoSuchElementException:
                continue
        
        return ""
    
    def extract_description_from_card(self, job_card):
        """Extract description from job card."""
        desc_selectors = [
            "p",
            ".description",
            ".summary",
            "div[class*='description']"
        ]
        
        for selector in desc_selectors:
            try:
                desc_elem = job_card.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if desc_text and len(desc_text) > 20:
                    return desc_text
            except NoSuchElementException:
                continue
        
        return ""
    
    def get_job_details(self, job_url):
        """Get detailed job information from job detail page."""
        try:
            logger.info(f"Getting job details: {job_url}")
            
            self.driver.get(job_url)
            time.sleep(3)  # Wait for page load
            
            job_details = {}
            
            # Extract title
            title_selectors = ["h1", ".job-title", ".title"]
            for selector in title_selectors:
                try:
                    title_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['title'] = title_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract company
            company_selectors = ["h1 + div span", ".company", ".employer"]
            for selector in company_selectors:
                try:
                    company_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['company'] = company_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract posted date
            date_selectors = ["time", "span[aria-label='Publicado']", ".date", ".posted"]
            for selector in date_selectors:
                try:
                    date_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    date_text = date_elem.text.strip()
                    job_details['posted_date'] = self.parse_date(date_text)
                    break
                except NoSuchElementException:
                    continue
            
            # Extract location
            location_selectors = ["div[aria-label='location']", ".location", ".place"]
            for selector in location_selectors:
                try:
                    location_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['location'] = location_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract description
            desc_selectors = [
                ".description",
                ".job-description",
                "div[class*='description']",
                "section h2 + div",
                "div[class*='desc']"
            ]
            for selector in desc_selectors:
                try:
                    desc_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['description'] = desc_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract requirements
            req_selectors = [
                ".requirements",
                ".skills",
                "section h2 + ul",
                "ul[class*='requirement']",
                "ul[class*='skill']"
            ]
            requirements_parts = []
            for selector in req_selectors:
                try:
                    req_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    requirements_parts.append(req_elem.text.strip())
                except NoSuchElementException:
                    continue
            
            if requirements_parts:
                job_details['requirements'] = " ".join(requirements_parts)
            
            # Extract contract type
            contract_selectors = [
                ".contract-type",
                ".type",
                "section li",
                "li[class*='contract']",
                "li[class*='type']"
            ]
            for selector in contract_selectors:
                try:
                    contract_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['contract_type'] = contract_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            # Extract remote type
            remote_selectors = [
                ".remote",
                ".modality",
                "section li",
                "li[class*='remote']",
                "li[class*='modality']"
            ]
            for selector in remote_selectors:
                try:
                    remote_elem = self.driver.find_element(By.CSS_SELECTOR, selector)
                    job_details['remote_type'] = remote_elem.text.strip()
                    break
                except NoSuchElementException:
                    continue
            
            return job_details
            
        except Exception as e:
            logger.error(f"Error getting job details from {job_url}: {e}")
            return None
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse Bumeran date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in Bumeran
            date_patterns = [
                r'Publicado (\d{1,2}) (\w+) (\d{4})',  # "Publicado 23 Ago 2025"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'(\d{1,2}) (\w+) (\d{4})',  # "23 Ago 2025"
                r'(\d{1,2}) de (\w+) de (\d{4})',  # "23 de Agosto de 2025"
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
