"""
ZonaJobs spider for Labor Market Observatory.
Scrapes job postings from zonajobs.com.ar using Selenium for React SPA handling.

Strategy: This site is a React SPA where job content loads via JavaScript after page render.
Static HTML does not contain job data, so we use Selenium with Chrome WebDriver to:
1. Load pages and wait for job cards to appear
2. Extract job listings from search results
3. Navigate to detail pages for full job information
4. Handle pagination until no more jobs are found

HTML Structure Analysis:
- Job listings are in div elements with classes like 'sc-iunyMi bPzdzh sc-gVZiCL jqMLeJ'
- Job information is embedded within link text
- Each job link contains: title, company, location, description, requirements
- Job URLs follow pattern: https://www.zonajobs.com.ar/empleos/{job-slug}.html
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional, List, Dict, Any
import logging
import time
import json
from pathlib import Path

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

logger = logging.getLogger(__name__)

class ZonaJobsSpider(BaseSpider):
    """Spider for ZonaJobs job portal using Selenium for React SPA handling."""
    
    name = "zonajobs"
    allowed_domains = ["zonajobs.com.ar"]
    
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
        self.wait_timeout = 15
        self.page_load_timeout = 30
        
        # Track scraped jobs to avoid duplicates
        self.scraped_urls = set()
        
        # Override custom settings for Selenium-based spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 3,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Selenium is single-threaded
            'DOWNLOAD_TIMEOUT': 60,
        })
    
    def start_requests(self):
        """Initialize Selenium driver and start scraping."""
        logger.info("Initializing Selenium WebDriver for ZonaJobs scraping")
        
        try:
            self.setup_driver()
            yield scrapy.Request(
                url=self.start_url,
                callback=self.parse_search_results,
                meta={'page': 1},
                dont_filter=True
            )
        except Exception as e:
            logger.error(f"Failed to initialize Selenium driver: {e}")
            raise
    
    def setup_driver(self):
        """Setup Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        
        # Headless mode for production
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # User agent rotation (will be handled by middleware)
        # chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        # Additional options for stability
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            logger.info("Selenium WebDriver initialized successfully")
        except Exception as e:
            logger.error(f"Failed to create WebDriver: {e}")
            raise
    
    def parse_search_results(self, response):
        """Parse search results page using Selenium."""
        page = response.meta.get('page', 1)
        logger.info(f"Parsing search results page {page}")
        
        try:
            # Navigate to the page
            page_url = f"{self.start_url}?page={page}" if page > 1 else self.start_url
            logger.info(f"Navigating to: {page_url}")
            self.driver.get(page_url)
            
            # Increased wait time for React SPA to load
            time.sleep(10)  # Increased wait time
            
            # Check if page loaded properly (not blocked)
            page_source = self.driver.page_source
            if "Attention Required!" in page_source or "Cloudflare" in page_source:
                logger.warning("Cloudflare protection detected - waiting longer...")
                time.sleep(20)
                self.driver.refresh()
                time.sleep(10)
                page_source = self.driver.page_source
                if "Attention Required!" in page_source or "Cloudflare" in page_source:
                    logger.error("Still blocked by Cloudflare")
                    return
            
            # Wait for content to load with multiple selector attempts
            wait = WebDriverWait(self.driver, 30)  # Increased timeout
            
            # Try multiple selectors to find job content
            job_selectors = [
                "a[href*='empleos/']",
                "a[href*='/empleos/']", 
                "a[href*='empleo']",
                "div[class*='job'] a",
                "div[class*='empleo'] a",
                "[class*='job-card'] a",
                "[class*='job-listing'] a",
                "article a",
                ".job-item a",
                "[data-testid*='job'] a"
            ]
            
            job_links_found = False
            job_links = []
            
            for selector in job_selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    
                    # Find job links
                    found_links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(found_links)} links with selector: {selector}")
                    
                    # Filter for actual job postings
                    for link in found_links:
                        href = link.get_attribute("href")
                        if href and '/empleos/' in href and not any(nav in href for nav in ['seniority', 'relevantes', 'recientes']):
                            job_links.append(link)
                    
                    if job_links:
                        job_links_found = True
                        logger.info(f"Found {len(job_links)} actual job postings")
                        break
                        
                except TimeoutException:
                    logger.debug(f"Selector '{selector}' timed out")
                    continue
                except Exception as e:
                    logger.debug(f"Selector '{selector}' failed: {e}")
                    continue
            
            if not job_links_found:
                logger.warning(f"No job links found on page {page} after trying all selectors")
                # Log page source for debugging
                page_source = self.driver.page_source
                logger.info(f"Page source length: {len(page_source)} characters")
                logger.info(f"Page source preview: {page_source[:500]}...")
                return
            
            # Extract data from all job links immediately to avoid stale element issues
            job_data_list = []
            for i, job_link in enumerate(job_links):
                try:
                    # Extract data immediately before DOM changes
                    job_url = job_link.get_attribute("href")
                    link_text = job_link.text.strip()
                    
                    if job_url and link_text:
                        job_data = self.parse_job_link_text(link_text)
                        job_data['url'] = job_url
                        job_data_list.append(job_data)
                        
                except Exception as e:
                    logger.error(f"Error extracting data from job link {i} on page {page}: {e}")
                    continue
            
            # Process the extracted job data
            for job_data in job_data_list:
                if job_data['url'] not in self.scraped_urls:
                    self.scraped_urls.add(job_data['url'])
                    
                    # Get detailed job information from the job page
                    detailed_info = self.get_job_details(job_data['url'])
                    
                    # Merge detailed info with link data
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
                    
                    # Validate and yield item
                    if self.validate_job_item(item):
                        yield item
                        logger.info(f"Scraped job: {item['title']} - {item['company']}")
                    else:
                        logger.warning(f"Invalid job item: {job_data.get('title', 'No title')}")
            
            # Check if we should continue to next page
            if page < self.max_pages:
                # Check if there are more job links on the next page
                next_page = page + 1
                next_url = f"{self.start_url}?page={next_page}"
                
                # Try to load next page to see if it has content
                self.driver.get(next_url)
                time.sleep(2)  # Brief wait for content to load
                
                try:
                    next_job_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='empleos/']")
                    # Filter actual job postings
                    next_actual_jobs = [link for link in next_job_links 
                                      if link.get_attribute("href") and '/empleos/' in link.get_attribute("href") 
                                      and not any(nav in link.get_attribute("href") for nav in ['seniority', 'relevantes', 'recientes'])]
                    
                    if next_actual_jobs:
                        logger.info(f"Found {len(next_actual_jobs)} jobs on page {next_page}, continuing...")
                        yield scrapy.Request(
                            url=next_url,
                            callback=self.parse_search_results,
                            meta={'page': next_page},
                            dont_filter=True
                        )
                    else:
                        logger.info(f"No more jobs found on page {next_page}, stopping pagination")
                except Exception as e:
                    logger.warning(f"Error checking next page {next_page}: {e}")
            
        except Exception as e:
            logger.error(f"Error parsing search results page {page}: {e}")
        finally:
            # Clean up driver when done
            if page >= self.max_pages or not self.driver:
                self.cleanup_driver()
    
    def parse_job_link_text(self, link_text: str) -> Dict[str, Any]:
        """Parse job information from link text."""
        job_data = {}
        
        try:
            # Split the text into lines
            lines = [line.strip() for line in link_text.split('\n') if line.strip()]
            
            if not lines:
                return job_data
            
            # Extract posted date (usually first line)
            if lines and 'hace' in lines[0].lower():
                job_data['posted_date'] = self.parse_date(lines[0])
                lines = lines[1:]  # Remove date line
            
            # Extract job title (usually the first substantial line)
            if lines:
                title_line = lines[0]
                # Skip lines that are just "Nuevo" or similar
                if not any(skip in title_line.lower() for skip in ['nuevo', 'alta revisión', 'múltiples']):
                    job_data['title'] = title_line
                    lines = lines[1:]
            
            # Extract company name (look for lines that don't contain job-related keywords)
            for i, line in enumerate(lines):
                if line and not any(keyword in line.lower() for keyword in 
                                  ['responsabilidades', 'requisitos', 'presencial', 'remoto', 'híbrido', 
                                   'alta revisión', 'múltiples vacantes', 'zona', 'buenos aires']):
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
                    job_data['remote_type'] = line
                    lines = lines[i+1:]
                    break
            
            # Extract description and requirements from remaining lines
            description_lines = []
            requirements_lines = []
            
            in_requirements = False
            for line in lines:
                if 'requisitos' in line.lower() or '¿qué esperamos' in line.lower():
                    in_requirements = True
                    continue
                
                if in_requirements:
                    requirements_lines.append(line)
                else:
                    description_lines.append(line)
            
            if description_lines:
                job_data['description'] = ' '.join(description_lines)
            
            if requirements_lines:
                job_data['requirements'] = ' '.join(requirements_lines)
            
        except Exception as e:
            logger.error(f"Error parsing job link text: {e}")
        
        return job_data
    
    def get_job_details(self, job_url: str) -> Dict[str, Any]:
        """Get detailed job information from job detail page."""
        details = {}
        
        try:
            # Navigate to job detail page
            self.driver.get(job_url)
            time.sleep(2)  # Wait for content to load
            
            wait = WebDriverWait(self.driver, self.wait_timeout)
            
            # Extract title
            try:
                title_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "h1")))
                details['title'] = title_element.text.strip()
            except TimeoutException:
                pass
            
            # Extract company
            try:
                company_selectors = [
                    "h1 + div span",
                    ".company-name",
                    ".employer",
                    "[data-testid='company']",
                    "div[class*='company']"
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
            
            # Extract posted date
            try:
                date_selectors = [
                    "time",
                    'span[aria-label="Publicado"]',
                    '.date',
                    '.posted-date',
                    'span[class*="date"]'
                ]
                
                for selector in date_selectors:
                    try:
                        date_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        date_text = date_element.text.strip()
                        if date_text:
                            details['posted_date'] = self.parse_date(date_text)
                            break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract date: {e}")
            
            # Extract location
            try:
                location_selectors = [
                    'div[aria-label="location"]',
                    '.location',
                    '.place',
                    'span[class*="location"]'
                ]
                
                for selector in location_selectors:
                    try:
                        location_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['location'] = location_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract location: {e}")
            
            # Extract description
            try:
                desc_selectors = [
                    'section h2:contains("Descripción") + div',
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
            
            # Extract requirements
            try:
                req_selectors = [
                    'section h3:contains("Requisitos") + ul',
                    '.requirements',
                    '.job-requirements',
                    '[data-testid="requirements"]',
                    'div[class*="requirements"]'
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
            
            # Extract contract type/modality
            try:
                modality_selectors = [
                    'div[aria-label="modalidad"]',
                    '.contract-type',
                    '.work-mode',
                    'span[class*="modality"]'
                ]
                
                for selector in modality_selectors:
                    try:
                        modality_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['contract_type'] = modality_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract contract type: {e}")
            
            # Extract salary (optional - generally not present)
            try:
                salary_selectors = [
                    '.salary',
                    '.wage',
                    '[data-testid="salary"]',
                    'span[class*="salary"]'
                ]
                
                for selector in salary_selectors:
                    try:
                        salary_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        details['salary_raw'] = salary_element.text.strip()
                        break
                    except NoSuchElementException:
                        continue
            except Exception as e:
                logger.debug(f"Could not extract salary: {e}")
            
        except Exception as e:
            logger.error(f"Error getting job details from {job_url}: {e}")
        
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
    
    def cleanup_driver(self):
        """Clean up Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"Error cleaning up WebDriver: {e}")
            finally:
                self.driver = None
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.cleanup_driver()
        logger.info(f"ZonaJobs spider closed: {reason}")
        
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
            'status': 'completed'
        }
        
        output_dir = Path("outputs")
        output_dir.mkdir(exist_ok=True)
        
        summary_file = output_dir / "zonajobs_scraping_summary.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Scraping summary saved to: {summary_file}")
