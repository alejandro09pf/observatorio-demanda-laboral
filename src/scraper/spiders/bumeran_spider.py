"""
Bumeran spider for Labor Market Observatory.
Scrapes job listings from https://www.bumeran.com.mx/empleos.html using Selenium for React rendering.
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
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

logger = logging.getLogger(__name__)

class BumeranSpider(BaseSpider):
    """Spider for Bumeran job portal - Mexico jobs."""
    
    name = "bumeran"
    allowed_domains = ["bumeran.com.mx"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "bumeran"
        
        # Force Mexico as specified
        self.country = "MX"
        
        # Base URL for Mexico
        self.base_url = "https://www.bumeran.com.mx/empleos.html"
        
        # Selenium setup
        self.driver = None
        self.wait_timeout = 15
        self.page_load_timeout = 30
        self.scraped_urls = set()
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 3,  # Conservative delay to avoid detection
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Single request at a time for Selenium
        })
    
    def setup_driver(self):
        """Setup Chrome WebDriver with advanced anti-detection for Cloudflare bypass."""
        chrome_options = Options()
        
        # Advanced anti-detection options
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins-discovery")
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--allow-running-insecure-content")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-ipc-flooding-protection")
        
        # User agent that looks more human
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Anti-detection flags
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.notifications": 2,
            "profile.managed_default_content_settings.images": 2,
            "profile.default_content_setting_values.media_stream": 2,
        })
        
        # Get proxy from orchestrator
        proxy = self.get_proxy()
        if proxy:
            chrome_options.add_argument(f'--proxy-server={proxy}')
            logger.info(f"Using proxy: {proxy}")
        
        try:
            # Use webdriver-manager for automatic ChromeDriver management
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Execute advanced anti-detection scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['es-MX', 'es', 'en']})")
            self.driver.execute_script("Object.defineProperty(navigator, 'permissions', {get: () => {query: () => Promise.resolve({state: 'granted'})}})")
            self.driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            self.driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
            
            # Set window properties
            self.driver.execute_script("Object.defineProperty(screen, 'width', {get: () => 1920})")
            self.driver.execute_script("Object.defineProperty(screen, 'height', {get: () => 1080})")
            self.driver.execute_script("Object.defineProperty(screen, 'availWidth', {get: () => 1920})")
            self.driver.execute_script("Object.defineProperty(screen, 'availHeight', {get: () => 1040})")
            
            self.driver.set_page_load_timeout(self.page_load_timeout)
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Chrome driver: {e}")
            return False
    
    def get_proxy(self):
        """Get proxy from orchestrator's proxy service."""
        try:
            # This should call your orchestrator's proxy service
            # For now, we'll use the proxy middleware
            return None  # Let middleware handle proxy rotation
        except Exception as e:
            logger.warning(f"Could not get proxy: {e}")
            return None
    
    def start_requests(self):
        """Start requests by initializing Selenium and navigating to the start URL."""
        # Check execution lock BEFORE starting requests
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                f"This spider '{self.__class__.__name__}' can only be executed through the orchestrator.\n"
                f"Use: python -m src.orchestrator run-once {self.__class__.__name__.lower()} --country <COUNTRY>\n"
                f"Or: python -m src.orchestrator run {self.__class__.__name__.lower()} --country <COUNTRY>"
            )
        
        if not self.setup_driver():
            logger.error("Failed to setup Selenium driver")
            return
        
        logger.info(f"Starting Bumeran spider for Mexico")
        logger.info(f"Base URL: {self.base_url}")
        
        # Start scraping from page 1
        for item in self.parse_search_results_page(1):
            yield item
    
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
    
    def parse_search_results_page(self, page):
        """Parse search results page using Selenium."""
        logger.info(f"Parsing search results page {page}")
        
        try:
            # Navigate to the page
            if page == 1:
                url = self.base_url
            else:
                url = f"{self.base_url}?page={page}"
            
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Handle Cloudflare challenge and wait for page to load
            if not self.wait_for_page_load():
                logger.error(f"Failed to load page {page} - Cloudflare protection or timeout")
                return
            
            # Wait for job cards to load
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            try:
                # Wait for article elements (job cards) to appear
                job_cards = wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "article"))
                )
                logger.info(f"Found {len(job_cards)} job cards on page {page}")
                
            except TimeoutException:
                logger.warning(f"No job cards found on page {page} - page may be empty")
                return
            
            if not job_cards:
                logger.warning(f"No job cards found on page {page}")
                return
            
            # Process each job card
            for i, job_card in enumerate(job_cards):
                try:
                    job_data = self.extract_job_from_card(job_card)
                    if job_data and job_data['url'] not in self.scraped_urls:
                        # Mark as scraped
                        self.scraped_urls.add(job_data['url'])
                        
                        # Get detailed job information
                        detailed_job = self.get_job_details(job_data['url'])
                        if detailed_job:
                            # Merge basic and detailed info
                            job_data.update(detailed_job)
                            
                            # Create JobItem
                            item = JobItem()
                            item['portal'] = self.portal
                            item['country'] = self.country
                            item['url'] = job_data['url']
                            item['title'] = job_data.get('title', '')
                            item['company'] = job_data.get('company', '')
                            item['location'] = job_data.get('location', '')
                            item['description'] = job_data.get('description', '')
                            item['requirements'] = job_data.get('requirements', '')
                            item['salary_raw'] = job_data.get('salary_raw', None)
                            item['contract_type'] = job_data.get('contract_type', '')
                            item['remote_type'] = job_data.get('remote_type', '')
                            item['posted_date'] = job_data.get('posted_date')
                            
                            # Validate item
                            if self.validate_job_item(item):
                                yield item
                                logger.info(f"✅ Successfully scraped job: {item['title'][:50]}...")
                            else:
                                logger.warning(f"Invalid job item: {item['title']}")
                        
                except Exception as e:
                    logger.error(f"Error processing job card {i}: {e}")
                    continue
            
            # Check for next page
            if page < self.max_pages:
                next_page = page + 1
                logger.info(f"Moving to page {next_page}")
                for item in self.parse_search_results_page(next_page):
                    yield item
            
        except Exception as e:
            logger.error(f"Error parsing search results page {page}: {e}")
    
    def extract_job_from_card(self, job_card):
        """Extract basic job information from job card."""
        try:
            job_data = {}
            
            # Extract title and URL from article h2 a
            try:
                title_link = job_card.find_element(By.CSS_SELECTOR, "h2 a")
                job_data['title'] = title_link.text.strip()
                job_data['url'] = title_link.get_attribute("href")
            except NoSuchElementException:
                logger.warning("Could not find title/link in job card")
                return None
            
            # Extract company from article a[href*="/empresas/"]
            try:
                company_link = job_card.find_element(By.CSS_SELECTOR, "a[href*='/empresas/']")
                job_data['company'] = company_link.text.strip()
            except NoSuchElementException:
                job_data['company'] = ""
            
            # Extract location from [aria-label="location"]
            try:
                location_elem = job_card.find_element(By.CSS_SELECTOR, "[aria-label='location']")
                job_data['location'] = location_elem.text.strip()
            except NoSuchElementException:
                job_data['location'] = ""
            
            # Extract short description from first <p> inside the card
            try:
                desc_elem = job_card.find_element(By.CSS_SELECTOR, "p")
                job_data['description'] = desc_elem.text.strip()
            except NoSuchElementException:
                job_data['description'] = ""
            
            logger.info(f"Extracted from card: {job_data['title'][:50]}... - {job_data['company']}")
            return job_data
            
        except Exception as e:
            logger.error(f"Error extracting job from card: {e}")
            return None
    
    def get_job_details(self, job_url):
        """Get detailed job information from job detail page."""
        try:
            logger.info(f"Getting job details: {job_url}")
            
            # Navigate to job detail page
            self.driver.get(job_url)
            time.sleep(3)  # Wait for page load
            
            # Wait for h1 to appear (main job title)
            wait = WebDriverWait(self.driver, self.wait_timeout)
            try:
                h1_elem = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
            except TimeoutException:
                logger.warning(f"Timeout waiting for h1 on {job_url}")
                return {}
            
            job_details = {}
            
            # Extract title from h1
            job_details['title'] = h1_elem.text.strip()
            
            # Extract company from h1 + div a
            try:
                company_elem = self.driver.find_element(By.CSS_SELECTOR, "h1 + div a")
                job_details['company'] = company_elem.text.strip()
            except NoSuchElementException:
                job_details['company'] = ""
            
            # Extract posted date from span[aria-label="Publicado"]
            try:
                date_elem = self.driver.find_element(By.CSS_SELECTOR, "span[aria-label='Publicado']")
                date_text = date_elem.text.strip()
                job_details['posted_date'] = self.parse_date(date_text)
            except NoSuchElementException:
                job_details['posted_date'] = datetime.today().date().isoformat()
            
            # Extract location from div[aria-label="location"]
            try:
                location_elem = self.driver.find_element(By.CSS_SELECTOR, "div[aria-label='location']")
                job_details['location'] = location_elem.text.strip()
            except NoSuchElementException:
                job_details['location'] = ""
            
            # Extract description from section h2:contains("Descripción del puesto") + div
            try:
                desc_section = self.driver.find_element(By.XPATH, "//section//h2[contains(text(), 'Descripción del puesto')]")
                desc_div = desc_section.find_element(By.XPATH, "following-sibling::div[1]")
                job_details['description'] = desc_div.text.strip()
            except NoSuchElementException:
                job_details['description'] = ""
            
            # Extract requirements from section h3:contains("Requisitos") + ul
            try:
                req_section = self.driver.find_element(By.XPATH, "//section//h3[contains(text(), 'Requisitos')]")
                req_ul = req_section.find_element(By.XPATH, "following-sibling::ul[1]")
                job_details['requirements'] = req_ul.text.strip()
            except NoSuchElementException:
                job_details['requirements'] = ""
            
            # Extract contract type from section li:contains("Por")
            try:
                contract_li = self.driver.find_element(By.XPATH, "//section//li[contains(text(), 'Por')]")
                job_details['contract_type'] = contract_li.text.strip()
            except NoSuchElementException:
                job_details['contract_type'] = ""
            
            # Extract remote type from section li:contains("Remoto"), "Presencial", "Híbrido"
            remote_type = ""
            try:
                # Look for remote type indicators
                remote_indicators = ["Remoto", "Presencial", "Híbrido"]
                for indicator in remote_indicators:
                    try:
                        remote_li = self.driver.find_element(By.XPATH, f"//section//li[contains(text(), '{indicator}')]")
                        remote_type = indicator
                        break
                    except NoSuchElementException:
                        continue
                job_details['remote_type'] = remote_type
            except Exception:
                job_details['remote_type'] = ""
            
            # Set salary to None as specified (site asks candidates for salary expectations)
            job_details['salary_raw'] = None
            
            logger.info(f"Extracted details: {job_details['title'][:50]}...")
            return job_details
            
        except Exception as e:
            logger.error(f"Error getting job details from {job_url}: {e}")
            return {}
    
    def parse_date(self, date_string: str) -> str:
        """Parse Bumeran date format."""
        if not date_string:
            return datetime.today().date().isoformat()
        
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
    
    def wait_for_page_load(self, timeout=60):
        """Wait for page to fully load, handling Cloudflare challenges."""
        start_time = time.time()
        logger.info("Waiting for page to load and checking for Cloudflare challenges...")
        
        while time.time() - start_time < timeout:
            try:
                page_source = self.driver.page_source
                current_url = self.driver.current_url
                
                # Check if we're still on the target page
                if self.base_url not in current_url and "bumeran.com.mx" not in current_url:
                    logger.warning(f"Redirected to unexpected URL: {current_url}")
                    return False
                
                # Check for Cloudflare challenge
                if self.check_cloudflare_challenge():
                    logger.info("Cloudflare challenge detected, waiting for resolution...")
                    time.sleep(5)
                    continue
                
                # Check if page has substantial content
                if len(page_source) > 50000:  # Page seems to have content
                    logger.info("Page loaded successfully with substantial content")
                    return True
                
                # Check for specific job-related content
                if any(keyword in page_source.lower() for keyword in ['empleo', 'trabajo', 'puesto', 'vacante']):
                    logger.info("Page loaded with job-related content")
                    return True
                
                time.sleep(2)
                
            except Exception as e:
                logger.debug(f"Error checking page load: {e}")
                time.sleep(2)
        
        logger.warning("Page load timeout reached")
        return False
    
    def check_cloudflare_challenge(self):
        """Check if we're being challenged by Cloudflare."""
        try:
            page_source = self.driver.page_source
            cloudflare_indicators = [
                "Attention Required!",
                "Cloudflare",
                "__CF$cv$params",
                "challenge-platform",
                "Checking your browser",
                "Please wait while we verify"
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking Cloudflare challenge: {e}")
            return False
    
    def validate_job_item(self, item: JobItem) -> bool:
        """Validate job item has required fields."""
        required_fields = ['title', 'company', 'portal', 'country']
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        return True
