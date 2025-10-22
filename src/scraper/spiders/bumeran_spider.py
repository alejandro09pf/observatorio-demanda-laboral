"""
Bumeran spider - OPTIMIZED VERSION.
Simplified Selenium approach with minimal anti-detection overhead.
Target: 200-300 jobs/hour with efficient page processing.
"""

import os
import scrapy
from urllib.parse import urljoin
from datetime import datetime
import re
import random
import time
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional
import logging

# Simplified Selenium imports
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)


class BumeranSpider(BaseSpider):
    """Optimized Bumeran spider with minimal overhead."""

    name = "bumeran"
    allowed_domains = ["bumeran.com.mx"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "bumeran"
        self.country = "MX"
        self.base_url = "https://www.bumeran.com.mx/empleos.html"

        self.driver = None
        self.wait_timeout = 15
        self.scraped_urls = set()

        logger.info("🚀 OPTIMIZED Bumeran spider initialized")
        logger.info(f"🎯 Target: ~250 jobs/hora (streamlined processing)")

        # Simplified settings
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 3,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        })

    def _setup_driver(self):
        """Setup undetected-chromedriver with minimal configuration."""
        try:
            logger.info("🔧 Setting up driver...")

            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument(f"--window-size={random.randint(1200,1400)},{random.randint(800,1000)}")

            user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            ]
            options.add_argument(f"--user-agent={random.choice(user_agents)}")

            self.driver = uc.Chrome(
                options=options,
                headless=False,
                use_subprocess=True
            )

            self.driver.set_page_load_timeout(30)
            self.driver.implicitly_wait(5)

            logger.info("✅ Driver setup complete")
            return True

        except Exception as e:
            logger.error(f"❌ Driver setup failed: {e}")
            return False

    def start_requests(self):
        """Start scraping."""
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                f"This spider can only be executed through the orchestrator.\n"
                f"Use: python -m src.orchestrator run-once bumeran --country MX"
            )

        if not self._setup_driver():
            logger.error("❌ Driver setup failed, aborting")
            return

        logger.info(f"🚀 Starting Bumeran scraper for {self.country}")

        try:
            for page in range(1, min(self.max_pages + 1, 51)):  # Cap at 50 pages
                logger.info(f"📄 Processing page {page}")

                for item in self._scrape_page(page):
                    yield item

                # Polite delay between pages
                time.sleep(random.uniform(2, 4))

        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            self._cleanup_driver()

    def _scrape_page(self, page):
        """Scrape a single page."""
        try:
            url = f"{self.base_url}?page={page}"
            logger.info(f"🔗 Navigating to: {url}")

            self.driver.get(url)
            time.sleep(random.uniform(5, 8))  # Longer initial wait (Best Practice 2025)

            # Multi-phase Cloudflare handling (Based on working version)
            max_retries = 5  # Increased from 3
            for attempt in range(max_retries):
                if self._is_cloudflare_challenge():
                    logger.warning(f"⚠️ Cloudflare detected (attempt {attempt+1}/{max_retries})")

                    # Phase 1: Long wait (Proven to work)
                    wait_time = 12 + (attempt * 4)  # 12s, 16s, 20s, 24s, 28s
                    logger.info(f"⏳ Waiting {wait_time}s...")
                    time.sleep(wait_time)

                    # Phase 2: Human-like interactions
                    try:
                        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                        time.sleep(random.uniform(1, 2))
                        self.driver.execute_script("window.scrollTo(0, 0);")
                        time.sleep(random.uniform(0.5, 1))
                    except Exception as e:
                        logger.debug(f"Scroll failed: {e}")

                    # Phase 3: Cookie manipulation (Phase 4 from working version)
                    if attempt >= 2:  # Try cookies from attempt 3 onwards
                        logger.info("🔧 Attempting cookie manipulation...")
                        try:
                            # Clear Cloudflare cookies
                            cookies = self.driver.get_cookies()
                            for cookie in cookies:
                                if any(kw in cookie['name'].lower() for kw in ['cf_', 'cloudflare', 'challenge']):
                                    self.driver.delete_cookie(cookie['name'])
                                    logger.debug(f"Deleted cookie: {cookie['name']}")

                            # Refresh page
                            self.driver.refresh()
                            time.sleep(random.uniform(5, 8))
                        except Exception as e:
                            logger.debug(f"Cookie manipulation failed: {e}")

                    # Check if resolved
                    if not self._is_cloudflare_challenge():
                        logger.info(f"✅ Cloudflare resolved after {attempt+1} attempts!")
                        break
                else:
                    # Cloudflare resolved
                    logger.info("✅ No Cloudflare detected, proceeding")
                    break

            # Final check
            if self._is_cloudflare_challenge():
                logger.error("❌ Cloudflare still present after all retries, skipping page")
                return []

            # Find job cards - Try multiple selectors
            job_cards = []
            selectors = [
                "a.sc-ljUfdc.ldTLfe",  # Original
                "a[href*='/empleos/']",  # Generic job links
                "div[data-testid='job-card'] a",  # Modern structure
                "article a",  # Article-based
                "a[class*='job']",  # Any class containing 'job'
            ]

            for selector in selectors:
                try:
                    job_cards = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if len(job_cards) > 0:
                        logger.info(f"✅ Found {len(job_cards)} job cards using selector: {selector}")
                        break
                except TimeoutException:
                    logger.debug(f"Selector '{selector}' found no results")
                    continue

            if not job_cards:
                logger.warning(f"⏰ No job cards found with any selector on page {page}")
                # Debug: Save page source
                logger.info("💾 Saving page source for debugging...")
                with open(f"bumeran_debug_page{page}.html", "w", encoding="utf-8") as f:
                    f.write(self.driver.page_source)
                logger.info(f"💾 Page source saved to bumeran_debug_page{page}.html")
                return []

            logger.info(f"✅ Processing {len(job_cards)} job cards")

            results = []
            for i, card in enumerate(job_cards):
                try:
                    job_data = self._extract_from_card(card)
                    if job_data:
                        results.append(job_data)
                        logger.info(f"✅ Extracted job {i+1}/{len(job_cards)}: {job_data['title'][:50]}")
                except Exception as e:
                    logger.error(f"❌ Error extracting job {i+1}: {e}")
                    continue

            return results

        except Exception as e:
            logger.error(f"❌ Error scraping page {page}: {e}")
            return []

    def _is_cloudflare_challenge(self):
        """Check if Cloudflare challenge is present."""
        try:
            page_source = self.driver.page_source
            indicators = ["Cloudflare", "challenge-platform", "Checking your browser"]
            return any(ind in page_source for ind in indicators)
        except:
            return False

    def _extract_from_card(self, card):
        """Extract job data from card element."""
        try:
            # Title
            try:
                title = card.find_element(By.CSS_SELECTOR, "h2").text.strip()
            except NoSuchElementException:
                logger.warning("No title found")
                return None

            # URL
            url = card.get_attribute("href")

            if url in self.scraped_urls:
                return None

            self.scraped_urls.add(url)

            # Company - more specific selectors, avoiding date text
            company = ""
            try:
                # Try specific company selectors first
                company_elem = None
                selectors = [
                    "[data-testid='company-name']",
                    ".company-name",
                    "h3[class*='company']",
                    "span[class*='company']",
                    "div[class*='company']"
                ]
                for selector in selectors:
                    try:
                        company_elem = card.find_element(By.CSS_SELECTOR, selector)
                        company = company_elem.text.strip()
                        if company and not any(word in company.lower() for word in ['publicado', 'hace', 'días', 'horas']):
                            break
                    except:
                        continue

                # If still no company or it looks like a date, try h3 but validate
                if not company or any(word in company.lower() for word in ['publicado', 'hace', 'días']):
                    try:
                        h3_text = card.find_element(By.CSS_SELECTOR, "h3").text.strip()
                        # Only use h3 if it doesn't look like a date
                        if h3_text and not any(word in h3_text.lower() for word in ['publicado', 'hace', 'días', 'horas']):
                            company = h3_text
                    except:
                        pass
            except NoSuchElementException:
                pass

            # Location - try multiple selectors
            location = ""
            try:
                location_selectors = [
                    "[aria-label='location']",
                    "[data-testid='location']",
                    ".location",
                    "span[class*='location']",
                    "div[class*='ubicacion']"
                ]
                for selector in location_selectors:
                    try:
                        location = card.find_element(By.CSS_SELECTOR, selector).text.strip()
                        if location:
                            break
                    except:
                        continue
            except NoSuchElementException:
                pass

            # Description - more specific
            description = ""
            try:
                desc_selectors = [
                    "p[class*='description']",
                    "div[class*='description']",
                    ".job-description",
                    "p"  # fallback to generic p
                ]
                for selector in desc_selectors:
                    try:
                        desc_elem = card.find_element(By.CSS_SELECTOR, selector)
                        desc_text = desc_elem.text.strip()
                        # Make sure it's not the date text
                        if desc_text and not any(word in desc_text.lower() for word in ['publicado hace']):
                            description = desc_text
                            break
                    except:
                        continue
            except NoSuchElementException:
                pass

            # Create item
            item = JobItem()
            item['portal'] = self.portal
            item['country'] = self.country
            item['url'] = url
            item['title'] = title
            item['company'] = company or "No especificado"
            item['location'] = location or self.country
            item['description'] = description or f"Trabajo: {title}"
            item['requirements'] = ""
            item['salary_raw'] = ""
            item['contract_type'] = ""
            item['remote_type'] = ""
            item['posted_date'] = datetime.now().date().isoformat()

            # Validate
            if len(title) < 3:
                return None

            return item

        except Exception as e:
            logger.error(f"❌ Error extracting from card: {e}")
            return None

    def _cleanup_driver(self):
        """Clean up driver."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✅ Driver cleaned up")
            except Exception as e:
                logger.error(f"❌ Error cleaning up driver: {e}")
            finally:
                self.driver = None

    def closed(self, reason):
        """Called when spider closes."""
        self._cleanup_driver()
