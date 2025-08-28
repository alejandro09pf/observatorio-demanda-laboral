#!/usr/bin/env python3
"""
Diagnostic script for Bumeran México website structure analysis.
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
    chrome_options.add_argument("--headless")
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
        time.sleep(3)  # Wait for initial load
        
        # Wait for content to load
        wait = WebDriverWait(driver, 10)
        
        # Check for job cards
        print("\n--- Job Cards Analysis ---")
        
        # Try different selectors for job cards
        selectors_to_try = [
            "article",
            "div[class*='job']",
            "div[class*='card']",
            "div[class*='offer']",
            "div[class*='listing']",
            ".job-card",
            ".job-item",
            ".offer-card",
            ".listing-item"
        ]
        
        job_cards = []
        for selector in selectors_to_try:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"Selector '{selector}': Found {len(cards)} elements")
                    if len(cards) > 0 and len(cards) <= 20:  # Reasonable number for job cards
                        job_cards = cards
                        print(f"Using selector: {selector}")
                        break
            except Exception as e:
                print(f"Selector '{selector}': Error - {e}")
        
        if not job_cards:
            print("No job cards found with any selector")
            return None
        
        # Analyze first job card structure
        if job_cards:
            first_card = job_cards[0]
            print(f"\n--- First Job Card Structure ---")
            print(f"Tag: {first_card.tag_name}")
            print(f"Classes: {first_card.get_attribute('class')}")
            print(f"HTML: {first_card.get_attribute('outerHTML')[:500]}...")
            
            # Try to extract job information
            print(f"\n--- Job Information Extraction ---")
            
            # Title
            title_selectors = [
                "h2 a",
                "h1 a", 
                "h3 a",
                "a[href*='/empleo/']",
                "a[href*='/trabajo/']",
                "a[href*='/job/']"
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
                "span[class*='company']"
            ]
            
            for selector in company_selectors:
                try:
                    company_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    company_text = company_elem.text.strip()
                    if company_text:
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
                "span[class*='location']"
            ]
            
            for selector in location_selectors:
                try:
                    location_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    location_text = location_elem.text.strip()
                    if location_text:
                        print(f"Location: {location_text}")
                        break
                except NoSuchElementException:
                    continue
            
            # Description
            desc_selectors = [
                "p",
                ".description",
                ".summary",
                "div[class*='description']"
            ]
            
            for selector in desc_selectors:
                try:
                    desc_elem = first_card.find_element(By.CSS_SELECTOR, selector)
                    desc_text = desc_elem.text.strip()
                    if desc_text and len(desc_text) > 20:  # Reasonable description length
                        print(f"Description: {desc_text[:100]}...")
                        break
                except NoSuchElementException:
                    continue
        
        # Check pagination
        print(f"\n--- Pagination Analysis ---")
        pagination_selectors = [
            "a[rel='next']",
            "a:contains('Siguiente')",
            ".pagination a:last-child",
            "a[href*='page=']"
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
    print("=== Bumeran México Website Structure Analysis ===")
    
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
        
        # Save results
        with open("outputs/bumeran_diagnosis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: outputs/bumeran_diagnosis.json")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
