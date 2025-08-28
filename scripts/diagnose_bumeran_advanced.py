#!/usr/bin/env python3
"""
Advanced diagnostic script for Bumeran México website structure analysis.
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

def analyze_page_structure(driver, url):
    """Analyze the structure of a Bumeran page."""
    print(f"\n=== Analyzing: {url} ===")
    
    try:
        driver.get(url)
        print("Page loaded, waiting for content...")
        
        # Wait longer for content to load
        time.sleep(10)
        
        # Get page title and URL
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Check if we were redirected
        if driver.current_url != url:
            print(f"Redirected from {url} to {driver.current_url}")
        
        # Wait for content to load
        wait = WebDriverWait(driver, 15)
        
        # Check for job cards with more comprehensive selectors
        print("\n--- Job Cards Analysis ---")
        
        # Try different selectors for job cards
        selectors_to_try = [
            "article",
            "div[class*='job']",
            "div[class*='card']",
            "div[class*='offer']",
            "div[class*='listing']",
            "div[class*='result']",
            ".job-card",
            ".job-item",
            ".offer-card",
            ".listing-item",
            ".result-item",
            "[data-testid*='job']",
            "[class*='JobCard']",
            "[class*='JobItem']",
            "div:has(a[href*='/empleo/'])",
            "div:has(a[href*='/trabajo/'])",
            "div:has(a[href*='/job/'])"
        ]
        
        job_cards = []
        for selector in selectors_to_try:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"Selector '{selector}': Found {len(cards)} elements")
                    if len(cards) > 0 and len(cards) <= 50:  # Reasonable number for job cards
                        job_cards = cards
                        print(f"Using selector: {selector}")
                        break
            except Exception as e:
                print(f"Selector '{selector}': Error - {e}")
        
        if not job_cards:
            print("No job cards found with any selector")
            
            # Try to find any links that might be job-related
            print("\n--- Looking for job-related links ---")
            job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/empleo/'], a[href*='/trabajo/'], a[href*='/job/']")
            print(f"Found {len(job_links)} job-related links")
            
            for i, link in enumerate(job_links[:5]):  # Show first 5
                try:
                    print(f"  {i+1}. Text: {link.text[:50]}...")
                    print(f"     URL: {link.get_attribute('href')}")
                    print(f"     Parent: {link.find_element(By.XPATH, '..').tag_name}")
                except Exception as e:
                    print(f"  {i+1}. Error: {e}")
            
            # Check page source for any job-related content
            page_source = driver.page_source
            if "empleo" in page_source.lower() or "trabajo" in page_source.lower():
                print("\n--- Page contains job-related keywords ---")
                # Look for any divs or sections that might contain jobs
                all_divs = driver.find_elements(By.TAG_NAME, "div")
                print(f"Total divs on page: {len(all_divs)}")
                
                # Check for divs with job-related classes
                for div in all_divs[:20]:  # Check first 20 divs
                    try:
                        class_attr = div.get_attribute('class')
                        if class_attr and any(keyword in class_attr.lower() for keyword in ['job', 'card', 'offer', 'listing', 'result']):
                            print(f"  Div with job-related class: {class_attr}")
                            print(f"    Text: {div.text[:100]}...")
                    except:
                        continue
            
            return None
        
        # Analyze first job card structure
        if job_cards:
            first_card = job_cards[0]
            print(f"\n--- First Job Card Structure ---")
            print(f"Tag: {first_card.tag_name}")
            print(f"Classes: {first_card.get_attribute('class')}")
            print(f"HTML: {first_card.get_attribute('outerHTML')[:800]}...")
            
            # Try to extract job information
            print(f"\n--- Job Information Extraction ---")
            
            # Title
            title_selectors = [
                "h2 a",
                "h1 a", 
                "h3 a",
                "a[href*='/empleo/']",
                "a[href*='/trabajo/']",
                "a[href*='/job/']",
                "a"
            ]
            
            for selector in title_selectors:
                try:
                    title_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    title_text = title_elem.text.strip()
                    title_url = title_elem.get_attribute('href')
                    if title_text and title_url:
                        print(f"Title: {title_text}")
                        print(f"URL: {title_url}")
                        break
                except NoSuchElementException:
                    continue
            
            # Company
            company_selectors = [
                "div:nth-of-type(2) span",
                "a[href*='/empresas/']",
                ".company",
                ".employer",
                "span[class*='company']",
                "span"
            ]
            
            for selector in company_selectors:
                try:
                    company_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    company_text = company_elem.text.strip()
                    if company_text and len(company_text) > 2:
                        print(f"Company: {company_text}")
                        break
                except NoSuchElementException:
                    continue
            
            # Location
            location_selectors = [
                "[aria-label='location']",
                ".location",
                ".place",
                ".city",
                "span[class*='location']",
                "span"
            ]
            
            for selector in location_selectors:
                try:
                    location_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    location_text = location_elem.text.strip()
                    if location_text and len(location_text) > 2:
                        print(f"Location: {location_text}")
                        break
                except NoSuchElementException:
                    continue
        
        # Check pagination
        print(f"\n--- Pagination Analysis ---")
        pagination_selectors = [
            "a[rel='next']",
            "a:contains('Siguiente')",
            ".pagination a:last-child",
            "a[href*='page=']",
            "a[href*='pagina=']",
            "button[aria-label*='next']",
            "button[aria-label*='siguiente']"
        ]
        
        for selector in pagination_selectors:
            try:
                pagination_elems = driver.find_elements(By.CSS_SELECTOR, selector)
                if pagination_elems:
                    print(f"Pagination selector '{selector}': Found {len(pagination_elems)} elements")
                    for elem in pagination_elems[:3]:  # Show first 3
                        print(f"  - Text: {elem.text}, URL: {elem.get_attribute('href')}")
            except Exception as e:
                print(f"Pagination selector '{selector}': Error - {e}")
        
        return {
            "url": url,
            "job_cards_found": len(job_cards),
            "job_card_selector": selector if job_cards else None,
            "has_pagination": any(driver.find_elements(By.CSS_SELECTOR, s) for s in pagination_selectors)
        }
        
    except Exception as e:
        print(f"Error analyzing page: {e}")
        return None

def main():
    """Main diagnostic function."""
    print("=== Advanced Bumeran México Website Structure Analysis ===")
    
    driver = setup_driver()
    if not driver:
        print("Failed to setup Chrome driver")
        return
    
    try:
        # Test URLs
        test_urls = [
            "https://www.bumeran.com.mx/empleos.html",
            "https://www.bumeran.com.mx/empleos.html?page=1",
            "https://www.bumeran.com.mx/empleos.html?state=ciudad-de-mexico&page=1"
        ]
        
        results = []
        
        for url in test_urls:
            result = analyze_page_structure(driver, url)
            if result:
                results.append(result)
            
            # Wait between requests
            time.sleep(5)
        
        # Save results
        with open("outputs/bumeran_advanced_diagnosis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: outputs/bumeran_advanced_diagnosis.json")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
