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
        self.limit = int(kwargs.get('limit', 0))  # 0 = unlimited
        self._emitted = 0
        
        # Set keyword and location from kwargs (optional)
        self.keyword = kwargs.get('keyword', '')
        self.location = kwargs.get('location', '')

        # Build base search URL - Indeed requires a search term to show job listings
        if self.keyword:
            self.base_search_url = f"https://mx.indeed.com/jobs?q={quote(self.keyword)}"
            if self.location:
                self.base_search_url += f"&l={quote(self.location)}"
        else:
            # Use a more specific search term to get job listings
            self.base_search_url = "https://mx.indeed.com/jobs?q=ingeniero"
            if self.location:
                self.base_search_url += f"&l={quote(self.location)}"
        
        # Proxy failure tracking
        self.proxy_failures = {}
        self.driver = None
        self.page_load_timeout = int(os.getenv("SELENIUM_PAGELOAD_TIMEOUT", "15"))
        
        # Fast test mode and detail fetching options
        self.fast = os.getenv("FAST_TEST", "false").lower() == "true"
        self.detail_via_selenium = os.getenv("DETAIL_VIA_SELENIUM", "false").lower() == "true"
        
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
    
    def _sleep(self, lo, hi):
        """Sleep with fast test mode support."""
        delay = random.uniform(lo, hi)
        if self.fast:
            delay = 0.3
        time.sleep(delay)
    
    def _canonicalize_job_url(self, url: str) -> str:
        """Normalize job URLs to canonical /viewjob?jk=... format"""
        if not url:
            return url
        try:
            m = re.search(r'[?&]jk=([a-f0-9]+)', url)
            if m:
                return f'https://mx.indeed.com/viewjob?jk={m.group(1)}'
        except Exception:
            pass
        return url
    
    def first_text(self, el, css):
        """Get first matching element's text, avoiding exceptions."""
        try:
            nodes = el.find_elements(By.CSS_SELECTOR, css)
            return nodes[0].text.strip() if nodes else ""
        except Exception:
            return ""
    
    def safe_following_text(self, response, label_substring):
        """Safely extract text following a label, avoiding scripts/styles."""
        xp = (
            f'//*[not(self::script or self::style) and '
            f'contains(normalize-space(.), "{label_substring}")]'
            f'/following-sibling::*[1][not(self::script or self::style)]//text()'
        )
        t = response.xpath(xp).get()
        return self.clean_text(t) if t else ""
    
    def _handle_banners_and_geo(self):
        """Handle OneTrust cookie banner and other modals that block interaction."""
        # OneTrust cookie banner
        try:
            btns = self.driver.find_elements(By.CSS_SELECTOR, "#onetrust-accept-btn-handler, button#onetrust-accept-btn-handler, button[aria-label*='Aceptar'], button[aria-label*='Accept']")
            if btns:
                btns[0].click()
                time.sleep(0.8)
        except Exception:
            pass

        # Close any modal/overlay that blocks interaction (common on Indeed)
        try:
            close_btns = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='Cerrar'], button[aria-label*='close'], .icl-CloseButton")
            if close_btns:
                for b in close_btns:
                    try:
                        b.click()
                        time.sleep(0.3)
                    except Exception:
                        continue
        except Exception:
            pass
    
    def _wait_for_results(self, timeout=20):
        """Wait for job results to appear using current Indeed markers."""
        wait = WebDriverWait(self.driver, timeout, poll_frequency=0.5)
        # Wait for *either* of these to appear
        try:
            wait.until(
                EC.any_of(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "h2.jobTitle a.jcs-JobTitle")),
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.job_seen_beacon"))
                )
            )
            return True
        except TimeoutException:
            return False
    
    def _stabilize_results(self):
        """Stabilize results by triggering lazy loaded content."""
        # small scrolls to trigger lazy content
        for y in (400, 900, 1400):
            try:
                self.driver.execute_script(f"window.scrollTo(0,{y});")
                time.sleep(0.6)
            except Exception:
                break
        # final settle
        time.sleep(0.8)
    
    def _blocked_by_indeed(self) -> bool:
        """Detect if blocked by captcha or unusual activity detection."""
        html = self.driver.page_source.lower()
        needles = [
            "unusual activity", "actividad inusual",
            "are you a robot", "captcha", "verifica que no eres un robot",
            "access denied"
        ]
        return any(n in html for n in needles)

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
            self.driver.implicitly_wait(0)  # Disable implicit waits for speed
            
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
        logger.info(f"📄 Total pages processed: {getattr(self, 'current_page', 0)}")

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
        if self.keyword:
            logger.info(f"🔍 Search query: {self.keyword}")
        else:
            logger.info(f"🔍 Using general search term: 'ingeniero'")
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
                self._sleep(3, 5)
                
                # Apply stealth measures after page load
                self._apply_stealth_measures()
                
                # Handle banners and geo modals
                self._handle_banners_and_geo()
                
                # Wait for results to appear
                if not self._wait_for_results(timeout=20):
                    logger.warning(f"⚠️ Results not visible yet on page {page}")
                    # Save the HTML for inspection
                    debug_file = f"debug_indeed_page_{page}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"🔍 Saved page source to {debug_file} for debugging")
                    if self._blocked_by_indeed():
                        logger.warning("⚠️ Looks like an anti-bot block (captcha/verification). Try proxies or wait & retry.")
                    break
                
                # Stabilize results by triggering lazy loaded content
                self._stabilize_results()
                
                # Primary card container
                cards = self.driver.find_elements(By.CSS_SELECTOR, "div.job_seen_beacon")
                if not cards:
                    # Fallback: collect by title links and walk up to the card container
                    title_links = self.driver.find_elements(By.CSS_SELECTOR, "h2.jobTitle a.jcs-JobTitle")
                    cards = []
                    for a in title_links:
                        try:
                            container = a.find_element(By.XPATH, "./ancestor::div[contains(@class,'job_seen_beacon')][1]")
                            cards.append(container)
                        except Exception:
                            # fallback to the <article> if present
                            try:
                                container = a.find_element(By.XPATH, "./ancestor::article[1]")
                                cards.append(container)
                            except Exception:
                                continue

                logger.info(f"🔍 Found {len(cards)} job cards on page {page}")
                if not cards:
                    # Save and exit early
                    debug_file = f"debug_indeed_page_{page}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"🔍 Saved page source to {debug_file} for debugging")
                    break
                
                num_before = len(self.scraped_urls)
                
                # Extract each card
                job_data_list = []
                for card in cards:
                    # Hard stop before processing if limit reached
                    if self.limit and self._emitted >= self.limit:
                        logger.info(f"Reached limit={self.limit}, stopping.")
                        break
                    
                    try:
                        # title + link
                        a = card.find_element(By.CSS_SELECTOR, "h2.jobTitle a.jcs-JobTitle")
                        title = (a.get_attribute("aria-label") or a.text or "").strip()
                        job_link = a.get_attribute("href") or ""

                        # company
                        company = ""
                        for sel in ("span.companyName", "[data-testid='company-name']"):
                            try:
                                company = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if company:
                                    break
                            except NoSuchElementException:
                                continue
                        if not company:
                            company = "Company not specified"

                        # location
                        location = ""
                        for sel in ("div.companyLocation", "[data-testid='job-location']"):
                            try:
                                location = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if location:
                                    break
                            except NoSuchElementException:
                                continue
                        if not location:
                            location = "Location not specified"

                        # snippet
                        snippet = ""
                        for sel in (".job-snippet", ".jobDescription", ".resultContent p"):
                            try:
                                snippet = card.find_element(By.CSS_SELECTOR, sel).text.strip()
                                if snippet:
                                    break
                            except NoSuchElementException:
                                continue

                        if not job_link and title:
                            # last resort: build from jk in href of any descendant link
                            try:
                                any_a = card.find_element(By.CSS_SELECTOR, "a[href*='viewjob']")
                                job_link = any_a.get_attribute("href")
                            except Exception:
                                pass

                        if not job_link:
                            logger.debug("Skipping a card without link")
                            continue
                        
                        # Canonicalize job URL to avoid tracking redirects
                        job_link = self._canonicalize_job_url(job_link)

                        # Extract jk for deduplication
                        import re
                        jk = re.search(r"jk=([a-f0-9]+)", job_link).group(1) if "jk=" in job_link else job_link
                        
                        if jk in self.scraped_urls:
                            continue
                        self.scraped_urls.add(jk)

                        job_data_list.append({
                            "jk": jk,
                            "title": title,
                            "job_link": job_link,
                            "company": company,
                            "location": location,
                            "snippet": snippet
                        })
                        logger.info(f"➡️ {title[:60]} — {company} — {location}")
                    except Exception as e:
                        logger.debug(f"Card parse failed: {e}")
                        continue
                
                # Process each job's detail page
                use_selenium_detail = os.getenv("DETAIL_VIA_SELENIUM", "true").lower() != "false"
                
                for jd in job_data_list:
                    if use_selenium_detail:
                        try:
                            yield from self._fetch_job_detail_with_selenium(
                                jd["job_link"], jd["title"], jd["company"], jd["location"], jd["snippet"]
                            )
                        except Exception as e:
                            logger.error(f" Error fetching detail for job {jd['jk']}: {e}")
                            # Yield basic item as fallback
                            basic_item = JobItem()
                            basic_item['portal'] = self.portal
                            basic_item['country'] = self.country
                            basic_item['url'] = jd['job_link']
                            basic_item['title'] = jd['title']
                            basic_item['company'] = jd['company']
                            basic_item['location'] = jd['location']
                            basic_item['description'] = jd['snippet'] or 'Description not available'
                            basic_item['requirements'] = 'Requirements not available'
                            basic_item['salary_raw'] = ''
                            basic_item['contract_type'] = ''
                            basic_item['remote_type'] = 'No especificado'
                            basic_item['posted_date'] = None
                            yield basic_item
                    else:
                        # Use Scrapy requests for faster processing
                        canon = self._canonicalize_job_url(jd["job_link"])
                        yield scrapy.Request(
                            url=canon,
                            callback=self.parse_job,
                            meta={
                                "title": jd["title"],
                                "company": jd["company"],
                                "location": jd["location"],
                                "snippet": jd["snippet"],
                                "dont_cache": True,
                                "dont_proxy": True
                            },
                            headers=self.get_headers(),
                            errback=self.handle_error
                        )
                
                new_jobs_found = len(self.scraped_urls) > num_before
                page += 1
                
                # Wait between pages
                if page <= self.max_pages and new_jobs_found:
                    self._sleep(5, 8)
                
            except Exception as e:
                logger.error(f"❌ Error processing page {page}: {e}")
                break

    def _fetch_job_detail_with_selenium(self, job_url, title, company, location, snippet):
        """Fetch job detail page using Selenium and parse it."""
        try:
            # Canonicalize job URL to avoid tracking redirects
            job_url = self._canonicalize_job_url(job_url)
            
            # Validate URL
            if not job_url or job_url.strip() == "":
                logger.warning(f"⚠️ Empty job URL, skipping detail fetch")
                # Yield basic item with available data
                basic_item = JobItem()
                basic_item['portal'] = self.portal
                basic_item['country'] = self.country
                basic_item['url'] = f"https://mx.indeed.com/viewjob?jk={list(self.scraped_urls)[-1]}" if self.scraped_urls else ""
                basic_item['title'] = title or 'Indeed Job Position'
                basic_item['company'] = company or 'Company Not Found'
                basic_item['location'] = location or 'Location Not Found'
                basic_item['description'] = snippet or 'Description not available'
                basic_item['requirements'] = 'Requirements not available'
                basic_item['salary_raw'] = ''
                basic_item['contract_type'] = ''
                basic_item['remote_type'] = 'No especificado'
                basic_item['posted_date'] = None
                yield basic_item
                return
            
            logger.info(f"🌐 Loading job detail: {job_url}")
            self.driver.get(job_url)
            
            # Wait for page to load
            self._sleep(2, 4)
            
            # Apply stealth measures
            self._apply_stealth_measures()
            
            # Remove noisy nodes (scripts, styles) to prevent JS contamination
            self.driver.execute_script("""
                for (const n of document.querySelectorAll('script,style,noscript')) n.remove();
            """)
            
            # Parse the detail page
            page_source = self.driver.page_source
            from scrapy.http import HtmlResponse, Request
            
            # Create a proper Request with meta data
            req = Request(job_url, headers=self.get_headers(), dont_filter=True)
            req.meta.update({'title': title, 'company': company, 'location': location, 'snippet': snippet})
            
            response = HtmlResponse(
                url=job_url,
                body=page_source.encode('utf-8'),
                encoding='utf-8',
                request=req
            )
            
            # Use the existing parse_job method with pre-extracted data
            for item in self.parse_job(response, title, company, location, snippet):
                yield item
                
        except Exception as e:
            logger.error(f"❌ Error fetching job detail {job_url}: {e}")
            
            # Yield fallback item with proper URL
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = self.portal
                fallback_item['country'] = self.country
                fallback_item['url'] = job_url if job_url else f"https://mx.indeed.com/viewjob?jk={list(self.scraped_urls)[-1]}" if self.scraped_urls else ""
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
            
            # Use the pre-extracted data passed as parameters
            # (No need to check response.meta since we pass data directly)
            
            # Create JobItem
            item = JobItem()
            item['portal'] = self.portal
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract title (use pre-extracted or parse from page)
            if not title:
                title_selectors = [
                    '//main//h1/text()',
                    '//h1/text()',
                    '//*[@data-testid="job-title"]/text()',
                    '//title/text()'
                ]
                for selector in title_selectors:
                    title = response.xpath(selector).get()
                    if title:
                        break
                title = self.clean_text(title) if title else "Job Title Not Found"
            item['title'] = title
            
            # Clean up title - remove "detalles completos de" prefix
            item['title'] = re.sub(r'^detalles completos de\s+', '', item['title'], flags=re.I).strip()
            
            # Extract company (use pre-extracted or parse from page)
            if not company or company == "Company not specified":
                company_selectors = [
                    '//main//h1/following::*[self::a or self::span][1]/text()',
                    '//*[@data-testid="company-name"]/text()',
                    '//*[contains(@class, "company")]//text()',
                    '//*[contains(text(), "Company")]/following::text()[1]'
                ]
                for selector in company_selectors:
                    company = response.xpath(selector).get()
                    if company and company.strip():
                        break
                company = self.clean_text(company) if company else "Company Not Found"
            item['company'] = company
            
            # Extract location (use pre-extracted or parse from page)
            if not location or location == "Location not specified":
                location_selectors = [
                    '//main//h1/following::*[contains(text(), ",")][1]/text()',
                    '//*[@data-testid="job-location"]/text()',
                    '//*[contains(@class, "location")]//text()',
                    '//*[contains(text(), "Location")]/following::text()[1]'
                ]
                for selector in location_selectors:
                    location = response.xpath(selector).get()
                    if location and location.strip():
                        break
                location = self.clean_text(location) if location else "Location Not Found"
            item['location'] = location
            
            # Extract salary - prefer structured area and avoid scripts/styles
            salary = response.xpath(
                '//*[@id="salaryInfoAndJobType"]//*[self::span or self::div]'
                '[contains(normalize-space(.), "$")]'
                '[not(ancestor::script) and not(ancestor::style)]//text()'
            ).get()

            if not salary:
                # Label-based fallback, but only to the next *sibling* and never scripts/styles
                salary = response.xpath(
                    '//*[not(self::script or self::style) and '
                    '(contains(translate(normalize-space(.),"SALARIOSUELDO","salariosueldo"),"sueldo") or '
                    ' contains(translate(normalize-space(.),"SALARIO","salario"),"salario"))]'
                    '/following-sibling::*[1][not(self::script or self::style)]//text()'
                ).get()

            salary = self.clean_text(salary) if salary else ""

            # Final sanity check: drop obviously bad values
            if salary and (len(salary) > 120 or re.search(r'\b(window|mosaic|function)\b', salary)):
                salary = ""

            item['salary_raw'] = salary
            
            # Extract contract type
            contract_type = response.xpath(
                '//*[contains(normalize-space(.),"Tipo de empleo")]'
                '/following-sibling::*[1][not(self::script or self::style)]//text()'
            ).get()

            if not contract_type:
                # Try to read from inline JSON (jobTypes labels) if present
                script_blob = response.xpath('//script[contains(., "jobTypes")][1]/text()').get()
                if script_blob:
                    labels = re.findall(r'"jobTypes"\s*:\s*\[(.*?)\]', script_blob, flags=re.S)
                    if labels:
                        ct = re.findall(r'"label"\s*:\s*"([^"]+)"', labels[0])
                        if ct:
                            contract_type = "; ".join(ct)

            contract_type = self.clean_text(contract_type) if contract_type else ""
            item['contract_type'] = contract_type
            
            # Extract schedule (not stored in JobItem, just for logging)
            schedule = response.xpath('//*[contains(text(), "Turno y horario")]/following::*[1]/text()').get()
            schedule = self.clean_text(schedule) if schedule else ""
            
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
            
            # Ensure mandatory fields have fallbacks
            if not item.get('title'):
                item['title'] = title or 'Indeed Job Position'
            if not item.get('company'):
                item['company'] = company or 'Company Not Found'
            
            # Check limit before yielding
            if self.limit and self._emitted >= self.limit:
                return
            
            logger.info(f"✅ Successfully parsed job: {item['title']} at {item['company']}")
            yield item
            self._emitted += 1
            
        except Exception as e:
            logger.error(f"❌ Error parsing job detail {response.url}: {e}")
            
            # Yield fallback item using passed parameters instead of response.meta
            try:
                fallback_item = JobItem()
                fallback_item['portal'] = self.portal
                fallback_item['country'] = self.country
                fallback_item['url'] = response.url
                fallback_item['title'] = title or 'Indeed Job Position'
                fallback_item['company'] = company or 'Company Not Found'
                fallback_item['location'] = location or 'Location Not Found'
                fallback_item['description'] = (snippet or 'Description not available')[:1000]
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

