#!/usr/bin/env python3
"""
Debug script to inspect OCC listing page structure and job card links.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_occ_listing():
    """Debug OCC listing page to see actual structure."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        logger.info("🔧 Setting up Chrome WebDriver...")
        
        # Create options
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--headless=new")
        
        # Create driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        try:
            url = "https://www.occ.com.mx/empleos"
            logger.info(f"🌐 Loading: {url}")
            driver.get(url)
            
            # Wait for content
            time.sleep(5)
            
            # Try to accept cookies
            try:
                cookie_buttons = driver.find_elements(By.CSS_SELECTOR, "button[aria-label*='aceptar'], button:contains('Aceptar')")
                if cookie_buttons:
                    cookie_buttons[0].click()
                    time.sleep(1)
            except:
                pass
            
            # Scroll to load content
            driver.execute_script("window.scrollBy(0, 1000);")
            time.sleep(2)
            
            # Look for different card structures
            logger.info("🔍 Looking for job cards...")
            
            # Try different selectors
            selectors = [
                "article",
                "div[class*='job']",
                "div[class*='card']",
                "div[class*='item']",
                "div:has(h2)",
                "article:has(h2)",
                "a[href*='jobid']",
                "a[href*='/empleo/']",
                "a[href*='/oferta/']"
            ]
            
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}': {len(elements)} elements")
                    
                    if elements and len(elements) > 0:
                        # Show first few elements
                        for i, elem in enumerate(elements[:3]):
                            try:
                                tag = elem.tag_name
                                text = elem.text[:100] if elem.text else ""
                                href = elem.get_attribute('href') if elem.tag_name == 'a' else ""
                                logger.info(f"  [{i}] <{tag}> text='{text}' href='{href}'")
                            except Exception as e:
                                logger.info(f"  [{i}] Error getting element info: {e}")
                except Exception as e:
                    logger.info(f"Selector '{selector}' failed: {e}")
            
            # Look specifically for links with job IDs
            logger.info("🔍 Looking for job links...")
            job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='jobid'], a[href*='/empleo/'], a[href*='/oferta/']")
            logger.info(f"Found {len(job_links)} potential job links")
            
            for i, link in enumerate(job_links[:10]):
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    logger.info(f"  Link {i}: href='{href}' text='{text}'")
                except Exception as e:
                    logger.info(f"  Link {i}: Error - {e}")
            
            # Check page source for job IDs
            logger.info("🔍 Checking page source for job IDs...")
            page_source = driver.page_source
            import re
            jobid_matches = re.findall(r'jobid[=:](\d+)', page_source)
            logger.info(f"Found {len(jobid_matches)} job IDs in source: {jobid_matches[:10]}")
            
            oferta_matches = re.findall(r'/empleo/oferta/(\d+)-', page_source)
            logger.info(f"Found {len(oferta_matches)} oferta IDs in source: {oferta_matches[:10]}")
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_occ_listing()

