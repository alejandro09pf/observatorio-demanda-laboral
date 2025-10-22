"""
Magneto spider for Labor Market Observatory.
Scrapes job postings from Magneto365 using Selenium (SPA dynamic content).
"""

import scrapy
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from .base_spider import BaseSpider
from ..items import JobItem

logger = logging.getLogger(__name__)


class MagnetoSpider(BaseSpider):
    """Spider for Magneto365 job portal using Selenium for SPA content."""

    name = "magneto"
    allowed_domains = ["magneto365.com"]

    # Custom settings optimized for Selenium scraping
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
        self.portal = "magneto"
        self.driver = None
        self.wait_timeout = 20
        self.scraped_urls = set()

        # Set start URL based on country
        if self.country == "CO":
            self.start_url = "https://www.magneto365.com/co/empleos"
        elif self.country == "AR":
            self.start_url = "https://www.magneto365.com/ar/empleos"
        else:
            logger.warning(f"Magneto not configured for country: {self.country}")
            self.start_url = "https://www.magneto365.com/co/empleos"

        logger.info(f"Magneto spider initialized for country: {self.country}")
        logger.info(f"Start URL: {self.start_url}")

    def start_requests(self):
        """Start scraping with Selenium."""
        if not hasattr(self, 'start_url'):
            logger.error("No start URL configured")
            return

        # Initialize Selenium driver
        self._setup_driver()

        # Start scraping from page 1
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_search_results_page,
            meta={'page': 1},
            dont_filter=True
        )

    def _setup_driver(self):
        """Setup Chrome WebDriver with webdriver-manager."""
        try:
            logger.info("Setting up Chrome WebDriver...")

            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            options.add_argument(f'user-agent={self.settings.get("USER_AGENT")}')

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)

            logger.info("ChromeDriver initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize ChromeDriver: {e}")
            raise

    def parse_search_results_page(self, response):
        """Parse a search results page using Selenium."""
        page = response.meta.get('page', 1)

        try:
            logger.info(f"Parsing search results page {page}")
            logger.info(f"Navigating to: {response.url}")

            # Navigate to page
            self.driver.get(response.url)

            # Wait for job cards to load (Magneto uses dynamic loading)
            time.sleep(5)  # Initial wait for JavaScript to execute

            # Extract job URLs (strings, not elements) to avoid stale element issues
            job_urls = self._extract_job_urls()

            if not job_urls:
                logger.warning(f"No job URLs found on page {page}")
                return

            logger.info(f"Found {len(job_urls)} job postings on page {page}")

            # Process each job URL
            job_data_list = []
            for i, job_url in enumerate(job_urls):
                try:
                    logger.info(f"Processing job {i+1}/{len(job_urls)}: {job_url}")
                    job_data = self._extract_job_from_url(job_url)
                    if job_data and job_data.get('url'):
                        job_data_list.append(job_data)
                except Exception as e:
                    logger.error(f"Error extracting job from URL {i}: {e}")
                    continue

            logger.info(f"Extracted {len(job_data_list)} jobs from page {page}")

            # Yield items
            for job_data in job_data_list:
                if job_data['url'] not in self.scraped_urls:
                    self.scraped_urls.add(job_data['url'])

                    item = JobItem()
                    item['portal'] = 'magneto'
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
                    item['posted_date'] = job_data.get('posted_date') or None  # None instead of '' for SQL
                    item['job_id'] = ''
                    item['job_category'] = ''
                    item['role_activities'] = []
                    item['compensation'] = {}
                    item['geolocation'] = []
                    item['source_country'] = self.country.lower()
                    item['scraped_at'] = datetime.now().isoformat()

                    if self.validate_job_item(item):
                        yield item
                        logger.info(f"Scraped job: {item['title']} - {item['company']}")

            # Check if we should continue to next page
            if page < self.max_pages and len(job_data_list) > 0:
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
                logger.info(f"Finished scraping. Processed {len(self.scraped_urls)} unique jobs.")

        except Exception as e:
            logger.error(f"Error parsing search results page {page}: {e}")
        finally:
            # Clean up driver when done
            if page >= self.max_pages:
                self.cleanup_driver()

    def _extract_job_urls(self):
        """Extract job URLs (as strings) from the current page."""
        job_urls = []

        # Try multiple selector strategies for Magneto
        selectors = [
            'a[href*="/empleos/"]',
            'a[href*="/co/empleos/"]',
            'a[href*="/ar/empleos/"]',
            '.job-card a',
            '.vacancy a',
            '[data-testid="job-card"] a',
            'article a',
        ]

        job_links = []
        for selector in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"Found {len(elements)} elements with selector: {selector}")
                    job_links = elements
                    break
            except Exception as e:
                logger.debug(f"Selector {selector} failed: {e}")
                continue

        # Extract URLs from elements immediately (before they become stale)
        for link in job_links:
            try:
                href = link.get_attribute('href')
                if href and '/empleos/' in href and href not in [self.start_url]:
                    # Avoid pagination/filter links
                    if '?' not in href or 'page=' not in href:
                        job_urls.append(href)
            except:
                continue

        logger.info(f"Found {len(job_urls)} actual job URLs")
        return job_urls

    def _extract_job_from_url(self, job_url: str) -> Dict[str, Any]:
        """Extract job information by navigating to the job detail page."""
        job_data = {}

        try:
            job_data['url'] = job_url

            # Navigate to job detail page
            logger.debug(f"Navigating to job detail: {job_url}")
            self.driver.get(job_url)
            time.sleep(3)  # Wait for page to load

            # Extract job details from the detail page
            job_data.update(self._extract_job_details_from_page())

            # Ensure we have at least a basic description
            if not job_data.get('description'):
                title = job_data.get('title', 'puesto')
                company = job_data.get('company', 'empresa')
                job_data['description'] = f"Oportunidad laboral en {company} - {title}"

        except Exception as e:
            logger.error(f"Error extracting job from URL: {e}")

        return job_data

    def _extract_job_details_from_page(self) -> Dict[str, Any]:
        """Extract all job details from the current detail page using Magneto-specific selectors."""
        job_data = {}

        try:
            # Extract title - Magneto uses h1 element
            try:
                title_elem = self.driver.find_element(By.CSS_SELECTOR, 'h1')
                if title_elem.text.strip():
                    job_data['title'] = title_elem.text.strip()
            except NoSuchElementException:
                logger.debug("Could not extract title")

            # Extract company name - Use meta tag as primary source (most reliable)
            try:
                meta_title = self.driver.find_element(By.CSS_SELECTOR, 'meta[property="og:title"]')
                content = meta_title.get_attribute('content')
                if ' en ' in content and ' | ' in content:
                    # Format: "Empleo como [title] en [company] | Magneto"
                    parts = content.split(' | ')[0].split(' en ', 1)
                    if len(parts) == 2:
                        job_data['company'] = parts[1].strip()
            except:
                # Fallback to /empresas/ link
                try:
                    company_elem = self.driver.find_element(By.CSS_SELECTOR, 'a[href*="/empresas/"]')
                    company_text = company_elem.text.strip()
                    # The link might contain both title and company, get just the company part
                    if company_text and '\n' in company_text:
                        # Take the last line which is usually the company name
                        company_text = company_text.split('\n')[-1].strip()
                    if company_text:
                        job_data['company'] = company_text
                except:
                    pass

            # Extract location - Magneto shows it in meta description
            try:
                meta_desc = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
                content = meta_desc.get_attribute('content')
                if ' en ' in content and ' con la empresa ' in content:
                    # Format: "Encuentra trabajo como [title] en [location] con la empresa [company]"
                    parts = content.split(' en ', 1)
                    if len(parts) == 2:
                        location_part = parts[1].split(' con la empresa ')[0].strip()
                        job_data['location'] = location_part
            except:
                pass

            # Extract detail items - Magneto shows experience, salary, keywords in specific divs
            try:
                detail_items = self.driver.find_elements(By.CSS_SELECTOR,
                    'div.mg_job_details_magneto-ui-job-details_item-detail_nkmig')

                for item in detail_items:
                    text = item.text.strip()

                    # Check if it's salary (contains numbers and currency-like format)
                    if text and any(char.isdigit() for char in text) and len(text) < 50:
                        # Could be salary like "5.333.000" or date like "Hace 16 minutos"
                        if not 'hace' in text.lower() and not 'experiencia' in text.lower():
                            if not job_data.get('salary_raw'):
                                job_data['salary_raw'] = text

                    # Check if it's experience/requirements
                    if 'experiencia' in text.lower() or 'años' in text.lower():
                        job_data['requirements'] = text

                    # Check if it's keywords (Palabras clave)
                    if 'palabras clave' in text.lower() or len(text) > 100:
                        # This is likely the keywords/skills section
                        if 'palabras clave:' in text.lower():
                            keywords = text.split('Palabras clave:', 1)[1].strip()
                            # Append to requirements
                            if job_data.get('requirements'):
                                job_data['requirements'] += f"\n\nHabilidades: {keywords}"
                            else:
                                job_data['requirements'] = f"Habilidades: {keywords}"

                    # Check if it's posted date
                    if 'hace' in text.lower():
                        job_data['posted_date'] = self.parse_date(text)

            except Exception as e:
                logger.debug(f"Could not extract detail items: {e}")

            # Extract description - Magneto doesn't have detailed descriptions
            # Use keywords as a minimal description if available
            if not job_data.get('description'):
                if job_data.get('requirements'):
                    job_data['description'] = f"Requisitos: {job_data.get('requirements', '')[:500]}"

            # Extract remote type - look in page text
            try:
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                if 'remoto' in page_text or 'trabajo remoto' in page_text:
                    job_data['remote_type'] = 'Remoto'
                elif 'híbrido' in page_text or 'hibrido' in page_text:
                    job_data['remote_type'] = 'Híbrido'
                elif 'presencial' in page_text:
                    job_data['remote_type'] = 'Presencial'
            except Exception as e:
                logger.debug(f"Could not extract remote type: {e}")

            # Extract contract type
            try:
                page_text = self.driver.find_element(By.TAG_NAME, 'body').text.lower()
                if 'tiempo completo' in page_text or 'full time' in page_text:
                    job_data['contract_type'] = 'Tiempo Completo'
                elif 'medio tiempo' in page_text or 'part time' in page_text:
                    job_data['contract_type'] = 'Medio Tiempo'
                elif 'contrato' in page_text:
                    job_data['contract_type'] = 'Contrato'
            except Exception as e:
                logger.debug(f"Could not extract contract type: {e}")

        except Exception as e:
            logger.error(f"Error extracting job details from page: {e}")

        return job_data

    def _parse_job_link_text(self, link_text: str) -> Dict[str, Any]:
        """Parse job information from link text content."""
        job_data = {}

        try:
            # Split the text into lines
            lines = [line.strip() for line in link_text.split('\n') if line.strip()]

            if not lines:
                return job_data

            # Remove timestamp/UI lines
            filtered_lines = []
            for line in lines:
                # Skip timestamp lines
                if any(skip in line.lower() for skip in ['publicado', 'actualizado', 'hace']):
                    if any(time_word in line.lower() for time_word in ['hora', 'minuto', 'día', 'mes', 'ayer', 'hoy', 'semana']):
                        job_data['posted_date'] = self.parse_date(line)
                        continue
                # Skip UI elements
                if any(skip in line.lower() for skip in ['aplicar', 'postular', 'guardar']):
                    continue
                # Skip very short lines
                if len(line) < 3:
                    continue
                filtered_lines.append(line)

            if not filtered_lines:
                return job_data

            # First line is usually the title
            if filtered_lines:
                job_data['title'] = filtered_lines[0]
                filtered_lines = filtered_lines[1:]

            # Second line is often the company
            if filtered_lines:
                second_line = filtered_lines[0]
                if len(second_line) < 100:
                    job_data['company'] = second_line
                    filtered_lines = filtered_lines[1:]

            # Look for location
            for i, line in enumerate(filtered_lines):
                if any(loc_keyword in line.lower() for loc_keyword in
                      ['bogotá', 'medellín', 'cali', 'barranquilla', 'buenos aires', 'capital federal']):
                    if len(line) < 150:
                        job_data['location'] = line
                        filtered_lines.pop(i)
                        break

            # Look for remote type
            for i, line in enumerate(filtered_lines):
                if any(mode in line.lower() for mode in ['remoto', 'presencial', 'híbrido', 'mixto']):
                    if len(line) < 100:
                        job_data['remote_type'] = line.title()
                        filtered_lines.pop(i)
                        break

            # Remaining lines form the description
            if filtered_lines:
                description_text = ' '.join(filtered_lines)
                if len(description_text) > 500:
                    description_text = description_text[:500] + '...'
                job_data['description'] = description_text

        except Exception as e:
            logger.error(f"Error parsing job link text: {e}")

        return job_data

    def cleanup_driver(self):
        """Clean up Selenium WebDriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Selenium WebDriver cleaned up successfully")
            except Exception as e:
                logger.error(f"Error closing driver: {e}")

    def closed(self, reason):
        """Called when spider closes."""
        self.cleanup_driver()
        logger.info(f"Magneto spider closed: {reason}")
        logger.info(f"Total jobs scraped: {len(self.scraped_urls)}")
