#!/usr/bin/env python3
"""
Debug script for ZonaJobs spider to test Selenium setup and website access.
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set environment variables for orchestrator execution
os.environ['ORCHESTRATOR_EXECUTION'] = 'true'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def test_selenium_setup():
    """Test Selenium setup with undetected-chromedriver."""
    try:
        import undetected_chromedriver as uc
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        
        logger.info("🔧 Testing Selenium setup...")
        
        # Create Chrome options
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Create driver with webdriver-manager
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        from selenium import webdriver
        
        # Get compatible ChromeDriver
        driver_path = ChromeDriverManager().install()
        logger.info(f"✅ ChromeDriver installed at: {driver_path}")
        
        # Create service
        service = Service(driver_path)
        
        # Create driver (using regular ChromeDriver instead of undetected)
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        
        logger.info("✅ Selenium driver created successfully")
        
        # Test navigation to ZonaJobs
        url = "https://www.zonajobs.com.ar/empleos.html"
        logger.info(f"🌐 Navigating to: {url}")
        
        driver.get(url)
        time.sleep(5)  # Wait for page to load
        
        # Check page source
        page_source = driver.page_source
        logger.info(f"📄 Page source length: {len(page_source)} characters")
        
        # Check for blocking
        if "Attention Required!" in page_source or "Cloudflare" in page_source:
            logger.warning("⚠️ Cloudflare protection detected")
        else:
            logger.info("✅ No Cloudflare protection detected")
        
        # Try to find article elements
        wait = WebDriverWait(driver, 20)
        try:
            logger.info("⏳ Waiting for article elements...")
            articles = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, 'article')))
            logger.info(f"✅ Found {len(articles)} article elements")
            
            # Try to extract some data from first article
            if articles:
                first_article = articles[0]
                try:
                    # Try to find title link
                    title_link = first_article.find_element(By.CSS_SELECTOR, "h2 a")
                    title = title_link.text.strip()
                    href = title_link.get_attribute('href')
                    logger.info(f"📋 First job title: {title}")
                    logger.info(f"🔗 First job URL: {href}")
                except NoSuchElementException:
                    logger.warning("⚠️ Could not find title link in first article")
                    
                    # Log article HTML for debugging
                    article_html = first_article.get_attribute('outerHTML')
                    logger.info(f"📄 First article HTML: {article_html[:500]}...")
            
        except TimeoutException:
            logger.error("❌ Timeout waiting for article elements")
            
            # Log page source for debugging
            logger.info(f"📄 Page source preview: {page_source[:1000]}...")
        
        # Keep browser open for manual inspection
        logger.info("🔍 Browser will stay open for 30 seconds for manual inspection...")
        time.sleep(30)
        
        driver.quit()
        logger.info("✅ Test completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        logger.error(f"📋 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    test_selenium_setup()
