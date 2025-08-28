#!/usr/bin/env python3
"""
Simple test script to debug Bumeran page loading and link detection.
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def setup_driver():
    """Setup Chrome WebDriver with options."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-detection
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def test_bumeran_page():
    """Test Bumeran page loading and link detection."""
    print("=== Testing Bumeran Page Loading ===")
    
    driver = setup_driver()
    
    try:
        # Test different URLs
        urls_to_test = [
            "https://www.bumeran.com.mx/empleos.html",
            "https://www.bumeran.com.mx/empleos",
            "https://www.bumeran.com.mx"
        ]
        
        for url in urls_to_test:
            print(f"\n--- Testing URL: {url} ---")
            
            driver.get(url)
            time.sleep(10)  # Wait longer for content to load
            
            print(f"Page title: {driver.title}")
            print(f"Current URL: {driver.current_url}")
            
            # Find all links
            all_links = driver.find_elements(By.TAG_NAME, "a")
            print(f"Total links on page: {len(all_links)}")
            
            # Find links with 'empleo'
            empleo_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo']")
            print(f"Links with 'empleo': {len(empleo_links)}")
            
            # Show first few empleo links
            for i, link in enumerate(empleo_links[:5]):
                try:
                    href = link.get_attribute('href')
                    text = link.text.strip()
                    print(f"  Link {i+1}: {text[:50]}... -> {href}")
                except:
                    print(f"  Link {i+1}: [Error reading]")
            
            # Check if page has content
            body_text = driver.find_element(By.TAG_NAME, "body").text
            print(f"Body text length: {len(body_text)}")
            print(f"Body text preview: {body_text[:200]}...")
            
            # Check for specific content
            if "empleo" in body_text.lower():
                print("✓ 'empleo' found in page content")
            else:
                print("✗ 'empleo' NOT found in page content")
            
            time.sleep(2)  # Wait between tests
        
    except Exception as e:
        print(f"Error during testing: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    test_bumeran_page()
