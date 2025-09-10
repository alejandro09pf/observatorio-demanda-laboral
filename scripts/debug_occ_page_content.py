#!/usr/bin/env python3
"""
Debug script to see what's actually on the OCC page.
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

def debug_occ_page():
    """Debug what's actually on the OCC page."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        logger.info("🔧 Setting up Chrome WebDriver...")
        
        # Create options - try without headless first
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        # Don't use headless to see what's happening
        # options.add_argument("--headless=new")
        
        # Create driver
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        try:
            url = "https://www.occ.com.mx/empleos"
            logger.info(f"🌐 Loading: {url}")
            driver.get(url)
            
            # Wait and check what we got
            time.sleep(10)
            
            # Get page title and URL
            title = driver.title
            current_url = driver.current_url
            logger.info(f"Page title: {title}")
            logger.info(f"Current URL: {current_url}")
            
            # Check if we got redirected or blocked
            if "blocked" in title.lower() or "access denied" in title.lower():
                logger.warning("❌ Page appears to be blocked!")
            
            # Get page source length
            page_source = driver.page_source
            logger.info(f"Page source length: {len(page_source)} characters")
            
            # Look for common blocking indicators
            blocking_indicators = [
                "cloudflare", "access denied", "blocked", "bot", "captcha",
                "please enable javascript", "security check", "verification"
            ]
            
            page_lower = page_source.lower()
            for indicator in blocking_indicators:
                if indicator in page_lower:
                    logger.warning(f"❌ Found blocking indicator: {indicator}")
            
            # Save page source for inspection
            with open("debug_occ_page.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            logger.info("💾 Saved page source to debug_occ_page.html")
            
            # Try to find any text content
            body_text = driver.find_element(By.TAG_NAME, "body").text
            logger.info(f"Body text length: {len(body_text)} characters")
            logger.info(f"First 500 chars of body: {body_text[:500]}")
            
            # Look for any links at all
            all_links = driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Total links on page: {len(all_links)}")
            
            for i, link in enumerate(all_links[:10]):
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    if href and text:
                        logger.info(f"  Link {i}: {text} -> {href}")
                except:
                    pass
            
            # Check for any divs with text
            divs_with_text = driver.find_elements(By.XPATH, "//div[text()]")
            logger.info(f"Divs with text: {len(divs_with_text)}")
            
            # Wait longer and try scrolling
            logger.info("⏳ Waiting 15 seconds and scrolling...")
            time.sleep(15)
            driver.execute_script("window.scrollBy(0, 2000);")
            time.sleep(5)
            
            # Check again for content
            all_links_after = driver.find_elements(By.TAG_NAME, "a")
            logger.info(f"Links after scroll: {len(all_links_after)}")
            
            # Look for any elements with job-related text
            job_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'empleo') or contains(text(), 'trabajo') or contains(text(), 'vacante')]")
            logger.info(f"Elements with job-related text: {len(job_elements)}")
            
        finally:
            input("Press Enter to close browser...")  # Keep browser open to inspect
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_occ_page()

