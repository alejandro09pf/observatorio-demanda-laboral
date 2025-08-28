#!/usr/bin/env python3
"""
Targeted diagnostic script to find job listings on Bumeran México.
"""

import sys
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time

# Add the project root to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def setup_driver():
    """Setup Chrome WebDriver with appropriate options."""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # Comment out for debugging
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-detection flags
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        return None

def analyze_job_listings(driver, url):
    """Analyze job listings on the page."""
    print(f"\n=== Analyzing Job Listings: {url} ===")
    
    try:
        driver.get(url)
        print("Page loaded, waiting for content...")
        
        # Wait longer for content to load
        time.sleep(15)
        
        # Get page title and URL
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Scroll down to trigger lazy loading
        print("Scrolling down to trigger content loading...")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)
        
        # Look for job-related content
        print("\n--- Looking for Job-Related Content ---")
        
        # Check for any text that mentions jobs
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if "empleo" in page_text.lower() or "trabajo" in page_text.lower():
            print("Page contains job-related keywords")
        
        # Look for any divs that might contain job listings
        all_divs = driver.find_elements(By.TAG_NAME, "div")
        print(f"Total divs on page: {len(all_divs)}")
        
        # Look for divs with job-related text
        job_related_divs = []
        for div in all_divs:
            try:
                div_text = div.text.strip()
                if div_text and any(keyword in div_text.lower() for keyword in ['empleo', 'trabajo', 'puesto', 'vacante', 'oferta']):
                    job_related_divs.append(div)
            except:
                continue
        
        print(f"Found {len(job_related_divs)} divs with job-related text")
        
        # Show first few job-related divs
        for i, div in enumerate(job_related_divs[:10]):
            try:
                print(f"\n--- Job-Related Div {i+1} ---")
                print(f"Class: {div.get_attribute('class')}")
                print(f"Text: {div.text[:300]}...")
                print(f"HTML: {div.get_attribute('outerHTML')[:500]}...")
                
                # Look for links within this div
                links = div.find_elements(By.TAG_NAME, "a")
                if links:
                    print(f"Links found: {len(links)}")
                    for j, link in enumerate(links[:3]):
                        try:
                            print(f"  Link {j+1}: {link.text[:50]}... -> {link.get_attribute('href')}")
                        except:
                            continue
            except Exception as e:
                print(f"Error analyzing div {i+1}: {e}")
        
        # Look for any sections or main content areas
        print("\n--- Looking for Main Content Areas ---")
        main_content_selectors = [
            "main",
            "[role='main']",
            ".main-content",
            ".content",
            ".results",
            ".listings",
            ".search-results",
            ".job-results"
        ]
        
        for selector in main_content_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Main content selector '{selector}': Found {len(elements)} elements")
                    for elem in elements[:2]:
                        print(f"  Text: {elem.text[:300]}...")
                        print(f"  HTML: {elem.get_attribute('outerHTML')[:500]}...")
            except Exception as e:
                print(f"Main content selector '{selector}': Error - {e}")
        
        # Look for any React components that might be job cards
        print("\n--- Looking for React Components ---")
        react_selectors = [
            "[class*='sc-']",
            "[class*='styled']",
            "[class*='component']",
            "[class*='card']",
            "[class*='item']"
        ]
        
        for selector in react_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"React selector '{selector}': Found {len(elements)} elements")
                    # Show first few elements
                    for elem in elements[:3]:
                        try:
                            elem_text = elem.text.strip()
                            if elem_text and len(elem_text) > 20:  # Reasonable text length
                                print(f"  Text: {elem_text[:100]}...")
                                print(f"  Class: {elem.get_attribute('class')}")
                        except:
                            continue
            except Exception as e:
                print(f"React selector '{selector}': Error - {e}")
        
        # Look for any iframes that might contain job content
        print("\n--- Looking for iframes ---")
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        if iframes:
            print(f"Found {len(iframes)} iframes")
            for i, iframe in enumerate(iframes):
                try:
                    print(f"  Iframe {i+1}: src={iframe.get_attribute('src')}")
                except:
                    continue
        
        # Check if there's a search form or filters
        print("\n--- Looking for Search Forms ---")
        form_selectors = [
            "form",
            "[role='search']",
            ".search",
            ".filter",
            ".filters"
        ]
        
        for selector in form_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"Form selector '{selector}': Found {len(elements)} elements")
            except Exception as e:
                print(f"Form selector '{selector}': Error - {e}")
        
        return {
            "url": url,
            "job_related_divs": len(job_related_divs),
            "total_divs": len(all_divs),
            "has_iframes": len(iframes) > 0
        }
        
    except Exception as e:
        print(f"Error analyzing page: {e}")
        return None

def main():
    """Main diagnostic function."""
    print("=== Targeted Bumeran México Job Listings Analysis ===")
    
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver")
        return
    
    try:
        # Test URLs
        test_urls = [
            "https://www.bumeran.com.mx/empleos.html",
            "https://www.bumeran.com.mx/empleos.html?page=1"
        ]
        
        results = []
        
        for url in test_urls:
            result = analyze_job_listings(driver, url)
            if result:
                results.append(result)
            
            # Wait between requests
            time.sleep(5)
        
        # Save results
        with open("outputs/bumeran_jobs_analysis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: outputs/bumeran_jobs_analysis.json")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
