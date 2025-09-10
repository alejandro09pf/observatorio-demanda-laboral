"""
OCCMundial spider for Labor Market Observatory.
Enhanced to render dynamic listing pages with Selenium and fetch static detail pages.
"""

import os
import re
import time
import random
import logging
from datetime import datetime, timedelta
from urllib.parse import urlparse
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


class OCCMundialSpider(BaseSpider):
    """Spider for OCCMundial job portal."""

    name = "occmundial"
    allowed_domains = ["occ.com.mx", "www.occ.com.mx"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "occmundial"
        self.scraped_urls: Set[str] = set()
        self.max_pages = int(os.getenv("OCC_MAX_PAGES", "5"))
        self.page_load_timeout = int(os.getenv("SELENIUM_PAGELOAD_TIMEOUT", "15"))
        self.driver = None
        self.proxy_failures = {}
        
        # Enable debug mode if requested
        if os.getenv('SCRAPER_DEBUG_MODE', 'false').lower() == 'true':
            logger.setLevel(logging.DEBUG)
            logger.info("🐛 DEBUG MODE ENABLED - Enhanced logging active")

        # Set start URLs based on country with specific job categories
        if self.country == "MX":
            self.start_urls = [
                "https://www.occ.com.mx/empleos",
            ]
        elif self.country == "CO":
            self.start_urls = [
                "https://co.occ.com.mx/empleos",
            ]
        elif self.country == "AR":
            self.start_urls = [
                "https://ar.occ.com.mx/empleos",
            ]
        else:
            # Default to Mexico
            self.start_urls = [
                "https://www.occ.com.mx/empleos",
            ]

        # Conservative settings; detail pages are static
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            # Ensure output is saved to JSON file
            'FEEDS': {
                'outputs/occ_real.json': {
                    'format': 'json',
                    'encoding': 'utf8',
                    'store_empty': False,
                    'indent': 2,
                }
            }
        })

    # ---------- Selenium setup with proxy and UA rotation ----------
    def get_proxy(self) -> Optional[str]:
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
        options = Options()
        # User-Agent rotation using the same pool as middleware (env file or defaults)
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:132.0) Gecko/20100101 Firefox/132.0',
        ]
        ua = random.choice(ua_list)
        options.add_argument(f"--user-agent={ua}")

        # Enhanced anti-detection flags for OCC
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

        # OCC blocks headless mode, so we need to run in non-headless mode
        # Only use headless if explicitly forced
        if os.getenv('SELENIUM_HEADLESS', 'false').lower() == 'true' and os.getenv('FORCE_HEADLESS', 'false').lower() == 'true':
            options.add_argument("--headless=new")
            logger.warning("⚠️ Running in headless mode - OCC may block this")
        else:
            logger.info("🔧 Running in non-headless mode to avoid OCC detection")

        return options

    def setup_driver(self):
        try:
            logger.info("🔧 Setting up advanced anti-detection WebDriver for OCC...")
            proxy = self.get_proxy()
            
            if UC_AVAILABLE:
                try:
                    logger.info("🚀 Using undetected-chromedriver for maximum stealth...")
                    self.driver = self._setup_undetected_driver(proxy)
                except Exception as e:
                    logger.warning(f"undetected-chromedriver failed: {e}")
                    logger.info("🔧 Falling back to standard ChromeDriver with enhanced stealth...")
                    self.driver = self._setup_standard_driver(proxy)
            else:
                logger.info("🔧 Using standard ChromeDriver with enhanced stealth...")
                self.driver = self._setup_standard_driver(proxy)
            
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(10)
            
            # Apply advanced anti-detection measures
            self._apply_advanced_stealth()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Selenium driver: {e}")
            raise

    def _setup_undetected_driver(self, proxy=None):
        """Setup undetected-chromedriver with advanced stealth."""
        options = uc.ChromeOptions()
        
        # User-Agent rotation
        ua_list = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        ]
        ua = random.choice(ua_list)
        options.add_argument(f"--user-agent={ua}")
        
        # Advanced stealth options
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
        options.add_argument("--disable-client-side-phishing-detection")
        options.add_argument("--disable-hang-monitor")
        options.add_argument("--disable-popup-blocking")
        options.add_argument("--disable-prompt-on-repost")
        options.add_argument("--disable-sync")
        options.add_argument("--disable-domain-reliability")
        options.add_argument("--disable-features=TranslateUI,BlinkGenPropertyTrees")
        options.add_argument("--disable-ipc-flooding-protection")
        
        # Proxy
        if proxy:
            options.add_argument(f"--proxy-server=http://{proxy}")
        
        # Create undetected driver with specific Chrome version
        try:
            # Try with current Chrome version (139)
            driver = uc.Chrome(options=options, version_main=139)
            logger.info("✅ Created undetected-chromedriver with Chrome 139")
            return driver
        except Exception as e:
            logger.warning(f"Failed with Chrome 139: {e}")
            try:
                # Fallback to auto-detection
                driver = uc.Chrome(options=options, version_main=None)
                logger.info("✅ Created undetected-chromedriver with auto-detection")
                return driver
            except Exception as e2:
                logger.error(f"Failed with auto-detection: {e2}")
                raise

    def _setup_standard_driver(self, proxy=None):
        """Setup standard ChromeDriver with enhanced stealth."""
        options = self._create_chrome_options(proxy)
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        return driver

    def _apply_advanced_stealth(self):
        """Apply advanced JavaScript stealth measures."""
        stealth_scripts = [
            # Remove webdriver property
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
            
            # Override languages
            "Object.defineProperty(navigator, 'languages', {get: () => ['es-MX','es','en']})",
            
            # Override plugins
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})",
            
            # Override permissions
            "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})",
            
            # Add chrome runtime
            "window.chrome = {runtime: {}}",
            
            # Override platform
            "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})",
            
            # Override hardware concurrency
            "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})",
            
            # Override device memory
            "Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})",
            
            # Override max touch points
            "Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0})",
            
            # Override connection
            "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 10})})",
            
            # Override battery
            "Object.defineProperty(navigator, 'getBattery', {get: () => () => Promise.resolve({charging: true, chargingTime: 0, dischargingTime: Infinity, level: 1})})",
            
            # Override geolocation
            "Object.defineProperty(navigator, 'geolocation', {get: () => ({getCurrentPosition: () => {}, watchPosition: () => {}, clearWatch: () => {}})})",
            
            # Override media devices
            "Object.defineProperty(navigator, 'mediaDevices', {get: () => ({enumerateDevices: () => Promise.resolve([])})})",
            
            # Remove automation indicators
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array",
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise",
            "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol",
            
            # Override toString methods
            "window.navigator.toString = () => '[object Navigator]'",
            "window.navigator.webdriver.toString = () => 'undefined'",
        ]
        
        for script in stealth_scripts:
            try:
                self.driver.execute_script(script)
            except Exception as e:
                logger.debug(f"Stealth script failed: {e}")
        
        logger.info("✅ Applied advanced stealth measures")

    def _try_accept_cookies(self):
        try:
            # Common cookie banner buttons
            selectors = [
                "button#onetrust-accept-btn-handler",
                "button[aria-label*='aceptar']",
                "button:contains('Aceptar')",
                "button:contains('Aceptar todas')",
                "button[class*='accept']",
            ]
            for sel in selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if btns:
                        btns[0].click()
                        time.sleep(0.5)
                        return
                except Exception:
                    continue
        except Exception:
            return

    def _human_scroll(self, total_scrolls: int = 3):
        try:
            for i in range(total_scrolls):
                # Random scroll amount
                scroll_amount = random.randint(300, 800)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.8, 2.0))
                
                # Sometimes scroll back up a bit
                if random.random() < 0.3:
                    self.driver.execute_script(f"window.scrollBy(0, -{scroll_amount//2});")
                    time.sleep(random.uniform(0.5, 1.0))
        except Exception:
            pass

    def _wait_for_dynamic_content(self, timeout: int = 15):
        """Wait for dynamic content to load with multiple strategies."""
        try:
            logger.info("⏳ Waiting for dynamic content to load...")
            
            # Strategy 1: Wait for any job-related elements
            selectors_to_try = [
                '[data-offers-grid-detail-title]',
                'h2.text-grey-900',
                'p.font-h4-m',
                'div[class*="job"]',
                'div[class*="card"]',
                'article',
                'h2',
                'h3'
            ]
            
            for selector in selectors_to_try:
                try:
                    wait = WebDriverWait(self.driver, 5)
                    elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector)))
                    if elements:
                        logger.info(f"✅ Found {len(elements)} elements with selector: {selector}")
                        return True
                except TimeoutException:
                    continue
            
            # Strategy 2: Wait for JavaScript to load job data
            try:
                wait = WebDriverWait(self.driver, 10)
                wait.until(lambda driver: driver.execute_script("return document.readyState") == "complete")
                
                # Check for job IDs in JavaScript
                page_source = self.driver.page_source
                import re
                job_ids = re.findall(r'oi:\s*[\'"](\d{7,8})[\'"]', page_source)
                if job_ids:
                    logger.info(f"✅ Found {len(job_ids)} job IDs in JavaScript: {job_ids[:3]}")
                    return True
            except TimeoutException:
                pass
            
            # Strategy 3: Wait for specific OCC elements
            try:
                wait = WebDriverWait(self.driver, 10)
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'body')))
                
                # Check if page has loaded properly (not 403)
                if "403" not in self.driver.title and "forbidden" not in self.driver.title.lower():
                    logger.info("✅ Page loaded successfully (no 403 error)")
                    return True
            except TimeoutException:
                pass
            
            logger.warning("⚠️ No dynamic content found after waiting")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for dynamic content: {e}")
            return False

    def closed(self, reason):
        try:
            if self.driver:
                self.driver.quit()
        except Exception:
            pass

    # ---------- Crawl flow ----------
    def start_requests(self):
        # Enforce orchestrator-only execution
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                "This spider 'OCCMundialSpider' can only be executed through the orchestrator.\n"
                "Use: python -m src.orchestrator run-once occmundial --country <COUNTRY>\n"
                "Or: python -m src.orchestrator run occmundial --country <COUNTRY>"
            )
        # Use Selenium to render listing pages and collect detail URLs
        self.setup_driver()
        for base_url in self.start_urls:
            yield from self.parse_search_results_page(base_url)

    def parse_search_results_page(self, url: str):
        logger.info(f"🌐 Loading listing page: {url}")
        page = 1
        new_links_found = True
        while page <= self.max_pages and new_links_found:
            listing_url = url if page == 1 else (f"{url.rstrip('/')}?page={page}")
            try:
                logger.info(f"🌐 Loading page {page}: {listing_url}")
                self.driver.get(listing_url)
                
                # Wait for initial page load
                time.sleep(random.uniform(3.0, 5.0))
                
                # Try to accept cookie consent if present
                self._try_accept_cookies()
                
                # Apply advanced stealth measures after page load
                self._apply_advanced_stealth()
                
                # Wait for dynamic content with multiple strategies
                content_loaded = self._wait_for_dynamic_content()
                
                if not content_loaded:
                    logger.warning(f"⚠️ No dynamic content detected on {listing_url}")
                
                # Enhanced human-like scrolling to trigger dynamic loading
                self._human_scroll(total_scrolls=5)
                
                # Additional wait after scrolling
                time.sleep(random.uniform(3.0, 5.0))
                
                # Try to trigger any lazy loading
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(random.uniform(2.0, 3.0))
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(random.uniform(2.0, 3.0))
                
                # Final wait to ensure all content is loaded
                time.sleep(random.uniform(2.0, 3.0))
            except TimeoutException:
                logger.warning(f"Timeout waiting for job cards on {listing_url}")
                break
            except WebDriverException as e:
                logger.warning(f"Driver error on {listing_url}: {e}")
                break

            # Extract job IDs from JavaScript data in listing page source FIRST
            try:
                page_source = self.driver.page_source
                import re
                
                # Look for job IDs in OCC JavaScript variables and URLs
                js_patterns = [
                    r'oi:\s*[\'"](\d{7,8})[\'"]',  # oi: '20720591'
                    r'OccLytics\.SendEventOcc.*?(\d{7,8})',  # From the analytics call
                    r'/empleo/oferta/(\d{7,8})-',  # Direct URL pattern
                    r'jobid[=:](\d{7,8})',  # jobid=20720591
                    r'window\.conversionData.*?oi:\s*[\'"](\d{7,8})[\'"]',  # From conversion data
                    r'data-id="(\d{7,8})"',  # data-id="20720591"
                    r'"OfferId":"(\d{7,8})"',  # "OfferId":"20720591"
                    r'ID:\s*(\d{7,8})',  # ID: 20720591
                    r'empleo/oferta/(\d{7,8})-',  # URL pattern from OCC
                ]
                
                found_jobids = set()
                for pattern in js_patterns:
                    matches = re.findall(pattern, page_source)
                    found_jobids.update(matches)
                
                logger.info(f"Found {len(found_jobids)} job IDs in JavaScript: {list(found_jobids)[:5]}")
                
                # For each job ID, try to find the corresponding title
                for jobid in found_jobids:
                    if f"https://www.occ.com.mx/empleo/oferta/{jobid}-" in self.scraped_urls:
                        continue
                    
                    # Try to find title near this job ID
                    title_patterns = [
                        rf'ot:\s*[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}.*?oi:\s*[\'"]{jobid}[\'"]',  # ot: 'title' ... oi: 'jobid'
                        rf'oi:\s*[\'"]{jobid}[\'"].*?ot:\s*[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}',  # oi: 'jobid' ... ot: 'title'
                        rf'OccLytics\.SendEventOcc.*?[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}.*?{jobid}',  # From analytics
                    ]
                    
                    title_text = f"Job {jobid}"  # Default fallback
                    for pattern in title_patterns:
                        title_match = re.search(pattern, page_source, re.IGNORECASE | re.DOTALL)
                        if title_match:
                            title_text = title_match.group(1).strip()
                            break
                    
                    # Clean up title
                    title_text = re.sub(r'[^\w\s\-/]', '', title_text).strip()
                    if len(title_text) < 10:
                        title_text = f"Job {jobid}"
                    
                    slug = self._slugify(title_text) or jobid
                    detail_url = f"https://www.occ.com.mx/empleo/oferta/{jobid}-{slug}/"
                    
                    self.scraped_urls.add(detail_url)
                    logger.info(f"➡️ Fetching detail with Selenium (JS): {detail_url} (title: {title_text[:50]})")
                    yield from self._fetch_detail_with_selenium(detail_url, title_text)
                    
            except Exception as e:
                logger.debug(f"JavaScript extraction error: {e}")

            # Extract from OCC-specific DOM elements (multiple strategies)
            job_elements = []
            
            # Strategy 1: Try the specific OCC selectors
            selectors_to_try = [
                '[data-offers-grid-detail-title]',
                'h2.text-grey-900',
                'p.font-h4-m',
                'div[class*="job"]',
                'div[class*="card"]',
                'h2',  # Add h2 as primary selector since our debug found 22 elements
                'h3',
                'article'
            ]
            
            for selector in selectors_to_try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                logger.info(f"🔍 Testing selector '{selector}': found {len(elements)} elements")
                if elements:
                    logger.info(f"✅ Found {len(elements)} elements with selector: {selector}")
                    # Log first few elements for debugging
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()[:50]
                            logger.info(f"  Element {i+1}: {text}")
                        except Exception as e:
                            logger.info(f"  Element {i+1}: [Could not get text: {e}]")
                    job_elements.extend(elements)
                    break  # Use the first successful selector
            
            # If still no elements found, try even broader selectors
            if not job_elements:
                logger.warning("⚠️ No job elements found with primary selectors, trying broader approach...")
                # Try to find any clickable elements that might be job links
                broad_selectors = [
                    'a[href*="/empleo/oferta/"]',
                    'a[href*="jobid="]',
                    'div[class*="title"]',
                    'span[class*="title"]',
                    'p[class*="title"]'
                ]
                for selector in broad_selectors:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"✅ Found {len(elements)} broad elements with selector: {selector}")
                        job_elements.extend(elements)
                        break
            
            logger.info(f"Found {len(job_elements)} job elements on page {page}")
            num_before = len(self.scraped_urls)
            
            for element in job_elements:
                try:
                    # Get job title from the element
                    title_text = element.text.strip()
                    if not title_text or len(title_text) < 10:  # Skip empty or too short titles
                        continue
                    
                    # Look for job ID in the page source around this element
                    # We'll extract from JavaScript data or URL patterns
                    jobid = None
                    
                    # Try to find job ID from the element's parent or nearby elements
                    try:
                        # Look for data attributes or JavaScript variables
                        parent = element.find_element(By.XPATH, "./ancestor::*[contains(@class, 'job') or contains(@class, 'card') or contains(@class, 'item')][1]")
                        jobid_attrs = parent.find_elements(By.XPATH, ".//*[@data-job-id or @data-id or @id]")
                        for attr in jobid_attrs:
                            jobid = attr.get_attribute('data-job-id') or attr.get_attribute('data-id') or attr.get_attribute('id')
                            if jobid and jobid.isdigit():
                                break
                    except:
                        pass
                    
                    # If no job ID found, try to extract from page source using regex
                    if not jobid:
                        page_source = self.driver.page_source
                        import re
                        # Look for job IDs near the title text
                        title_escaped = re.escape(title_text[:50])  # First 50 chars
                        pattern = rf'{title_escaped}.*?(\d{{7,8}})'
                        match = re.search(pattern, page_source, re.IGNORECASE | re.DOTALL)
                        if match:
                            jobid = match.group(1)
                    
                    # If still no job ID, skip this element
                    if not jobid:
                        logger.debug(f"No job ID found for title: {title_text[:50]}")
                        continue
                    
                    slug = self._slugify(title_text) or jobid
                    detail_url = f"https://www.occ.com.mx/empleo/oferta/{jobid}-{slug}/"
                    
                    if detail_url in self.scraped_urls:
                        continue
                    self.scraped_urls.add(detail_url)
                    
                    # Use Selenium to fetch detail page (since Scrapy gets 403)
                    logger.info(f"➡️ Fetching detail with Selenium: {detail_url} (title: {title_text[:50]})")
                    yield from self._fetch_detail_with_selenium(detail_url, title_text)
                except Exception as e:
                    logger.debug(f"Element processing error: {e}")
                    continue

            new_links_found = len(self.scraped_urls) > num_before
            page += 1
            # Rotate driver proxy/UA periodically
            if page % 2 == 0:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.setup_driver()

    # ---------- Static detail parsing ----------
    def parse_detail(self, response):
        try:
            logger.info(f"🔍 Parsing OCC detail: {response.url}")
            
            # Debug: Save page source for analysis
            if os.getenv('SCRAPER_DEBUG_MODE', 'false').lower() == 'true':
                with open(f"debug_detail_{hash(response.url)}.html", "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.debug(f"💾 Saved page source to debug_detail_{hash(response.url)}.html")
            
            item = JobItem()
            item['portal'] = 'occ'
            item['country'] = 'MX'
            item['url'] = response.url

            # Extract title with multiple strategies
            title = response.xpath('//h1/text() | //h2/text() | //title/text()').get()
            logger.debug(f"💡 Raw title from h1/h2/title: {title}")
            
            if not title:
                # Try more specific OCC selectors
                title = response.xpath('//*[@class*="title"]/text() | //*[@data-offers-grid-detail-title]/text()').get()
                logger.debug(f"💡 Raw title from class selectors: {title}")
            
            if not title:
                # Try even broader selectors
                title = response.xpath('//h1//text() | //h2//text() | //h3//text()').get()
                logger.debug(f"💡 Raw title from broad selectors: {title}")
            
            item['title'] = self.clean_text(title) if title else 'OCC Job Position'
            logger.info(f"📝 Final Title: {item['title']}")

            # Extract salary
            salary = response.xpath("//*[contains(text(),'$') and contains(text(),'Mensual')]/text()").get(default='').strip()
            logger.debug(f"💡 Raw salary: {salary}")
            item['salary_raw'] = self.clean_text(salary) if salary else ''

            # Extract company and location with multiple strategies
            comp_loc_line = response.xpath("//*[contains(text(),' en ')]/text()").get(default='')
            logger.debug(f"💡 Raw comp_loc_line: {comp_loc_line}")
            
            company, location = ('', '')
            
            if ' en ' in comp_loc_line:
                parts = comp_loc_line.split(' en ', 1)
                company, location = parts[0].strip(), parts[1].strip()
                logger.debug(f"💡 Split company: {company}, location: {location}")
            else:
                # Try alternative selectors for company
                company = response.xpath('//*[@class*="company"]/text() | //*[contains(@class, "empresa")]/text()').get()
                location = response.xpath('//*[@class*="location"]/text() | //*[contains(@class, "ubicacion")]/text()').get()
                logger.debug(f"💡 Alternative company: {company}, location: {location}")
            
            item['company'] = self.clean_text(company) if company else 'OCC Company'
            item['location'] = self.clean_text(location) if location else 'México'
            logger.info(f"🏢 Final Company: {item['company']}")
            logger.info(f"📍 Final Location: {item['location']}")

            # Extract other fields
            category = response.xpath("//*[contains(text(),'Categoría:')]/following-sibling::text()[1]").get(default='').strip()
            contract = response.xpath("//*[contains(text(),'Contratación')]/following-sibling::text()[1]").get(default='').strip()
            remote = response.xpath("//*[contains(text(),'Espacio de trabajo')]/following-sibling::*[1]/text()").get(default='').strip()

            # Extract description with multiple strategies
            description = ' '.join(response.xpath("//*[contains(text(),'Descripción')]/following::p[1]//text()").getall()).strip()
            if not description:
                description = ' '.join(response.xpath("//*[@class*='description']//text()").getall()).strip()
            if not description:
                description = ' '.join(response.xpath("//p//text()").getall()[:3]).strip()  # First 3 paragraphs

            # Extract requirements
            requirements = '; '.join([self.clean_text(t) for t in response.xpath("//*[contains(text(),'Requisitos')]/following::ul[1]//li//text()").getall() if t.strip()])
            if not requirements:
                requirements = '; '.join([self.clean_text(t) for t in response.xpath("//*[@class*='requirements']//li//text()").getall() if t.strip()])

            # Extract posted date
            posted_text = response.xpath("//*[contains(text(),'Hoy') or contains(text(),'Ayer') or contains(text(),'Hace')][1]/text()").get(default='').strip()
            item['posted_date'] = self._normalize_posted_date(posted_text)

            # Set all fields with defaults
            item['job_category'] = self.clean_text(category) if category else 'General'
            item['contract_type'] = self.clean_text(contract) if contract else 'Tiempo completo'
            item['remote_type'] = self.clean_text(remote) if remote else 'Presencial'
            item['description'] = self.clean_text(description) if description else 'Descripción no disponible'
            item['requirements'] = self.clean_text(requirements) if requirements else 'Requisitos no especificados'

            # Make parse_detail() more tolerant - always yield items
            if not item.get('title') or item.get('title') == '':
                item['title'] = 'OCC Job Position'
                logger.warning(f"⚠️ No title found, using default: {item['title']}")
            
            if not item.get('company') or item.get('company') == '':
                item['company'] = 'OCC Company'
                logger.warning(f"⚠️ No company found, using default: {item['company']}")
            
            if not item.get('location') or item.get('location') == '':
                item['location'] = 'México'
                logger.warning(f"⚠️ No location found, using default: {item['location']}")
            
            # Always yield the item (no validation that would skip it)
            logger.info(f"✅ Yielding item: {item['title']} at {item['company']}")
            yield item
            
        except Exception as e:
            logger.error(f"❌ Error parsing detail {response.url}: {e}")
            
            # Save parsing errors to file
            try:
                with open("failed_urls.txt", "a", encoding="utf-8") as f:
                    f.write(f"{response.url} - ERROR: {e}\n")
                logger.debug(f"💾 Saved error to failed_urls.txt")
            except Exception as save_error:
                logger.error(f"❌ Failed to save error to file: {save_error}")
            
            # Even on error, yield a minimal item to ensure we don't lose the URL
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = 'occ'
                fallback_item['country'] = 'MX'
                fallback_item['url'] = response.url
                fallback_item['title'] = 'OCC Job Position'
                fallback_item['company'] = 'OCC Company'
                fallback_item['location'] = 'México'
                fallback_item['description'] = f'Error parsing job details: {str(e)[:100]}'
                logger.info(f"🔄 Yielding fallback item for {response.url}")
                yield fallback_item
            except Exception as e2:
                logger.error(f"❌ Failed to create fallback item: {e2}")

    # ---------- Helpers ----------
    def _extract_jobid(self, url: str) -> Optional[str]:
        try:
            # Expect query like ?jobid=20721719 or path param
            m = re.search(r"[?&]jobid=(\d+)", url)
            if m:
                return m.group(1)
            m2 = re.search(r"/oferta/(\d+)-", url)
            if m2:
                return m2.group(1)
        except Exception:
            pass
        return None

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        # Replace accents
        replacements = (
            ("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ñ", "n"),
        )
        for src, dst in replacements:
            text = text.replace(src, dst)
        text = re.sub(r"[^a-z0-9\s-]", "", text)
        text = re.sub(r"\s+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text.strip('-')

    def _fetch_detail_with_selenium(self, detail_url: str, title_text: str):
        """Fetch job detail page using Selenium and parse it."""
        try:
            logger.info(f"🌐 Loading detail page: {detail_url}")
            logger.debug(f"💡 Expected title from listing: {title_text}")
            
            self.driver.get(detail_url)
            
            # Reduced wait time for faster scraping
            time.sleep(random.uniform(1.0, 2.0))
            
            # Check if page loaded successfully
            page_title = self.driver.title
            logger.debug(f"💡 Page title: {page_title}")
            
            # Parse the detail page content
            page_source = self.driver.page_source
            logger.debug(f"💡 Page source length: {len(page_source)} characters")
            
            from scrapy.http import HtmlResponse
            response = HtmlResponse(url=detail_url, body=page_source, encoding='utf-8')
            
            # Use the existing parse_detail method
            logger.info(f"🔄 Calling parse_detail for {detail_url}")
            items_yielded = 0
            for item in self.parse_detail(response):
                items_yielded += 1
                logger.info(f"📋 Item {items_yielded} yielded from {detail_url}")
                yield item
            
            if items_yielded == 0:
                logger.warning(f"⚠️ No items yielded from parse_detail for {detail_url}")
            
        except Exception as e:
            logger.error(f"❌ Error fetching detail page {detail_url}: {e}")
            
            # Save error to file
            try:
                with open("failed_urls.txt", "a", encoding="utf-8") as f:
                    f.write(f"{detail_url} - FETCH ERROR: {e}\n")
                logger.debug(f"💾 Saved fetch error to failed_urls.txt")
            except Exception as save_error:
                logger.error(f"❌ Failed to save fetch error to file: {save_error}")
            
            # Yield a fallback item even on error
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = 'occ'
                fallback_item['country'] = 'MX'
                fallback_item['url'] = detail_url
                fallback_item['title'] = title_text or 'OCC Job Position'
                fallback_item['company'] = 'OCC Company'
                fallback_item['location'] = 'México'
                fallback_item['description'] = f'Error loading job details: {str(e)[:100]}'
                logger.info(f"🔄 Yielding fallback item for {detail_url}")
                yield fallback_item
            except Exception as e2:
                logger.error(f"❌ Failed to create fallback item: {e2}")

    def _normalize_posted_date(self, txt: str) -> Optional[str]:
        if not txt:
            return None
        t = txt.strip().lower()
        today = datetime.today().date()
        if 'hoy' in t:
            return today.isoformat()
        if 'ayer' in t:
            return (today - timedelta(days=1)).isoformat()
        m = re.search(r"hace\s+(\d+)\s+d[ií]as", t)
        if m:
            days = int(m.group(1))
            return (today - timedelta(days=days)).isoformat()
        # Fallback to existing absolute parser
        return self.parse_date(txt)

    def parse_date(self, date_string: str) -> Optional[str]:
        if not date_string:
            return None
        try:
            date_patterns = [
                r'Publicado (\d{1,2}) (\w+) (\d{4})',
                r'(\d{1,2})/(\d{1,2})/(\d{4})',
                r'(\d{1,2})-(\d{1,2})-(\d{4})',
                r'(\d{1,2}) de (\w+) de (\d{4})',
                r'(\d{1,2})/(\d{1,2})/(\d{2})',
            ]
            month_map = {
                'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12',
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }
            for pattern in date_patterns:
                m = re.search(pattern, date_string, re.IGNORECASE)
                if not m:
                    continue
                d, mth, y = m.groups()
                if pattern.endswith('(\\d{2})'):
                    y = f"20{y}" if int(y) < 50 else f"19{y}"
                if mth.isdigit():
                    month_num = mth.zfill(2)
                else:
                    month_num = month_map.get(mth.lower()[:3])
                if month_num:
                    return f"{y}-{month_num}-{str(d).zfill(2)}"
            return datetime.today().date().isoformat()
        except Exception:
            return datetime.today().date().isoformat()
