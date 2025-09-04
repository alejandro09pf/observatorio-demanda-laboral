"""
Bumeran spider for Labor Market Observatory.
Scrapes job listings from https://www.bumeran.com.mx/empleos.html using undetected-chromedriver for advanced anti-detection.
"""

import os
import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
import random
import time
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional, List, Dict
import logging
import json
import yaml
from pathlib import Path

# Advanced anti-detection imports
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

logger = logging.getLogger(__name__)

class BumeranSpider(BaseSpider):
    """Enhanced Bumeran spider using undetected-chromedriver and human-like behavior."""
    
    name = "bumeran"
    allowed_domains = ["bumeran.com.mx"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "bumeran"
        
        # Force Mexico as specified
        self.country = "MX"
        
        # Base URL for Mexico
        self.base_url = "https://www.bumeran.com.mx/empleos.html"
        
        # Enhanced anti-detection setup
        self.driver = None
        self.wait_timeout = 20
        self.page_load_timeout = 45
        self.scraped_urls = set()
        
        # Human behavior simulation
        self.min_delay = 2
        self.max_delay = 8
        self.mouse_movement_probability = 0.7
        
        # Proxy configuration
        self.proxy_pools = self._load_proxy_pools()
        self.current_proxy = None
        self.proxy_failures = {}
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 5,  # Conservative delay to avoid detection
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Single request at a time for Selenium
        })
    
    def _get_chrome_version(self) -> int:
        """Get the current Chrome browser version."""
        try:
            import subprocess
            import re
            
            # Try to get Chrome version from command line
            if os.name == 'nt':  # Windows
                cmd = r'reg query "HKEY_CURRENT_USER\Software\Google\Chrome\BLBeacon" /v version'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.returncode == 0:
                    match = re.search(r'version\s+REG_SZ\s+(\d+)\.', result.stdout)
                    if match:
                        return int(match.group(1))
                
                # Alternative: check Program Files
                chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                ]
                
                for path in chrome_paths:
                    if os.path.exists(path):
                        result = subprocess.run([path, '--version'], capture_output=True, text=True)
                        if result.returncode == 0:
                            match = re.search(r'Chrome\s+(\d+)\.', result.stdout)
                            if match:
                                return int(match.group(1))
            
            # Fallback: return current version from error message
            logger.warning("⚠️ Could not detect Chrome version, using fallback")
            return 139
            
        except Exception as e:
            logger.warning(f"⚠️ Error detecting Chrome version: {e}")
            return 139
    
    def _load_proxy_pools(self) -> Dict[str, List[str]]:
        """Load residential proxy pools from configuration."""
        try:
            # Try to load from YAML config first
            config_path = Path("config/proxies.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    logger.info(f"✅ Loaded proxy configuration from {config_path}")
                    return config.get('proxy_pools', {})
            
            # Fallback to environment variables
            import os
            proxy_pool = os.getenv('PROXY_POOL', '')
            if proxy_pool:
                proxies = [p.strip() for p in proxy_pool.split(',') if p.strip()]
                return {'residential': proxies}
            
            logger.warning("⚠️ No proxy configuration found, will run without proxies")
            return {}
            
        except Exception as e:
            logger.error(f"❌ Error loading proxy configuration: {e}")
            return {}
    
    def _get_residential_proxy(self) -> Optional[str]:
        """Get a residential proxy from the pool."""
        if not self.proxy_pools:
            return None
        
        # For now, return None to test without proxies
        # TODO: Implement working proxy rotation when real proxies are available
        logger.info("🌐 Temporarily running without proxies for testing")
        return None
        
        # Original proxy logic (commented out for testing)
        """
        # Prioritize residential proxies
        for pool_name, proxies in self.proxy_pools.items():
            if 'residential' in pool_name.lower() or 'premium' in pool_name.lower():
                available_proxies = [p for p in proxies if self.proxy_failures.get(p, 0) < 3]
                if available_proxies:
                    proxy = random.choice(available_proxies)
                    logger.info(f"🌐 Using {pool_name} proxy: {proxy[:30]}...")
                    return proxy
        
        # Fallback to any available proxy
        for pool_name, proxies in self.proxy_pools.items():
            available_proxies = [p for p in proxies if self.proxy_failures.get(p, 0) < 3]
            if available_proxies:
                proxy = random.choice(available_proxies)
                logger.info(f"🌐 Using fallback {pool_name} proxy: {proxy[:30]}...")
                return proxy
        
        logger.warning("⚠️ No available proxies found")
        return None
        """
    
    def _mark_proxy_failed(self, proxy: str):
        """Mark a proxy as failed."""
        if proxy:
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            logger.warning(f"⚠️ Proxy {proxy[:30]}... marked as failed (attempts: {self.proxy_failures[proxy]})")
    
    def _human_delay(self, min_seconds: float = None, max_seconds: float = None):
        """Simulate human-like random delays."""
        min_delay = min_seconds or self.min_delay
        max_delay = max_seconds or self.max_delay
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"⏳ Human delay: {delay:.2f} seconds")
        time.sleep(delay)
    
    def _human_mouse_movement(self, driver):
        """Simulate human-like mouse movements."""
        if random.random() < self.mouse_movement_probability:
            try:
                # Get page dimensions
                page_width = driver.execute_script("return document.body.scrollWidth")
                page_height = driver.execute_script("return document.body.scrollHeight")
                
                # Generate random coordinates
                x = random.randint(100, min(page_width - 100, 800))
                y = random.randint(100, min(page_height - 100, 600))
                
                # Perform mouse movement
                actions = ActionChains(driver)
                actions.move_by_offset(x, y)
                actions.perform()
                
                logger.debug(f"🖱️ Human mouse movement to ({x}, {y})")
                
            except Exception as e:
                logger.debug(f"Mouse movement failed: {e}")
    
    def _human_scroll(self, driver):
        """Simulate human-like scrolling behavior."""
        try:
            # Random scroll amount
            scroll_amount = random.randint(100, 500)
            
            # Random scroll direction (mostly down, sometimes up)
            if random.random() < 0.8:
                driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                logger.debug(f"📜 Human scroll down: {scroll_amount}px")
            else:
                driver.execute_script(f"window.scrollBy(0, -{scroll_amount});")
                logger.debug(f"📜 Human scroll up: {scroll_amount}px")
            
            # Small delay after scrolling
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.debug(f"Human scroll failed: {e}")
    
    def _human_typing(self, element, text: str):
        """Simulate human-like typing with random delays."""
        try:
            element.clear()
            for char in text:
                element.send_keys(char)
                # Random delay between characters
                time.sleep(random.uniform(0.05, 0.15))
            logger.debug(f"⌨️ Human typing: {text[:20]}...")
        except Exception as e:
            logger.debug(f"Human typing failed: {e}")
            element.send_keys(text)
    
    def _create_chrome_options(self, proxy: str = None) -> uc.ChromeOptions:
        """Create fresh Chrome options for each driver attempt."""
        options = uc.ChromeOptions()
        
        # Basic anti-detection options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins-discovery")
        options.add_argument("--disable-web-security")
        options.add_argument("--allow-running-insecure-content")
        
        # Window size (randomize slightly)
        width = random.randint(1200, 1400)
        height = random.randint(800, 1000)
        options.add_argument(f"--window-size={width},{height}")
        
        # User agent rotation
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"--user-agent={random.choice(user_agents)}")
        
        # Add proxy if available
        if proxy:
            options.add_argument(f'--proxy-server={proxy}')
            logger.info(f"🌐 Using proxy: {proxy[:30]}...")
        
        return options
    
    def setup_driver(self):
        """Setup undetected-chromedriver with advanced anti-detection."""
        try:
            logger.info("🔧 Setting up undetected-chromedriver...")
            
            # Get residential proxy
            proxy = self._get_residential_proxy()
            self.current_proxy = proxy
            
            # Create undetected-chromedriver instance
            logger.info("🔧 Creating undetected-chromedriver...")
            
            # Try multiple approaches to create the driver
            driver_created = False
            
            # Approach 1: Try with webdriver-manager for version compatibility
            try:
                logger.info("🔧 Trying webdriver-manager approach...")
                from webdriver_manager.chrome import ChromeDriverManager
                from selenium.webdriver.chrome.service import Service
                
                # Get compatible ChromeDriver
                driver_path = ChromeDriverManager().install()
                logger.info(f"✅ ChromeDriver installed at: {driver_path}")
                
                # Create options and service
                options = self._create_chrome_options(proxy)
                service = Service(driver_path)
                
                # Try with undetected-chromedriver using the service
                self.driver = uc.Chrome(
                    service=service,
                    options=options,
                    headless=False,
                    use_subprocess=True
                )
                driver_created = True
                logger.info("✅ Driver created successfully with webdriver-manager")
                
            except Exception as wdm_error:
                logger.warning(f"⚠️ Webdriver-manager approach failed: {wdm_error}")
                
                # Approach 2: Try with undetected-chromedriver auto-detection
                if not driver_created:
                    try:
                        logger.info("🔧 Trying undetected-chromedriver auto-detection...")
                        options = self._create_chrome_options(proxy)
                        self.driver = uc.Chrome(
                            options=options,
                            version_main=None,  # Auto-detect Chrome version
                            headless=False,
                            use_subprocess=True
                        )
                        driver_created = True
                        logger.info("✅ Driver created successfully with auto-detection")
                        
                    except Exception as auto_error:
                        logger.warning(f"⚠️ Auto-detection failed: {auto_error}")
                        
                        # Approach 3: Try with specific Chrome version
                        if not driver_created:
                            try:
                                chrome_version = self._get_chrome_version()
                                logger.info(f"🔧 Trying with Chrome version: {chrome_version}")
                                
                                options = self._create_chrome_options(proxy)
                                self.driver = uc.Chrome(
                                    options=options,
                                    version_main=chrome_version,
                                    headless=False,
                                    use_subprocess=True
                                )
                                driver_created = True
                                logger.info("✅ Driver created successfully with specific version")
                                
                            except Exception as version_error:
                                logger.error(f"❌ Specific version failed: {version_error}")
                                
                                # Approach 4: Final fallback
                                if not driver_created:
                                    try:
                                        logger.info("🔧 Trying final fallback...")
                                        options = self._create_chrome_options(proxy)
                                        self.driver = uc.Chrome(
                                            options=options,
                                            headless=False,
                                            use_subprocess=True
                                        )
                                        driver_created = True
                                        logger.info("✅ Driver created successfully with fallback")
                                        
                                    except Exception as fallback_error:
                                        logger.error(f"❌ All driver creation attempts failed: {fallback_error}")
                                        raise fallback_error
            
            if not driver_created:
                raise RuntimeError("Failed to create driver with any approach")
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(10)
            
            # Execute additional anti-detection scripts
            logger.info("🔧 Executing advanced anti-detection scripts...")
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['es-MX', 'es', 'en']})")
            self.driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            self.driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
            
            logger.info("✅ Undetected-chromedriver setup completed successfully")
            return self.driver
            
        except Exception as e:
            logger.error(f"❌ Error setting up undetected-chromedriver: {e}")
            if proxy:
                self._mark_proxy_failed(proxy)
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return False
    
    def get_proxy(self):
        """Get proxy from orchestrator's proxy service."""
        return self.current_proxy
    
    def start_requests(self):
        """Start requests by initializing undetected-chromedriver and navigating to the start URL."""
        # Check execution lock BEFORE starting requests
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                f"This spider '{self.__class__.__name__}' can only be executed through the orchestrator.\n"
                f"Use: python -m src.orchestrator run-once {self.__class__.__name__.lower()} --country <COUNTRY>\n"
                f"Or: python -m src.orchestrator run {self.__class__.__name__.lower()} --country <COUNTRY>"
            )
        
        logger.info("🔧 Setting up undetected-chromedriver...")
        driver = self.setup_driver()
        
        if not driver:
            logger.error("❌ Failed to setup undetected-chromedriver")
            return
        elif driver is False:
            logger.error("❌ Driver setup returned False")
            return
        else:
            logger.info(f"✅ Driver setup successful: {type(driver)}")
        
        # Store driver in spider instance
        self.driver = driver
        
        logger.info(f"🚀 Starting enhanced Bumeran spider for Mexico")
        logger.info(f"🔗 Base URL: {self.base_url}")
        
        try:
            # Start scraping from page 1
            logger.info("📄 Attempting to parse page 1...")
            for item in self.parse_search_results_page(1):
                logger.info(f"📋 Yielding item: {item.get('title', 'No title')[:50]}...")
                yield item
        except Exception as e:
            logger.error(f"❌ Error during parsing: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
        finally:
            logger.info("🧹 Cleaning up driver...")
            self.cleanup_driver()
    
    def cleanup_driver(self):
        """Clean up undetected-chromedriver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Driver cleaned up successfully")
            except Exception as e:
                logger.error(f"❌ Error quitting driver: {e}")
            finally:
                self.driver = None
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.cleanup_driver()
    
    def parse_search_results_page(self, page):
        """Parse a single page of search results with human-like behavior."""
        try:
            logger.info(f"🔍 Starting to parse page {page}")
            
            # Navigate to the page
            url = f"{self.base_url}?page={page}"
            logger.info(f"🔗 Navigating to: {url}")
            
            # Human-like navigation
            self.driver.get(url)
            self._human_delay(3, 6)  # Wait like a human
            
            # Simulate human behavior while page loads
            self._human_mouse_movement(self.driver)
            self._human_scroll(self.driver)
            
            logger.info("✅ Navigation completed")
            
            # Wait for page to load with human-like patience
            logger.info("⏳ Waiting for page to load with human-like behavior...")
            page_load_result = self.wait_for_page_load_human()
            logger.info(f"📄 Page load result: {page_load_result}")
            
            if not page_load_result:
                logger.error(f"❌ Page load failed on page {page}")
                return []
            
            # Check for Cloudflare challenge
            if self.check_cloudflare_challenge():
                logger.warning(f"⚠️ Cloudflare challenge detected on page {page}, attempting human-like resolution...")
                if not self.resolve_cloudflare_human():
                    logger.error(f"❌ Cloudflare challenge not resolved on page {page}")
                    return []
            
            # Look for job cards using the correct selector
            logger.info("🔍 Looking for job cards...")
            job_cards = self.driver.find_elements("css selector", "a.sc-ljUfdc.ldTLfe")
            
            if not job_cards:
                logger.warning(f"⚠️ No job cards found on page {page} - page may be empty")
                # Save page source for debugging
                page_source = self.driver.page_source
                logger.info(f"📄 Page source length: {len(page_source)} characters")
                logger.info(f"🔗 Current URL: {self.driver.current_url}")
                return []
            
            logger.info(f"✅ Found {len(job_cards)} job cards on page {page}")
            
            # Human-like processing of job cards
            results = []
            for i, card in enumerate(job_cards):
                try:
                    logger.info(f"🔍 Processing card {i+1}/{len(job_cards)}")
                    
                    # Simulate human reading behavior
                    self._human_delay(0.5, 1.5)
                    self._human_mouse_movement(self.driver)
                    
                    # Extract job information from the card
                    job_data = self.extract_job_from_card(card)
                    if job_data:
                        results.append(job_data)
                        logger.info(f"✅ Card {i+1} processed successfully")
                    else:
                        logger.warning(f"⚠️ Card {i+1} returned no data")
                        
                except Exception as e:
                    logger.error(f"❌ Error extracting job from card {i+1}: {e}")
                    continue
            
            logger.info(f"✅ Successfully extracted {len(results)} jobs from page {page}")
            return results
            
        except Exception as e:
            logger.error(f"❌ Error parsing search results page {page}: {e}")
            import traceback
            logger.error(f"📋 Traceback: {traceback.format_exc()}")
            return []
    
    def wait_for_page_load_human(self, timeout=60):
        """Wait for page to load with human-like behavior patterns."""
        start_time = time.time()
        logger.info("⏳ Waiting for page to load with human-like behavior...")
        
        while time.time() - start_time < timeout:
            try:
                page_source = self.driver.page_source
                current_url = self.driver.current_url
                
                # Check if we're still on the target page
                if self.base_url not in current_url and "bumeran.com.mx" not in current_url:
                    logger.warning(f"⚠️ Redirected to unexpected URL: {current_url}")
                    return False
                
                # Check for Cloudflare challenge and attempt advanced resolution
                if self.check_cloudflare_challenge():
                    logger.info("⚠️ Cloudflare challenge detected, attempting advanced resolution...")
                    if self.resolve_cloudflare_human():
                        logger.info("✅ Cloudflare challenge resolved during page load wait")
                        # After Cloudflare resolution, wait for actual content to load
                        logger.info("⏳ Waiting for content to load after Cloudflare resolution...")
                        self._human_delay(5, 10)
                        
                        # Try to wait for job cards to appear with explicit waits
                        try:
                            wait = WebDriverWait(self.driver, 20)
                            job_cards = wait.until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, "a.sc-ljUfdc.ldTLfe"))
                            )
                            logger.info("✅ Job cards appeared after Cloudflare resolution")
                            return True
                        except TimeoutException:
                            logger.info("⏳ Job cards not yet visible, continuing to wait...")
                        
                        continue
                    else:
                        logger.warning("⚠️ Cloudflare challenge not resolved during page load wait")
                        # Continue waiting but with longer delays
                        self._human_delay(8, 12)
                        continue
                
                # Enhanced content detection after Cloudflare resolution
                # Check for actual job cards presence
                try:
                    job_cards = self.driver.find_elements("css selector", "a.sc-ljUfdc.ldTLfe")
                    if job_cards and len(job_cards) > 0:
                        logger.info(f"✅ Found {len(job_cards)} job cards - page fully loaded")
                        return True
                except Exception as e:
                    logger.debug(f"Error checking job cards: {e}")
                
                # Check if page has substantial content
                if len(page_source) > 50000:  # Page seems to have content
                    logger.info("✅ Page loaded successfully with substantial content")
                    return True
                
                # Check for specific job-related content
                if any(keyword in page_source.lower() for keyword in ['empleo', 'trabajo', 'puesto', 'vacante']):
                    logger.info("✅ Page loaded with job-related content")
                    return True
                
                # Human-like behavior while waiting
                self._human_delay(2, 4)
                self._human_mouse_movement(self.driver)
                self._human_scroll(self.driver)
                
            except Exception as e:
                logger.debug(f"Error checking page load: {e}")
                self._human_delay(2, 4)
        
        logger.warning("⚠️ Page load timeout reached")
        return False
    
    def resolve_cloudflare_human(self):
        """Advanced Cloudflare challenge resolution with multiple sophisticated techniques."""
        try:
            logger.info("🔧 Starting advanced Cloudflare challenge resolution...")
            
            # Phase 1: Enhanced human-like behavior
            if self._phase1_cloudflare_resolution():
                return True
            
            # Phase 2: Advanced browser manipulation
            if self._phase2_cloudflare_resolution():
                return True
            
            # Phase 3: JavaScript challenge solving
            if self._phase3_cloudflare_resolution():
                return True
            
            # Phase 4: Cookie and session manipulation
            if self._phase4_cloudflare_resolution():
                return True
            
            # Phase 5: Final aggressive attempts
            if self._phase5_cloudflare_resolution():
                return True
            
            logger.warning("⚠️ All Cloudflare resolution phases failed")
            return False
            
        except Exception as e:
            logger.error(f"❌ Error in advanced Cloudflare resolution: {e}")
            return False
    
    def _phase1_cloudflare_resolution(self):
        """Phase 1: Enhanced human-like behavior patterns."""
        try:
            logger.info("🔧 Phase 1: Enhanced human-like behavior...")
            
            # Extended waiting with progressive delays
            wait_times = [8, 12, 15, 20]
            for wait_time in wait_times:
                logger.info(f"⏳ Waiting {wait_time} seconds...")
                self._human_delay(wait_time, wait_time + 2)
                
                # Complex mouse movement patterns
                self._complex_mouse_patterns()
                
                # Advanced scrolling behavior
                self._advanced_scrolling_behavior()
                
                # Check if resolved
                if not self.check_cloudflare_challenge():
                    logger.info("✅ Phase 1 successful: Cloudflare challenge resolved")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Phase 1 failed: {e}")
            return False
    
    def _phase2_cloudflare_resolution(self):
        """Phase 2: Advanced browser manipulation and fingerprinting."""
        try:
            logger.info("🔧 Phase 2: Advanced browser manipulation...")
            
            # Execute advanced anti-detection scripts
            anti_detection_scripts = [
                # Hide automation indicators
                "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;",
                "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;",
                "delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;",
                
                # Override permissions API
                "Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})});",
                
                # Override connection API
                "Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 10})});",
                
                # Override canvas fingerprinting
                "HTMLCanvasElement.prototype.toDataURL = function() { return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=='; };",
                
                # Override WebGL fingerprinting
                "WebGLRenderingContext.prototype.getParameter = function(parameter) { if (parameter === 37445) return 'Intel Inc.'; if (parameter === 37446) return 'Intel(R) Iris(TM) Graphics 6100'; return this._getParameter ? this._getParameter(parameter) : null; };",
            ]
            
            for script in anti_detection_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Script execution failed: {e}")
            
            # Simulate browser interactions
            self._simulate_browser_interactions()
            
            # Check if resolved
            if not self.check_cloudflare_challenge():
                logger.info("✅ Phase 2 successful: Cloudflare challenge resolved")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Phase 2 failed: {e}")
            return False
    
    def _phase3_cloudflare_resolution(self):
        """Phase 3: JavaScript challenge solving and automation detection bypass."""
        try:
            logger.info("🔧 Phase 3: JavaScript challenge solving...")
            
            # Try to find and solve JavaScript challenges
            challenge_scripts = [
                # Override Cloudflare specific objects
                """
                if (typeof window.__CF$cv$params !== 'undefined') {
                    window.__CF$cv$params = 'r=0&m=0&s=0&u=0&i=0&b=0&f=0&p=0&c=0&w=0&v=0&d=0&h=0&t=0&l=0&a=0&o=0&n=0&x=0&y=0&z=0';
                }
                """,
                
                # Override timing functions
                """
                const originalSetTimeout = window.setTimeout;
                const originalSetInterval = window.setInterval;
                
                window.setTimeout = function(fn, delay, ...args) {
                    if (delay < 100) delay = 100;
                    return originalSetTimeout(fn, delay, ...args);
                };
                """,
            ]
            
            for script in challenge_scripts:
                try:
                    self.driver.execute_script(script)
                except Exception as e:
                    logger.debug(f"Challenge script failed: {e}")
            
            # Wait for JavaScript execution
            self._human_delay(5, 10)
            
            # Check if resolved
            if not self.check_cloudflare_challenge():
                logger.info("✅ Phase 3 successful: Cloudflare challenge resolved")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Phase 3 failed: {e}")
            return False
    
    def _phase4_cloudflare_resolution(self):
        """Phase 4: Cookie and session manipulation."""
        try:
            logger.info("🔧 Phase 4: Cookie and session manipulation...")
            
            # Clear problematic cookies
            try:
                cookies = self.driver.get_cookies()
                for cookie in cookies:
                    if any(keyword in cookie['name'].lower() for keyword in ['cf_', 'cloudflare', 'challenge', 'captcha']):
                        self.driver.delete_cookie(cookie['name'])
                        logger.debug(f"Deleted cookie: {cookie['name']}")
            except Exception as e:
                logger.debug(f"Cookie manipulation failed: {e}")
            
            # Set helpful cookies
            helpful_cookies = [
                {'name': 'cf_clearance', 'value': 'test', 'domain': '.bumeran.com.mx'},
                {'name': 'cf_use_ob', 'value': '0', 'domain': '.bumeran.com.mx'},
            ]
            
            for cookie in helpful_cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Cookie setting failed: {e}")
            
            # Refresh page to apply cookie changes
            try:
                self.driver.refresh()
                self._human_delay(3, 6)
            except Exception as e:
                logger.debug(f"Page refresh failed: {e}")
            
            # Check if resolved
            if not self.check_cloudflare_challenge():
                logger.info("✅ Phase 4 successful: Cloudflare challenge resolved")
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Phase 4 failed: {e}")
            return False
    
    def _phase5_cloudflare_resolution(self):
        """Phase 5: Final aggressive attempts and fallback strategies."""
        try:
            logger.info("🔧 Phase 5: Final aggressive attempts...")
            
            # Try multiple page reloads with different strategies
            reload_strategies = [
                # Strategy 1: Force reload
                lambda: self.driver.execute_script("window.location.reload(true);"),
                
                # Strategy 2: Navigate to different URL then back
                lambda: self.driver.get("https://www.bumeran.com.mx/") and self._human_delay(2, 4) and self.driver.get(self.base_url),
                
                # Strategy 3: Clear cache and reload
                lambda: self.driver.execute_script("window.location.reload();") and self.driver.execute_script("window.localStorage.clear(); window.sessionStorage.clear();"),
            ]
            
            for i, strategy in enumerate(reload_strategies):
                try:
                    logger.info(f"🔧 Trying reload strategy {i+1}...")
                    strategy()
                    self._human_delay(5, 10)
                    
                    # Check if resolved
                    if not self.check_cloudflare_challenge():
                        logger.info(f"✅ Phase 5 successful with strategy {i+1}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Strategy {i+1} failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Phase 5 failed: {e}")
            return False
    
    def _complex_mouse_patterns(self):
        """Execute complex mouse movement patterns to simulate human behavior."""
        try:
            # Get page dimensions
            page_width = self.driver.execute_script("return document.body.scrollWidth")
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Create complex movement patterns
            patterns = [
                # Circular pattern
                lambda: self._draw_circle_mouse_movement(page_width, page_height),
                # Zigzag pattern
                lambda: self._draw_zigzag_mouse_movement(page_width, page_height),
                # Random walk pattern
                lambda: self._draw_random_walk_mouse_movement(page_width, page_height),
            ]
            
            for pattern in patterns:
                try:
                    pattern()
                    self._human_delay(0.5, 1.5)
                except Exception as e:
                    logger.debug(f"Mouse pattern failed: {e}")
                    
        except Exception as e:
            logger.debug(f"Complex mouse patterns failed: {e}")
    
    def _draw_circle_mouse_movement(self, page_width, page_height):
        """Draw a circle with mouse movements."""
        try:
            center_x = page_width // 2
            center_y = page_height // 2
            radius = min(page_width, page_height) // 4
            
            actions = ActionChains(self.driver)
            for angle in range(0, 360, 10):
                x = center_x + int(radius * math.cos(math.radians(angle)))
                y = center_y + int(radius * math.sin(math.radians(angle)))
                actions.move_by_offset(x, y)
            
            actions.perform()
        except Exception as e:
            logger.debug(f"Circle mouse movement failed: {e}")
    
    def _draw_zigzag_mouse_movement(self, page_width, page_height):
        """Draw a zigzag pattern with mouse movements."""
        try:
            actions = ActionChains(self.driver)
            for x in range(100, page_width - 100, 50):
                y = 100 + (x // 50) % 2 * 100
                actions.move_by_offset(x, y)
            
            actions.perform()
        except Exception as e:
            logger.debug(f"Circle mouse movement failed: {e}")
    
    def _draw_random_walk_mouse_movement(self, page_width, page_height):
        """Draw a random walk pattern with mouse movements."""
        try:
            actions = ActionChains(self.driver)
            x, y = page_width // 2, page_height // 2
            
            for _ in range(20):
                dx = random.randint(-50, 50)
                dy = random.randint(-50, 50)
                x = max(100, min(page_width - 100, x + dx))
                y = max(100, min(page_height - 100, y + dy))
                actions.move_by_offset(x, y)
            
            actions.perform()
        except Exception as e:
            logger.debug(f"Random walk mouse movement failed: {e}")
    
    def _advanced_scrolling_behavior(self):
        """Execute advanced scrolling behavior patterns."""
        try:
            # Get page dimensions
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Advanced scrolling patterns
            scroll_patterns = [
                # Smooth scroll down
                lambda: self.driver.execute_script(f"window.scrollTo({{top: {page_height//4}, behavior: 'smooth'}});"),
                # Jump scroll
                lambda: self.driver.execute_script(f"window.scrollTo(0, {page_height//2});"),
                # Random scroll positions
                lambda: self.driver.execute_script(f"window.scrollTo(0, {random.randint(100, page_height-100)});"),
            ]
            
            for pattern in scroll_patterns:
                try:
                    pattern()
                    self._human_delay(0.5, 1.5)
                except Exception as e:
                    logger.debug(f"Scroll pattern failed: {e}")
                    
        except Exception as e:
            logger.debug(f"Advanced scrolling failed: {e}")
    
    def _simulate_browser_interactions(self):
        """Simulate various browser interactions to appear more human."""
        try:
            # Simulate window focus/blur
            self.driver.execute_script("window.focus();")
            self._human_delay(0.5, 1)
            self.driver.execute_script("window.blur();")
            self._human_delay(0.5, 1)
            self.driver.execute_script("window.focus();")
            
            # Simulate mouse enter/leave events
            self.driver.execute_script("""
                const event = new MouseEvent('mouseenter', {
                    bubbles: true,
                    cancelable: true,
                    view: window
                });
                document.body.dispatchEvent(event);
            """)
            
        except Exception as e:
            logger.debug(f"Browser interactions failed: {e}")
    
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
                "Please wait while we verify",
                "DDoS protection by Cloudflare",
                "Just a moment..."
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking Cloudflare challenge: {e}")
            return False
    
    def extract_job_from_card(self, job_card):
        """Extract basic job information from job card."""
        try:
            job_data = {}
            
            # Extract title from h2 with class sc-jIWCYS cRJTXs
            try:
                title_elem = job_card.find_element(By.CSS_SELECTOR, "h2.sc-jIWCYS.cRJTXs")
                job_data['title'] = title_elem.text.strip()
            except NoSuchElementException:
                # Fallback to any h2
                try:
                    title_elem = job_card.find_element(By.CSS_SELECTOR, "h2")
                    job_data['title'] = title_elem.text.strip()
                except NoSuchElementException:
                    logger.warning("Could not find title in job card")
                    return None
            
            # Extract URL from the job card itself (it's an <a> tag)
            job_data['url'] = job_card.get_attribute("href")
            
            # Extract company from h3 with class sc-ezgcVH bpwAJM (or similar)
            try:
                company_elem = job_card.find_element(By.CSS_SELECTOR, "h3.sc-ezgcVH.bpwAJM, h3.sc-crZBWn.jArxxf, h3.sc-JqSnb.kiuIQu, h3.sc-cagiPt.eGOOnS, h3.sc-hEpDqx.hFwEwf, h3.sc-bzWdZj.iktiF, h3.sc-fLGdtL.hCrGud, h3.sc-dibpSh.eosMnL, h3.sc-kidJrC.dmvgiX, h3.sc-gIbWsZ.bOctwe, h3.sc-fRVxeA.ixsRRo, h3.sc-exlezd.fiJoyz, h3.sc-bpOlVg.hgrUsn, h3.sc-bCEHqE.ipdLmq, h3.sc-fbNrFI.jIlEKb, h3.sc-fRCFMq.gHDXds, h3.sc-gMbazw.czrWfJ, h3.sc-bhKohJ.htgddS, h3.sc-cWAGMr.hDNdpN, h3.sc-cyxpkx.iOzuCE")
                job_data['company'] = company_elem.text.strip()
            except NoSuchElementException:
                # Fallback to any h3
                try:
                    company_elem = job_card.find_element(By.CSS_SELECTOR, "h3")
                    job_data['company'] = company_elem.text.strip()
                except NoSuchElementException:
                    job_data['company'] = ""
            
            # Extract location from [aria-label="location"] or similar
            try:
                location_elem = job_card.find_element(By.CSS_SELECTOR, "[aria-label='location'], .sc-lffWgi.ealzkR h3")
                job_data['location'] = location_elem.text.strip()
            except NoSuchElementException:
                job_data['location'] = ""
            
            # Extract short description from p with class sc-gDeQiw cxkncc (or similar)
            try:
                desc_elem = job_card.find_element(By.CSS_SELECTOR, "p.sc-gDeQiw.cxkncc, p.sc-ejSpPi.ckYRfy, p.sc-jjbMYL.gRgpML, p.sc-bQwXya.dmIkML, p.sc-jmUTF.glHNjB, p.sc-dxcOqk.jaIxgP, p.sc-TfVrH.bquxUy, p.sc-ivORUo.ixHUD")
                job_data['description'] = desc_elem.text.strip()
            except NoSuchElementException:
                # Fallback to any p
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
    
    def validate_job_item(self, item: JobItem) -> bool:
        """Validate job item has required fields."""
        required_fields = ['title', 'company', 'portal', 'country']
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        return True
