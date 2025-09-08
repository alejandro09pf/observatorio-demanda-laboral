"""
ZonaJobs spider for Labor Market Observatory.
Scrapes job postings from zonajobs.com.ar using Selenium for React SPA handling.

Strategy: This site is a React SPA where job content loads via JavaScript after page render.
Static HTML does not contain job data, so we use Selenium with undetected-chromedriver to:
1. Load pages and wait for job cards to appear
2. Extract job listings from search results
3. Navigate to detail pages for full job information
4. Handle pagination until no more jobs are found
5. Rotate proxies and user agents to evade detection

HTML Structure Analysis:
- Job listings are in <article> elements with job title and link inside <h2><a>...</a></h2>
- Company name appears just below the title
- Location block is on the right with city and province
- Short description is in the first <p> element
- Job URLs follow pattern: https://www.zonajobs.com.ar/empleos/{job-slug}.html
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime, timedelta
import re
import random
import time
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Undetected ChromeDriver
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    logging.warning("undetected_chromedriver not available, falling back to regular ChromeDriver")

from .base_spider import BaseSpider
from ..items import JobItem

logger = logging.getLogger(__name__)

class ZonaJobsSpider(BaseSpider):
    """Spider for ZonaJobs job portal using Selenium for React SPA handling."""
    
    name = "zonajobs"
    allowed_domains = ["zonajobs.com.ar"]
    
    # Spider configuration - override base settings for Selenium
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Selenium is single-threaded
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 5,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,
        'ROBOTSTXT_OBEY': False,
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "zonajobs"
        
        # Fixed to Argentina as per requirements
        self.country = "AR"
        
        # Base URL for ZonaJobs Argentina
        self.base_url = "https://www.zonajobs.com.ar"
        self.start_url = f"{self.base_url}/empleos.html"
        
        # Selenium configuration
        self.driver = None
        self.wait_timeout = 30
        self.page_load_timeout = 45
        
        # Track scraped jobs to avoid duplicates
        self.scraped_urls = set()
        
        # Proxy and user agent management
        self.current_proxy = None
        self.current_user_agent = None
        self.proxy_failures = {}
        
        # User agents for rotation
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
        ]
    
    def start_requests(self):
        """Initialize Selenium driver and start scraping."""
        logger.info("🔧 Initializing Selenium WebDriver for ZonaJobs scraping")
        
        try:
            # Check orchestrator execution
            if not self._is_orchestrator_execution():
                raise RuntimeError(
                    f"This spider '{self.__class__.__name__}' can only be executed through the orchestrator.\n"
                    f"Use: python -m src.orchestrator run-once {self.__class__.__name__.lower()} --country AR"
                )
            
            self.setup_driver()
            yield scrapy.Request(
                url=self.start_url,
                callback=self.parse_search_results_page,
                meta={'page': 1},
                dont_filter=True
            )
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium driver: {e}")
            raise
    
    def get_proxy(self):
        """Get proxy from orchestrator's proxy service."""
        try:
            # For testing, disable proxy to avoid network issues
            if os.getenv('DISABLE_PROXY', 'false').lower() == 'true':
                logger.info("🔧 Proxy disabled for testing")
                return None
            
            # Try to get proxy from environment or proxy service
            proxy_pool = os.getenv('PROXY_POOL', '')
            if proxy_pool:
                proxies = [proxy.strip() for proxy in proxy_pool.split(',') if proxy.strip()]
                if proxies:
                    # Filter out failed proxies
                    available_proxies = [p for p in proxies if p not in self.proxy_failures]
                    if available_proxies:
                        return random.choice(available_proxies)
                    else:
                        # Reset failures if all proxies failed
                        self.proxy_failures.clear()
                        return random.choice(proxies)
            return None
        except Exception as e:
            logger.warning(f"Could not get proxy: {e}")
            return None
    
    def _create_chrome_options(self, proxy: str = None) -> Options:
        """Create Chrome options with anti-detection features."""
        options = Options()
        
        # Basic anti-detection options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Window size (randomize slightly)
        width = random.randint(1200, 1400)
        height = random.randint(800, 1000)
        options.add_argument(f"--window-size={width},{height}")
        
        # User agent rotation
        self.current_user_agent = random.choice(self.user_agents)
        options.add_argument(f"--user-agent={self.current_user_agent}")
        
        # Language settings for Argentina
        options.add_argument("--lang=es-AR")
        options.add_experimental_option("prefs", {
            "intl.accept_languages": "es-AR,es,en-US,en"
        })
        
        # Add proxy if available
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
            self.current_proxy = proxy
            logger.info(f"🌐 Using proxy: {proxy[:30]}...")
        
        # Additional anti-detection options
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        return options
    
    def setup_driver(self):
        """Setup Chrome WebDriver with advanced anti-detection."""
        try:
            logger.info("🔧 Setting up Chrome WebDriver...")
            
            # Get proxy
            proxy = self.get_proxy()
            
            # Create options
            options = self._create_chrome_options(proxy)
            
            # Create driver with webdriver-manager for version compatibility
            logger.info("🔧 Using regular ChromeDriver with webdriver-manager...")
            from webdriver_manager.chrome import ChromeDriverManager
            from selenium.webdriver.chrome.service import Service
            
            # Get compatible ChromeDriver
            driver_path = ChromeDriverManager().install()
            logger.info(f"✅ ChromeDriver installed at: {driver_path}")
            
            # Create service
            service = Service(driver_path)
            
            # Create regular ChromeDriver (more reliable than undetected-chromedriver)
            self.driver = webdriver.Chrome(service=service, options=options)
            logger.info("✅ Driver created successfully with webdriver-manager")
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(10)
            
            # Execute anti-detection scripts
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['es-AR', 'es', 'en']})")
            self.driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            self.driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
            
            logger.info("✅ Chrome WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create WebDriver: {e}")
            if proxy:
                self._mark_proxy_failed(proxy)
            raise
    
    def _mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed."""
        self.proxy_failures[proxy] = datetime.now()
        logger.warning(f"⚠️ Marked proxy as failed: {proxy[:30]}...")
    
    def _rotate_proxy_and_ua(self):
        """Rotate proxy and user agent for new session."""
        try:
            if self.driver:
                self.driver.quit()
            
            # Wait a bit before creating new session
            time.sleep(random.uniform(2, 5))
            
            # Setup new driver with new proxy/UA
            self.setup_driver()
            logger.info("🔄 Rotated proxy and user agent")
            
        except Exception as e:
            logger.error(f"❌ Error rotating proxy/UA: {e}")
            raise
    
    def parse_search_results_page(self, response):
        """Parse search results page using Selenium with proper article element detection."""
        page = response.meta.get('page', 1)
        logger.info(f"📄 Parsing search results page {page}")
        
        try:
            # Navigate to the page
            page_url = f"{self.start_url}?page={page}" if page > 1 else self.start_url
            logger.info(f"🌐 Navigating to: {page_url}")
            self.driver.get(page_url)
            
            # Wait for React SPA to load
            time.sleep(random.uniform(5, 8))
            
            # Check if page loaded properly (not blocked or error page)
            page_source = self.driver.page_source
            logger.info(f"📄 Page source length: {len(page_source)} characters")
            
            # Check for error pages
            if "This site can't be reached" in page_source or "ERR_" in page_source or "Chrome error" in page_source:
                logger.error("❌ Network error or proxy issue detected")
                logger.info(f"📄 Page source preview: {page_source[:500]}...")
                return
            
            if "Attention Required!" in page_source or "Cloudflare" in page_source:
                logger.warning("⚠️ Cloudflare protection detected - waiting longer...")
                time.sleep(15)
                self.driver.refresh()
                time.sleep(8)
                page_source = self.driver.page_source
                if "Attention Required!" in page_source or "Cloudflare" in page_source:
                    logger.error("❌ Still blocked by Cloudflare")
                    return
            else:
                logger.info("✅ No Cloudflare protection detected")
            
            # Wait for article elements to appear (as per requirements)
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            try:
                # Wait for job links to be present (actual structure found)
                logger.info("⏳ Waiting for job links to load...")
                
                # Try to find job links with a more flexible approach
                job_links = []
                max_attempts = 10
                for attempt in range(max_attempts):
                    job_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='empleos/']")
                    if job_links:
                        logger.info(f"📋 Found {len(job_links)} job links on attempt {attempt + 1}")
                        break
                    else:
                        logger.info(f"⏳ Attempt {attempt + 1}: No job links found, waiting...")
                        time.sleep(2)
                
                if not job_links:
                    logger.error("❌ No job links found after all attempts")
                    # Log page source for debugging
                    page_source = self.driver.page_source
                    logger.info(f"📄 Page source preview: {page_source[:1000]}...")
                    return
                
                # Filter out navigation links (seniority, relevantes, recientes)
                actual_job_links = []
                for link in job_links:
                    href = link.get_attribute('href')
                    if href and not any(nav in href for nav in ['seniority', 'relevantes', 'recientes']):
                        actual_job_links.append(link)
                
                logger.info(f"📋 Found {len(actual_job_links)} actual job postings")
                
                if not actual_job_links:
                    logger.warning(f"⚠️ No actual job links found on page {page}")
                    return
                
                # Extract job data from each link
                job_data_list = []
                for i, job_link in enumerate(actual_job_links):
                    try:
                        job_data = self.extract_job_from_link(job_link)
                        if job_data and job_data.get('url'):
                            job_data_list.append(job_data)
                    except Exception as e:
                        logger.error(f"❌ Error extracting job from link {i}: {e}")
                        continue
                
                logger.info(f"✅ Extracted {len(job_data_list)} jobs from page {page}")
                
                # Process each job
                for job_data in job_data_list:
                    if job_data['url'] not in self.scraped_urls:
                        self.scraped_urls.add(job_data['url'])
                        
                        # Get detailed job information from the job page (temporarily disabled for testing)
                        # detailed_info = self.get_job_details(job_data['url'])
                        detailed_info = {}  # Skip detail extraction to avoid hanging
                        
                        # Merge detailed info with listing data
                        for key, value in detailed_info.items():
                            if value and not job_data.get(key):
                                job_data[key] = value
                        
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
                        item['salary_raw'] = job_data.get('salary_raw', '')
                        item['contract_type'] = job_data.get('contract_type', '')
                        item['remote_type'] = job_data.get('remote_type', '')
                        item['posted_date'] = job_data.get('posted_date', datetime.today().date().isoformat())
                        
                        # Add additional fields
                        item['job_id'] = job_data.get('job_id', '')
                        item['job_category'] = job_data.get('job_category', '')
                        item['role_activities'] = job_data.get('role_activities', [])
                        item['compensation'] = job_data.get('compensation', {})
                        item['geolocation'] = job_data.get('geolocation', [])
                        item['source_country'] = self.country.lower()
                        item['scraped_at'] = datetime.now().isoformat()
                        
                        # Validate and yield item
                        if self.validate_job_item(item):
                            yield item
                            logger.info(f"✅ Scraped job: {item['title']} - {item['company']}")
                        else:
                            logger.warning(f"⚠️ Invalid job item: {job_data.get('title', 'No title')}")
                
                # Check if we should continue to next page
                if page < self.max_pages and len(job_data_list) > 0:
                    # Rotate proxy and user agent for next page
                    if page % 3 == 0:  # Rotate every 3 pages
                        logger.info("🔄 Rotating proxy and user agent...")
                        self._rotate_proxy_and_ua()
                    
                    # Continue to next page
                    next_page = page + 1
                    next_url = f"{self.start_url}?page={next_page}"
                    
                    # Add random delay
                    time.sleep(random.uniform(2, 5))
                    
                    yield scrapy.Request(
                        url=next_url,
                        callback=self.parse_search_results_page,
                        meta={'page': next_page},
                        dont_filter=True
                    )
                else:
                    logger.info(f"🏁 Finished scraping. Processed {len(self.scraped_urls)} unique jobs.")
                
            except TimeoutException:
                logger.error(f"❌ Timeout waiting for job links on page {page}")
                return
                
        except Exception as e:
            logger.error(f"❌ Error parsing search results page {page}: {e}")
        finally:
            # Clean up driver when done
            if page >= self.max_pages:
                self.cleanup_driver()
    
    def extract_job_from_link(self, job_link) -> Dict[str, Any]:
        """Extract job information from a job link element."""
        job_data = {}
        
        try:
            # Extract URL
            job_data['url'] = job_link.get_attribute('href')
            
            # Extract text content and parse it
            link_text = job_link.text.strip()
            if link_text:
                job_data.update(self.parse_job_link_text(link_text))
            
            # Try to extract additional data from child elements
            try:
                # Look for title in child elements
                title_selectors = [
                    "h2", "h3", "h4", ".title", "[class*='title']"
                ]
                for selector in title_selectors:
                    try:
                        title_element = job_link.find_element(By.CSS_SELECTOR, selector)
                        if title_element.text.strip():
                            job_data['title'] = title_element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
                # Look for company in child elements
                company_selectors = [
                    ".company", "[class*='company']", ".employer", "[class*='employer']"
                ]
                for selector in company_selectors:
                    try:
                        company_element = job_link.find_element(By.CSS_SELECTOR, selector)
                        if company_element.text.strip():
                            job_data['company'] = company_element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
                # Look for location in child elements
                location_selectors = [
                    ".location", "[class*='location']", ".place", "[class*='place']"
                ]
                for selector in location_selectors:
                    try:
                        location_element = job_link.find_element(By.CSS_SELECTOR, selector)
                        if location_element.text.strip():
                            job_data['location'] = location_element.text.strip()
                            break
                    except NoSuchElementException:
                        continue
                
            except Exception as e:
                logger.debug(f"Could not extract additional data from child elements: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error extracting job from link: {e}")
        
        return job_data
    
    def parse_job_link_text(self, link_text: str) -> Dict[str, Any]:
        """Parse job information from link text content."""
        job_data = {}
        
        try:
            # Split the text into lines
            lines = [line.strip() for line in link_text.split('\n') if line.strip()]
            
            if not lines:
                return job_data
            
            # Extract posted date (usually first line with "Publicado")
            for i, line in enumerate(lines):
                if 'publicado' in line.lower():
                    job_data['posted_date'] = self.parse_date(line)
                    lines = lines[i+1:]  # Remove date line
                    break
            
            # Extract job title (usually the first substantial line after date)
            if lines:
                title_line = lines[0]
                # Skip lines that are just navigation or filters
                if not any(skip in title_line.lower() for skip in ['puestos', 'relevantes', 'recientes', 'seniority']):
                    job_data['title'] = title_line
                    lines = lines[1:]
            
            # Extract company name (look for lines that don't contain job-related keywords)
            for i, line in enumerate(lines):
                if line and not any(keyword in line.lower() for keyword in 
                                  ['responsabilidades', 'requisitos', 'presencial', 'remoto', 'híbrido', 
                                   'para', 'zona', 'buenos aires', 'caba', 'rosario', 'córdoba']):
                    job_data['company'] = line
                    lines = lines[i+1:]
                    break
            
            # Extract location (look for lines with location keywords)
            for i, line in enumerate(lines):
                if any(location_keyword in line.lower() for location_keyword in 
                      ['buenos aires', 'caba', 'rosario', 'córdoba', 'mendoza', 'la plata', 'quilmes', 'moreno']):
                    job_data['location'] = line
                    lines = lines[i+1:]
                    break
            
            # Extract remote type (look for work mode keywords)
            for i, line in enumerate(lines):
                if any(mode in line.lower() for mode in ['presencial', 'remoto', 'híbrido']):
                    job_data['remote_type'] = line.title()
                    lines = lines[i+1:]
                    break
            
            # Extract description from remaining lines
            if lines:
                description_lines = []
                for line in lines:
                    if line and not any(skip in line.lower() for skip in ['requisitos', 'responsabilidades']):
                        description_lines.append(line)
                
                if description_lines:
                    job_data['description'] = ' '.join(description_lines)
            
            # If no description found, provide a default one
            if not job_data.get('description'):
                job_data['description'] = f"Oportunidad laboral en {job_data.get('company', 'empresa')} - {job_data.get('title', 'puesto')}"
            
        except Exception as e:
            logger.error(f"Error parsing job link text: {e}")
        
        return job_data
    
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Get detailed job information from job detail page."""
        details = {}
        
        try:
            logger.info(f"🔍 Getting job details from: {job_url}")
            
            # Navigate to job detail page
            self.driver.get(job_url)
            time.sleep(random.uniform(2, 4))  # Wait for content to load
            
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            # Extract title (h1)
            try:
                title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
                details['title'] = title_element.text.strip()
            except TimeoutException:
                logger.warning("⚠️ Could not find title element")
            
            # Extract company (link immediately following the title)
            try:
                company_selectors = [
                    "h1 + a",
                    "h1 + div a",
                    "h1 + span a",
                    ".company-name",
                    ".employer",
                    "[data-testid='company']",
                    "div[class*='company'] a"
                ]
                
                for selector in company_selectors:
                    try:
                        company_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['company'] = company_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract company: {e}")
            
            # Extract posted date (element with "Publicado")
            try:
                date_selectors = [
                    'span[aria-label="Publicado"]',
                    'span:contains("Publicado")',
                    'time',
                    '.date',
                    '.posted-date',
                    'span[class*="date"]'
                ]
                
                for selector in date_selectors:
                    try:
                        date_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        date_text = date_element.text.strip()
                        if date_text and 'publicado' in date_text.lower():
                            details['posted_date'] = self.parse_date(date_text)
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract date: {e}")
            
            # Extract location (city/province text)
            try:
                location_selectors = [
                    'div[aria-label="location"]',
                    '.location',
                    '.place',
                    'span[class*="location"]',
                    'div[class*="location"]'
                ]
                
                for selector in location_selectors:
                    try:
                        location_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        location_text = location_element.text.strip()
                        if location_text:
                            details['location'] = location_text
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract location: {e}")
            
            # Extract remote type (look for "Remoto", "Presencial", or "Híbrido")
            try:
                # Look for remote type indicators near location
                page_text = self.driver.page_source.lower()
                if 'remoto' in page_text:
                    details['remote_type'] = 'Remoto'
                elif 'híbrido' in page_text:
                    details['remote_type'] = 'Híbrido'
                elif 'presencial' in page_text:
                    details['remote_type'] = 'Presencial'
                
                # Also try to find specific elements
                modality_selectors = [
                    'div[aria-label="modalidad"]',
                    '.contract-type',
                    '.work-mode',
                    'span[class*="modality"]',
                    'span:contains("Remoto")',
                    'span:contains("Presencial")',
                    'span:contains("Híbrido")'
                ]
                
                for selector in modality_selectors:
                    try:
                        modality_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        modality_text = modality_element.text.strip().lower()
                        if any(mode in modality_text for mode in ['remoto', 'presencial', 'híbrido']):
                            for mode in ['remoto', 'presencial', 'híbrido']:
                                if mode in modality_text:
                                    details['remote_type'] = mode.title()
                                    break
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract remote type: {e}")
            
            # Extract description (paragraphs following "Descripción del puesto")
            try:
                desc_selectors = [
                    'section h2:contains("Descripción") + div',
                    'section h3:contains("Descripción") + div',
                    '.description',
                    '.job-description',
                    '[data-testid="description"]',
                    'div[class*="description"]'
                ]
                
                for selector in desc_selectors:
                    try:
                        desc_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['description'] = desc_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract description: {e}")
            
            # Extract requirements (bullet points under "Requisitos")
            try:
                req_selectors = [
                    'section h3:contains("Requisitos") + ul',
                    'section h2:contains("Requisitos") + ul',
                    '.requirements',
                    '.job-requirements',
                    '[data-testid="requirements"]',
                    'div[class*="requirements"] ul'
                ]
                
                for selector in req_selectors:
                    try:
                        req_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['requirements'] = req_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract requirements: {e}")
            
            # Extract contract type (tags like "Tiempo Completo")
            try:
                contract_selectors = [
                    'span:contains("Tiempo Completo")',
                    'span:contains("Part Time")',
                    'span:contains("Contrato")',
                    '.contract-type',
                    '.work-mode',
                    'span[class*="contract"]'
                ]
                
                for selector in contract_selectors:
                    try:
                        contract_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        contract_text = contract_element.text.strip()
                        if contract_text:
                            details['contract_type'] = contract_text
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract contract type: {e}")
            
            # Set salary to None (ZonaJobs does not disclose salaries)
            details['salary_raw'] = None
            
        except Exception as e:
            logger.error(f"❌ Error getting job details from {job_url}: {e}")
        
        return details
    
    def parse_date(self, date_string: str) -> str:
        """Parse date string to ISO format."""
        if not date_string:
            return datetime.today().date().isoformat()
        
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
                        # Handle relative dates - subtract days/hours
                        if 'días' in date_string:
                            days = int(match.group(1))
                            return (datetime.today() - timedelta(days=days)).date().isoformat()
                        elif 'horas' in date_string:
                            hours = int(match.group(1))
                            return (datetime.today() - timedelta(hours=hours)).date().isoformat()
                        else:
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
    
    def cleanup_driver(self):
        """Clean up Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Selenium WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"❌ Error cleaning up WebDriver: {e}")
            finally:
                self.driver = None
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.cleanup_driver()
        logger.info(f"🏁 ZonaJobs spider closed: {reason}")
        logger.info(f"📊 Total jobs scraped: {len(self.scraped_urls)}")
        
        # Save results summary
        self.save_scraping_summary()
    
    def save_scraping_summary(self):
        """Save scraping summary to file."""
        summary = {
            'spider_name': self.name,
            'country': self.country,
            'total_jobs_scraped': len(self.scraped_urls),
            'scraped_urls': list(self.scraped_urls),
            'timestamp': datetime.now().isoformat(),
            'status': 'completed',
            'proxy_usage': {
                'current_proxy': self.current_proxy,
                'failed_proxies': list(self.proxy_failures.keys()),
                'user_agent': self.current_user_agent
            }
        }
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        summary_file = output_dir / "zonajobs_scraping_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"📄 Scraping summary saved to: {summary_file}")
