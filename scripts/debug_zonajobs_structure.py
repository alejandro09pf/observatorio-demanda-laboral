#!/usr/bin/env python3
"""
Debug script to understand ZonaJobs website structure.
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

def analyze_zonajobs_structure():
    """Analyze the actual structure of ZonaJobs website."""
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.chrome.options import Options
        
        logger.info("🔧 Setting up Chrome WebDriver...")
        
        # Create options
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Create driver
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        logger.info("✅ Driver created successfully")
        
        # Navigate to ZonaJobs
        url = "https://www.zonajobs.com.ar/empleos.html"
        logger.info(f"🌐 Navigating to: {url}")
        driver.get(url)
        
        # Wait for page to load
        time.sleep(10)
        
        # Get page source
        page_source = driver.page_source
        logger.info(f"📄 Page source length: {len(page_source)} characters")
        
        # Look for various selectors that might contain job listings
        selectors_to_try = [
            "article",
            "[class*='job']",
            "[class*='empleo']",
            "[class*='card']",
            "[class*='listing']",
            "a[href*='empleos/']",
            "a[href*='/empleos/']",
            ".job-item",
            ".job-card",
            ".job-listing",
            "[data-testid*='job']",
            "[data-testid*='listing']"
        ]
        
        for selector in selectors_to_try:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger.info(f"✅ Found {len(elements)} elements with selector: {selector}")
                    if len(elements) > 0:
                        # Log first element's HTML
                        first_element = elements[0]
                        element_html = first_element.get_attribute('outerHTML')
                        logger.info(f"📄 First element HTML: {element_html[:200]}...")
                else:
                    logger.info(f"❌ No elements found with selector: {selector}")
            except Exception as e:
                logger.error(f"❌ Error with selector {selector}: {e}")
        
        # Look for any links that might be job postings
        all_links = driver.find_elements(By.TAG_NAME, "a")
        job_links = []
        for link in all_links:
            href = link.get_attribute("href")
            if href and ("empleos" in href or "empleo" in href):
                job_links.append(link)
        
        logger.info(f"🔗 Found {len(job_links)} potential job links")
        
        if job_links:
            for i, link in enumerate(job_links[:5]):  # Show first 5
                href = link.get_attribute("href")
                text = link.text.strip()
                logger.info(f"📋 Link {i+1}: {text[:50]}... -> {href}")
        
        # Keep browser open for manual inspection
        logger.info("🔍 Browser will stay open for 60 seconds for manual inspection...")
        time.sleep(60)
        
        driver.quit()
        logger.info("✅ Analysis completed")
        
    except Exception as e:
        logger.error(f"❌ Analysis failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    analyze_zonajobs_structure()

