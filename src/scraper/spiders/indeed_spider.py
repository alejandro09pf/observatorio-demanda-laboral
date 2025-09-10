"""
Indeed spider for Labor Market Observatory.
Scraper for Indeed Mexico (mx.indeed.com) with Selenium to bypass anti-bot protection.
"""

import os
import re
import time
import random
import logging
from datetime import datetime, timedelta
from urllib.parse import urljoin, quote
from typing import Optional, Set

import scrapy
from .base_spider import BaseSpider
from ..items import JobItem

# Selenium imports
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

# Advanced anti-detection
try:
    import undetected_chromedriver as uc
    UC_AVAILABLE = True
except ImportError:
    UC_AVAILABLE = False
    logger.warning("undetected-chromedriver not available, using standard ChromeDriver")

logger = logging.getLogger(__name__)

# User agents for rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/131.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
]


class IndeedSpider(BaseSpider):
    """Spider for Indeed Mexico job portal."""

    name = "indeed"
    allowed_domains = ["mx.indeed.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "indeed"
        self.country = "MX"
        self.scraped_urls: Set[str] = set()
        self.max_pages = int(kwargs.get('max_pages', 5))
        
        # Search parameters
        self.keyword = kwargs.get('keyword', 'ingeniero en sistemas')
        self.location = kwargs.get('location', '')
        
        # Build base search URL
        self.base_search_url = f"https://mx.indeed.com/jobs?q={quote(self.keyword)}"
        if self.location:
            self.base_search_url += f"&l={quote(self.location)}"
        
        # Proxy failure tracking
        self.proxy_failures = {}
        self.driver = None
        self.page_load_timeout = int(os.getenv("SELENIUM_PAGELOAD_TIMEOUT", "15"))
        
        # Conservative settings for Indeed (using Selenium to bypass anti-bot protection)
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            # Ensure output is saved to JSON file
            'FEEDS': {
                'outputs/indeed_real.json': {
                    'format': 'json',
                    'encoding': 'utf8',
                    'store_empty': False,
                    'indent': 2,
                }
            }
        })

    def get_random_user_agent(self) -> str:
        """Get a random user agent from the list."""
        return random.choice(USER_AGENTS)

    def get_proxy(self) -> Optional[str]:
        """Get proxy from orchestrator's proxy service."""
        try:
            if os.getenv('DISABLE_PROXY', 'false').lower() == 'true':
                logger.info("🔧 Proxy disabled for testing")
                return None
            
            proxy_pool = os.getenv('PROXY_POOL', '')
            if proxy_pool:
                proxies = [p.strip() for p in proxy_pool.split(',') if p.strip()]
                available = [p for p in proxies if self.proxy_failures.get(p, 0) < 3]
                if not available:
                    self.proxy_failures.clear()
                    available = proxies
                return random.choice(available) if available else None
            return None
        except Exception as e:
            logger.warning(f"Could not get proxy: {e}")
            return None

    def _create_chrome_options(self, proxy: str = None) -> Options:
        """Create Chrome options with anti-detection measures."""
        options = Options()
        
        # User-Agent rotation
        ua = self.get_random_user_agent()
        options.add_argument(f"--user-agent={ua}")
        
        # Anti-detection flags
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-features=VizDisplayCompositor")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        options.add_argument("--disable-features=TranslateUI")
        options.add_argument("--disable-ipc-flooding-protection")
        options.add_argument("--disable-background-timer-throttling")
        options.add_argument("--disable-backgrounding-occluded-windows")
        options.add_argument("--disable-renderer-backgrounding")
        options.add_argument("--disable-field-trial-config")
        options.add_argument("--disable-back-forward-cache")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-default-apps")
        options.add_argument("--disable-component-extensions-with-background-pages")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
                "media_stream": 2,
            },
            "profile.managed_default_content_settings": {
                "images": 2
            }
        })
        
        # Proxy
        if proxy:
            options.add_argument(f"--proxy-server=http://{proxy}")
        
        # Run in non-headless mode to avoid detection
        if os.getenv('SELENIUM_HEADLESS', 'false').lower() == 'true':
            options.add_argument("--headless=new")
            logger.warning("⚠️ Running in headless mode - Indeed may block this")
        else:
            logger.info("🔧 Running in non-headless mode to avoid Indeed detection")
        
        return options

    def setup_driver(self):
        """Setup Selenium driver with anti-detection measures."""
        try:
            logger.info("🔧 Setting up anti-detection WebDriver for Indeed...")
            proxy = self.get_proxy()
            
            if UC_AVAILABLE:
                try:
                    logger.info("🚀 Using undetected-chromedriver for maximum stealth...")
                    self.driver = self._setup_undetected_driver(proxy)
                except Exception as e:
                    logger.warning(f"undetected-chromedriver failed: {e}")
                    logger.info("🔧 Falling back to standard ChromeDriver...")
                    self.driver = self._setup_standard_driver(proxy)
            else:
                logger.info("🔧 Using standard ChromeDriver...")
                self.driver = self._setup_standard_driver(proxy)
            
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(10)
            
            # Apply anti-detection measures
            self._apply_stealth_measures()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium driver: {e}")
            raise

    def _setup_undetected_driver(self, proxy=None):
        """Setup undetected-chromedriver."""
        options = uc.ChromeOptions()
        
        # User-Agent rotation
        ua = self.get_random_user_agent()
        options.add_argument(f"--user-agent={ua}")
        
        # Anti-detection options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        
        # Proxy
        if proxy:
            options.add_argument(f"--proxy-server=http://{proxy}")
        
        # Create undetected driver
        try:
            driver = uc.Chrome(options=options, version_main=None)
            logger.info("✅ Created undetected-chromedriver")
            return driver
        except Exception as e:
            logger.error(f"Failed to create undetected driver: {e}")
            raise

    def _setup_standard_driver(self, proxy=None):
        """Setup standard ChromeDriver."""
        options = self._create_chrome_options(proxy)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def _apply_stealth_measures(self):
        """Apply JavaScript stealth measures."""
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Override languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['es-MX','es','en']})",
            
            # Override plugins
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
            
            # Add chrome runtime
            "window.chrome = {runtime: {}}",
            
            # Override platform
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})",
            
            # Override hardware concurrency
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})",
            
            # Remove automation indicators
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array",
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise",
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol",
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.debug(f"Stealth script failed: {e}")
        
        logger.info("✅ Applied stealth measures")

    def closed(self, reason):
        """Clean up driver when spider closes."""
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass
        logger.info(f"🔄 Indeed spider closed: {reason}")
        logger.info(f"📊 Total unique jobs found: {len(self.scraped_urls)}")
        logger.info(f"📄 Total pages processed: {self.current_page}")

    def get_headers(self):
        """Get realistic headers to avoid detection."""
        return {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Referer': 'https://mx.indeed.com/',
        }

    def start_requests(self):
        """Start requests with orchestrator execution check."""
        # Enforce orchestrator-only execution
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                "This spider 'IndeedSpider' can only be executed through the orchestrator.\n"
                "Use: python -m src.orchestrator run-once indeed --country MX\n"
                "Or: python -m src.orchestrator run indeed --country MX"
            )
        
        logger.info(f"🚀 Starting Indeed spider for Mexico")
        logger.info(f"🔍 Search query: {self.keyword}")
        logger.info(f"📍 Location: {self.location or 'All locations'}")
        logger.info(f"📄 Max pages: {self.max_pages}")
        
        # Setup Selenium driver
        self.setup_driver()
        
        # Use Selenium to scrape Indeed
        yield from self.parse_search_results_with_selenium()

    def parse_search_results_with_selenium(self):
        """Parse search results using Selenium."""
        page = 1
        new_jobs_found = True
        
        while page <= self.max_pages and new_jobs_found:
            try:
                # Build URL for current page
                if page == 1:
                    url = self.base_search_url
                else:
                    offset = (page - 1) * 10  # Indeed uses 10 jobs per page
                    url = f"{self.base_search_url}&start={offset}"
                
                logger.info(f"🌐 Loading page {page}: {url}")
                self.driver.get(url)
                
                # Wait for page to load
                time.sleep(random.uniform(3.0, 5.0))
                
                # Apply stealth measures after page load
                self._apply_stealth_measures()
                
                # Wait for job cards to load
                try:
                    wait = WebDriverWait(self.driver, 10)
                    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '[data-jk]')))
                except TimeoutException:
                    logger.warning(f"⚠️ No job cards found on page {page}")
                    break
                
                # Extract job cards
                job_cards = self.driver.find_elements(By.CSS_SELECTOR, '[data-jk]')
                logger.info(f"🔍 Found {len(job_cards)} job cards on page {page}")
                
                if not job_cards:
                    logger.warning(f"⚠️ No job cards found on page {page}")
                    break
                
                num_before = len(self.scraped_urls)
                
                for card in job_cards:
                    try:
                        # Extract job ID
                        jk = card.get_attribute('data-jk')
                        if not jk or jk in self.scraped_urls:
                            continue
                        
                        self.scraped_urls.add(jk)
                        
                        # Extract job information - try multiple selectors for Indeed's structure
                        title = ""
                        job_link = ""
                        
                        # Try different selectors for job title
                        title_selectors = [
                            'h2 a[data-jk]',
                            'h2 a',
                            '.jobTitle a',
                            'a[data-jk]',
                            'a[href*="/viewjob"]'
                        ]
                        
                        for selector in title_selectors:
                            try:
                                title_elem = card.find_element(By.CSS_SELECTOR, selector)
                                title = title_elem.text.strip()
                                job_link = title_elem.get_attribute('href')
                                if title and job_link:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if not title:
                            # Fallback: try to get any text from the card
                            try:
                                title = card.text.strip()[:100]  # First 100 chars
                            except:
                                title = f"Job {jk}"
                        
                        # Extract company - try multiple selectors
                        company = "Company not specified"
                        company_selectors = [
                            '[data-testid="company-name"]',
                            '.companyName',
                            '.company',
                            'span[title]'
                        ]
                        
                        for selector in company_selectors:
                            try:
                                company_elem = card.find_element(By.CSS_SELECTOR, selector)
                                company = company_elem.text.strip() or company_elem.get_attribute('title')
                                if company:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        # Extract location - try multiple selectors
                        location = "Location not specified"
                        location_selectors = [
                            '[data-testid="job-location"]',
                            '.companyLocation',
                            '.location',
                            '.jobLocation'
                        ]
                        
                        for selector in location_selectors:
                            try:
                                location_elem = card.find_element(By.CSS_SELECTOR, selector)
                                location = location_elem.text.strip()
                                if location:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        # Extract snippet - try multiple selectors
                        snippet = ""
                        snippet_selectors = [
                            '.summary',
                            '.job-snippet',
                            '.jobDescription',
                            '.description'
                        ]
                        
                        for selector in snippet_selectors:
                            try:
                                snippet_elem = card.find_element(By.CSS_SELECTOR, selector)
                                snippet = snippet_elem.text.strip()
                                if snippet:
                                    break
                            except NoSuchElementException:
                                continue
                        
                        logger.info(f"➡️ Found job: {title[:50]}... at {company}")
                        
                        # Fetch job detail page with Selenium
                        yield from self._fetch_job_detail_with_selenium(job_link, title, company, location, snippet)
                        
                    except Exception as e:
                        logger.error(f"❌ Error processing job card: {e}")
                        continue
                
                new_jobs_found = len(self.scraped_urls) > num_before
                page += 1
                
                # Wait between pages
                if page <= self.max_pages and new_jobs_found:
                    time.sleep(random.uniform(5.0, 8.0))
                
            except Exception as e:
                logger.error(f"❌ Error processing page {page}: {e}")
                break

    def _fetch_job_detail_with_selenium(self, job_url, title, company, location, snippet):
        """Fetch job detail page using Selenium and parse it."""
        try:
            logger.info(f"🌐 Loading job detail: {job_url}")
            self.driver.get(job_url)
            
            # Wait for page to load
            time.sleep(random.uniform(2.0, 4.0))
            
            # Apply stealth measures
            self._apply_stealth_measures()
            
            # Parse the detail page
            page_source = self.driver.page_source
            from scrapy.http import HtmlResponse
            response = HtmlResponse(url=job_url, body=page_source, encoding='utf-8')
            
            # Use the existing parse_job method
            for item in self.parse_job(response, title, company, location, snippet):
                yield item
                
        except Exception as e:
            logger.error(f"❌ Error fetching job detail {job_url}: {e}")
            
            # Yield fallback item
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = self.portal
                fallback_item['country'] = self.country
                fallback_item['url'] = job_url
                fallback_item['title'] = title or 'Indeed Job Position'
                fallback_item['company'] = company or 'Company Not Found'
                fallback_item['location'] = location or 'Location Not Found'
                fallback_item['description'] = snippet or 'Description not available'
                fallback_item['requirements'] = 'Requirements not available'
                fallback_item['salary_raw'] = ''
                fallback_item['contract_type'] = ''
                fallback_item['remote_type'] = 'No especificado'
                fallback_item['posted_date'] = None
                
                logger.info(f"🔄 Yielding fallback item for {job_url}")
                yield fallback_item
            except Exception as e2:
                logger.error(f"❌ Failed to create fallback item: {e2}")

    def parse_results(self, response):
        """Parse search results page."""
        page = response.meta.get('page', 1)
        logger.info(f"📄 Parsing page {page}: {response.url}")
        
        # Extract job cards using XPath
        job_cards = response.xpath('//main//h2[.//a]/ancestor::*[self::article or self::div][1]')
        logger.info(f"🔍 Found {len(job_cards)} job cards on page {page}")
        
        if not job_cards:
            logger.warning(f"⚠️ No job cards found on page {page}")
            return
        
        new_jobs_found = 0
        
        for card in job_cards:
            try:
                # Extract job information from card
                title_elem = card.xpath('.//h2//a')
                if not title_elem:
                    continue
                
                title = title_elem.xpath('./text()').get()
                if not title:
                    continue
                
                title = self.clean_text(title)
                
                # Extract job link
                relative_link = title_elem.xpath('./@href').get()
                if not relative_link:
                    continue
                
                job_link = response.urljoin(relative_link)
                
                # Extract jk parameter for deduplication
                jk_match = re.search(r'jk=([a-f0-9]+)', job_link)
                if jk_match:
                    jk = jk_match.group(1)
                    if jk in self.scraped_urls:
                        continue
                    self.scraped_urls.add(jk)
                else:
                    # Fallback to full URL
                    if job_link in self.scraped_urls:
                        continue
                    self.scraped_urls.add(job_link)
                
                # Extract company
                company = card.xpath('.//h2//a/following::*[self::span or self::div][1]/text()').get()
                if not company:
                    # Try alternative selectors
                    company = card.xpath('.//*[contains(@class, "company")]//text()').get()
                company = self.clean_text(company) if company else "Company not specified"
                
                # Extract location
                location = card.xpath('.//*[contains(text(), ",")][1]/text()').get()
                if not location:
                    # Try alternative selectors
                    location = card.xpath('.//*[contains(@class, "location")]//text()').get()
                location = self.clean_text(location) if location else "Location not specified"
                
                # Extract snippet (optional)
                snippet = card.xpath('.//ul/li[1]//text() | .//p[1]//text()').get()
                snippet = self.clean_text(snippet) if snippet else ""
                
                logger.info(f"➡️ Found job: {title[:50]}... at {company}")
                
                # Request job detail page
                yield scrapy.Request(
                    url=job_link,
                    callback=self.parse_job,
                    meta={
                        'dont_cache': True,
                        'title': title,
                        'company': company,
                        'location': location,
                        'snippet': snippet
                    },
                    headers=self.get_headers(),
                    errback=self.handle_error
                )
                
                new_jobs_found += 1
                
            except Exception as e:
                logger.error(f"❌ Error processing job card: {e}")
                continue
        
        logger.info(f"✅ Found {new_jobs_found} new jobs on page {page}")
        
        # Pagination
        if page < self.max_pages and new_jobs_found > 0:
            next_offset = page * 10  # Indeed uses 10 jobs per page
            next_url = f"{self.base_search_url}&start={next_offset}"
            
            logger.info(f"➡️ Moving to page {page + 1}: {next_url}")
            
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_results,
                meta={
                    'page': page + 1,
                    'dont_cache': True
                },
                headers=self.get_headers(),
                errback=self.handle_error
            )

    def parse_job(self, response, title=None, company=None, location=None, snippet=None):
        """Parse individual job detail page."""
        try:
            logger.info(f"🔍 Parsing job detail: {response.url}")
            
            # Get pre-extracted data from parameters or meta
            if not title:
                title = response.meta.get('title', '')
            if not company:
                company = response.meta.get('company', '')
            if not location:
                location = response.meta.get('location', '')
            if not snippet:
                snippet = response.meta.get('snippet', '')
            
            # Create JobItem
            item = JobItem()
            item['portal'] = self.portal
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract title (use pre-extracted or parse from page)
            if not title:
                title = response.xpath('//main//h1/text()').get()
                title = self.clean_text(title) if title else "Job Title Not Found"
            item['title'] = title
            
            # Extract company (use pre-extracted or parse from page)
            if not company:
                company = response.xpath('//main//h1/following::*[self::a or self::span][1]/text()').get()
                company = self.clean_text(company) if company else "Company Not Found"
            item['company'] = company
            
            # Extract location (use pre-extracted or parse from page)
            if not location:
                location = response.xpath('//main//h1/following::*[contains(text(), ",")][1]/text()').get()
                location = self.clean_text(location) if location else "Location Not Found"
            item['location'] = location
            
            # Extract salary
            salary = response.xpath('//span[contains(text(), "$") and (contains(text(), "mes") or contains(text(), "semanal"))]/text()').get()
            if not salary:
                # Try alternative selectors
                salary = response.xpath('//*[contains(text(), "Sueldo")]/following::*[1]/text()').get()
            item['salary_raw'] = self.clean_text(salary) if salary else ""
            
            # Extract contract type
            contract_type = response.xpath('//*[contains(text(), "Tipo de empleo")]/following::*[1]/text()').get()
            item['contract_type'] = self.clean_text(contract_type) if contract_type else ""
            
            # Extract schedule
            schedule = response.xpath('//*[contains(text(), "Turno y horario")]/following::*[1]/text()').get()
            item['schedule'] = self.clean_text(schedule) if schedule else ""
            
            # Extract benefits
            benefits = response.xpath('//*[contains(text(), "Beneficios")]/following::ul[1]//li//text()').getall()
            benefits_text = "; ".join([self.clean_text(b) for b in benefits if b.strip()])
            
            # Extract description
            description_parts = response.xpath('//*[contains(text(), "Descripción completa del empleo")]/following::p//text()').getall()
            if not description_parts:
                # Fallback to broader selectors
                description_parts = response.xpath('//main//p//text()').getall()[:5]  # First 5 paragraphs
            
            description = " ".join([self.clean_text(p) for p in description_parts if p.strip()])
            if snippet and not description:
                description = snippet
            item['description'] = description if description else "Description not available"
            
            # Extract requirements
            requirements = response.xpath('//*[contains(text(), "Requisitos")]/following::ul[1]//li//text()').getall()
            if not requirements:
                # Try to extract from description bullet points
                requirements = response.xpath('//main//ul//li[contains(text(), "•") or contains(text(), "-")]//text()').getall()
            
            requirements_text = "; ".join([self.clean_text(r) for r in requirements if r.strip()])
            item['requirements'] = requirements_text if requirements_text else "Requirements not specified"
            
            # Extract posted date
            posted_text = response.xpath('//*[contains(text(), "Hoy") or contains(text(), "Ayer") or contains(text(), "Hace")][1]/text()').get()
            item['posted_date'] = self._normalize_posted_date(posted_text) if posted_text else None
            
            # Extract remote type
            remote_type = ""
            page_text = response.text.lower()
            if "home office" in page_text or "remoto" in page_text:
                remote_type = "Remoto"
            elif "híbrido" in page_text:
                remote_type = "Híbrido"
            elif "presencial" in page_text:
                remote_type = "Presencial"
            else:
                remote_type = "No especificado"
            item['remote_type'] = remote_type
            
            # Validate mandatory fields
            if not item.get('title') or not item.get('company'):
                logger.warning(f"⚠️ Missing mandatory fields for {response.url}")
                return
            
            logger.info(f"✅ Successfully parsed job: {item['title']} at {item['company']}")
            yield item
            
        except Exception as e:
            logger.error(f"❌ Error parsing job detail {response.url}: {e}")
            
            # Yield fallback item
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = self.portal
                fallback_item['country'] = self.country
                fallback_item['url'] = response.url
                fallback_item['title'] = response.meta.get('title', 'Indeed Job Position')
                fallback_item['company'] = response.meta.get('company', 'Company Not Found')
                fallback_item['location'] = response.meta.get('location', 'Location Not Found')
                fallback_item['description'] = f'Error parsing job details: {str(e)[:100]}'
                fallback_item['requirements'] = 'Requirements not available'
                fallback_item['salary_raw'] = ''
                fallback_item['contract_type'] = ''
                fallback_item['remote_type'] = 'No especificado'
                fallback_item['posted_date'] = None
                
                logger.info(f"🔄 Yielding fallback item for {response.url}")
                yield fallback_item
            except Exception as e2:
                logger.error(f"❌ Failed to create fallback item: {e2}")

    def handle_error(self, failure):
        """Handle request errors with retry logic."""
        request = failure.request
        logger.error(f"❌ Request failed: {request.url} - {failure.value}")
        
        # Check if it's a rate limiting or blocking error
        if hasattr(failure.value, 'response') and failure.value.response:
            status = failure.value.response.status
            if status == 403:
                logger.warning(f"⚠️ Indeed blocked the request (HTTP 403) - this is common with Indeed's anti-bot protection")
                logger.warning(f"💡 Consider using Selenium or residential proxies for Indeed")
            elif status == 429:
                logger.warning(f"⚠️ Rate limited (HTTP 429), waiting longer between requests")
            elif status in [500, 502, 503, 504]:
                logger.warning(f"⚠️ Server error (HTTP {status}), will retry")
        else:
            logger.error(f"❌ Network error: {failure.value}")

    def _normalize_posted_date(self, date_text: str) -> Optional[str]:
        """Normalize posted date to ISO format."""
        if not date_text:
            return None
        
        date_text = date_text.strip().lower()
        today = datetime.today().date()
        
        if 'hoy' in date_text:
            return today.isoformat()
        elif 'ayer' in date_text:
            return (today - timedelta(days=1)).isoformat()
        elif 'hace' in date_text:
            # Extract number of days
            days_match = re.search(r'hace\s+(\d+)\s+d[ií]as?', date_text)
            if days_match:
                days = int(days_match.group(1))
                return (today - timedelta(days=days)).isoformat()
        
        # Try to parse absolute dates
        return self.parse_date(date_text)

    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse various date formats to ISO format."""
        if not date_string:
            return None
        
        try:
            # Common Spanish date patterns
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(\d{1,2})-(\d{1,2})-(\d{4})',
                r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})',
            ]
            
            month_map = {
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12',
                'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'
            }
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'de' in pattern:
                        day, month_name, year = match.groups()
                        month = month_map.get(month_name.lower())
                        if month:
                            return f"{year}-{month}-{day.zfill(2)}"
                    else:
                        day, month, year = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
            # Fallback to today
            return datetime.today().date().isoformat()
            
        except Exception:
            return datetime.today().date().isoformat()

    def closed(self, reason):
        """Called when spider is closed."""
        logger.info(f"🔄 Indeed spider closed: {reason}")
        logger.info(f"📊 Total unique jobs found: {len(self.scraped_urls)}")
        logger.info(f"📄 Total pages processed: {self.current_page}")
