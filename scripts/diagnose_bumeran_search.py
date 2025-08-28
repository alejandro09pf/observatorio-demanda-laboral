#!/usr/bin/env python3
"""
Diagnostic script to test search functionality on Bumeran México.
"""

import sys
import os
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
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

def test_search_functionality(driver, url):
    """Test search functionality on Bumeran."""
    print(f"\n=== Testing Search: {url} ===")
    
    try:
        driver.get(url)
        print("Page loaded, waiting for content...")
        
        # Wait for content to load
        time.sleep(10)
        
        # Get page title and URL
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Look for search input
        print("\n--- Looking for Search Input ---")
        search_selectors = [
            "input[type='text']",
            "input[placeholder*='empleo']",
            "input[placeholder*='trabajo']",
            "input[placeholder*='puesto']",
            "input[placeholder*='buscar']",
            ".search-input",
            "#busqueda",
            "input"
        ]
        
        search_input = None
        for selector in search_selectors:
            try:
                inputs = driver.find_elements(By.CSS_SELECTOR, selector)
                if inputs:
                    print(f"Found {len(inputs)} elements with selector '{selector}'")
                    for inp in inputs:
                        try:
                            placeholder = inp.get_attribute('placeholder')
                            if placeholder and any(keyword in placeholder.lower() for keyword in ['empleo', 'trabajo', 'puesto', 'buscar']):
                                search_input = inp
                                print(f"Found search input: {placeholder}")
                                break
                        except:
                            continue
                    if search_input:
                        break
            except Exception as e:
                print(f"Selector '{selector}': Error - {e}")
        
        if not search_input:
            print("No search input found")
            return None
        
        # Try to perform a search
        print("\n--- Performing Search ---")
        try:
            # Clear the input
            search_input.clear()
            time.sleep(1)
            
            # Type a search term
            search_term = "desarrollador"
            search_input.send_keys(search_term)
            print(f"Typed search term: {search_term}")
            time.sleep(2)
            
            # Press Enter to search
            search_input.send_keys(Keys.RETURN)
            print("Pressed Enter to search")
            time.sleep(10)
            
            # Check if URL changed
            print(f"URL after search: {driver.current_url}")
            
            # Look for job listings after search
            print("\n--- Looking for Job Listings After Search ---")
            
            # Wait for content to load
            time.sleep(5)
            
            # Look for job cards
            job_card_selectors = [
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
                ".result-item"
            ]
            
            job_cards = []
            for selector in job_card_selectors:
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
            
            if job_cards:
                print(f"\n--- Found {len(job_cards)} Job Cards ---")
                
                # Analyze first job card
                first_card = job_cards[0]
                print(f"First card tag: {first_card.tag_name}")
                print(f"First card class: {first_card.get_attribute('class')}")
                print(f"First card text: {first_card.text[:200]}...")
                print(f"First card HTML: {first_card.get_attribute('outerHTML')[:500]}...")
                
                # Look for job links
                job_links = first_card.find_elements(By.TAG_NAME, "a")
                if job_links:
                    print(f"Found {len(job_links)} links in first card")
                    for i, link in enumerate(job_links[:3]):
                        try:
                            print(f"  Link {i+1}: {link.text[:50]}... -> {link.get_attribute('href')}")
                        except:
                            continue
                
                return {
                    "url": driver.current_url,
                    "search_performed": True,
                    "job_cards_found": len(job_cards),
                    "job_card_selector": selector
                }
            else:
                print("No job cards found after search")
                
                # Check if there's a "no results" message
                no_results_selectors = [
                    ".no-results",
                    ".empty-state",
                    ".no-jobs",
                    "div:contains('No se encontraron')",
                    "div:contains('no hay')"
                ]
                
                for selector in no_results_selectors:
                    try:
                        elements = driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            print(f"Found no results message with selector: {selector}")
                            for elem in elements:
                                print(f"  Text: {elem.text}")
                    except:
                        continue
                
                return {
                    "url": driver.current_url,
                    "search_performed": True,
                    "job_cards_found": 0,
                    "no_results": True
                }
                
        except Exception as e:
            print(f"Error performing search: {e}")
            return None
        
    except Exception as e:
        print(f"Error testing search: {e}")
        return None

def main():
    """Main diagnostic function."""
    print("=== Bumeran México Search Functionality Test ===")
    
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
            result = test_search_functionality(driver, url)
            if result:
                results.append(result)
            
            # Wait between requests
            time.sleep(5)
        
        # Save results
        with open("outputs/bumeran_search_test.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Test Complete ===")
        print(f"Results saved to: outputs/bumeran_search_test.json")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
