#!/usr/bin/env python3
"""
Debug script to inspect OCC detail page structure.
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

def debug_occ_detail():
    """Debug OCC detail page to see actual structure."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
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
            # Use the same URL we saw in the logs
            url = "https://www.occ.com.mx/empleo/oferta/20250828-customer-sales-representative-ejecutivo-de-ventas/"
            logger.info(f"🌐 Loading: {url}")
            driver.get(url)
            
            # Wait for content
            time.sleep(5)
            
            # Get page title and URL
            title = driver.title
            current_url = driver.current_url
            logger.info(f"Page title: {title}")
            logger.info(f"Current URL: {current_url}")
            
            # Save page source for inspection
            page_source = driver.page_source
            with open("debug_occ_detail.html", "w", encoding="utf-8") as f:
                f.write(page_source)
            logger.info("💾 Saved page source to debug_occ_detail.html")
            
            # Look for title elements
            logger.info("🔍 Looking for title elements...")
            title_selectors = [
                "h1",
                "h2", 
                "h3",
                "[class*='title']",
                "[data-offers-grid-detail-title]"
            ]
            
            for selector in title_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}': {len(elements)} elements")
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()
                            if text and len(text) > 5:
                                logger.info(f"  [{i}] '{text[:100]}'")
                        except:
                            pass
                except Exception as e:
                    logger.info(f"Selector '{selector}' failed: {e}")
            
            # Look for company elements
            logger.info("🔍 Looking for company elements...")
            company_selectors = [
                "[class*='company']",
                "[class*='employer']",
                "span:contains('Empresa')",
                "div:contains('Empresa')"
            ]
            
            for selector in company_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}': {len(elements)} elements")
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()
                            if text and len(text) > 2:
                                logger.info(f"  [{i}] '{text[:100]}'")
                        except:
                            pass
                except Exception as e:
                    logger.info(f"Selector '{selector}' failed: {e}")
            
            # Look for salary elements
            logger.info("🔍 Looking for salary elements...")
            salary_selectors = [
                "[class*='salary']",
                "[class*='wage']",
                "span:contains('$')",
                "div:contains('$')"
            ]
            
            for selector in salary_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}': {len(elements)} elements")
                    for i, elem in enumerate(elements[:3]):
                        try:
                            text = elem.text.strip()
                            if text and '$' in text:
                                logger.info(f"  [{i}] '{text[:100]}'")
                        except:
                            pass
                except Exception as e:
                    logger.info(f"Selector '{selector}' failed: {e}")
            
            # Look for any text containing key words
            logger.info("🔍 Looking for key words in page...")
            key_words = ["Customer Sales", "SeguroInteligente", "12,000", "Mensual", "Ciudad de México"]
            
            for word in key_words:
                try:
                    elements = driver.find_elements(By.XPATH, f"//*[contains(text(), '{word}')]")
                    logger.info(f"Word '{word}': {len(elements)} elements")
                    for i, elem in enumerate(elements[:2]):
                        try:
                            text = elem.text.strip()
                            logger.info(f"  [{i}] '{text[:100]}'")
                        except:
                            pass
                except Exception as e:
                    logger.info(f"Word '{word}' failed: {e}")
            
        finally:
            driver.quit()
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_occ_detail()

