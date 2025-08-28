#!/usr/bin/env python3
"""
Diagnostic script for Clarín website structure.
"""

import sys
import os
from pathlib import Path
import time
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def setup_driver():
    """Setup Chrome WebDriver for diagnosis."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # Anti-detection flags
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    return driver

def diagnose_clarin():
    """Diagnose Clarín website structure."""
    driver = None
    try:
        print("Setting up Chrome WebDriver...")
        driver = setup_driver()
        
        # Test different Clarín URLs
        urls_to_test = [
            "https://clasificados.clarin.com/empleos",
            "https://clasificados.clarin.com/inicio/index#!/1/listado/nivel-estructura/Empleos",
            "https://clasificados.clarin.com/empleos/tecnologia",
            "https://clasificados.clarin.com/empleos/administracion"
        ]
        
        results = {}
        
        for url in urls_to_test:
            print(f"\nTesting URL: {url}")
            results[url] = test_url(driver, url)
        
        # Save results
        with open("outputs/clarin_diagnosis.json", "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\nDiagnosis completed! Results saved to outputs/clarin_diagnosis.json")
        
    except Exception as e:
        print(f"Error during diagnosis: {e}")
    finally:
        if driver:
            driver.quit()

def test_url(driver, url):
    """Test a specific URL and analyze its structure."""
    result = {
        "url": url,
        "status": "failed",
        "page_title": "",
        "job_cards_found": 0,
        "potential_ids": [],
        "html_structure": {},
        "errors": []
    }
    
    try:
        print(f"  Navigating to {url}...")
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        # Get page title
        result["page_title"] = driver.title
        print(f"  Page title: {result['page_title']}")
        
        # Scroll to load content
        print("  Scrolling to load content...")
        scroll_to_load_content(driver)
        
        # Look for job cards
        job_cards = find_job_cards(driver)
        result["job_cards_found"] = len(job_cards)
        print(f"  Found {len(job_cards)} job cards")
        
        # Extract potential IDs
        potential_ids = extract_potential_ids(driver)
        result["potential_ids"] = potential_ids
        print(f"  Found {len(potential_ids)} potential IDs")
        
        # Analyze HTML structure
        html_structure = analyze_html_structure(driver)
        result["html_structure"] = html_structure
        
        result["status"] = "success"
        
    except Exception as e:
        error_msg = str(e)
        result["errors"].append(error_msg)
        print(f"  Error: {error_msg}")
    
    return result

def scroll_to_load_content(driver):
    """Scroll down to load more content."""
    last_height = driver.execute_script("return document.body.scrollHeight")
    scroll_attempts = 0
    max_scroll_attempts = 5
    
    while scroll_attempts < max_scroll_attempts:
        # Scroll down
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        
        # Wait for new content to load
        time.sleep(2)
        
        # Calculate new scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        
        if new_height == last_height:
            break
            
        last_height = new_height
        scroll_attempts += 1

def find_job_cards(driver):
    """Find job cards on the page."""
    selectors = [
        "article",
        ".job-card",
        ".listing-item",
        "div[class*='job']",
        "div[class*='listing']",
        "div[class*='result']",
        "div[class*='item']",
        ".card",
        ".item"
    ]
    
    job_cards = []
    for selector in selectors:
        try:
            cards = driver.find_elements(By.CSS_SELECTOR, selector)
            if cards:
                job_cards.extend(cards)
                print(f"    Found {len(cards)} elements with selector: {selector}")
        except Exception as e:
            print(f"    Error with selector {selector}: {e}")
    
    # Remove duplicates
    unique_cards = []
    seen = set()
    for card in job_cards:
        card_id = card.id
        if card_id not in seen:
            seen.add(card_id)
            unique_cards.append(card)
    
    return unique_cards

def extract_potential_ids(driver):
    """Extract potential advert IDs from the page."""
    import re
    
    # Get page HTML
    page_html = driver.page_source
    
    # Look for 6-8 digit numbers
    patterns = [
        r'\b(\d{6,8})\b',  # 6-8 digit numbers
        r'aviso[\/\-](\d{6,8})',  # aviso/123456 or aviso-123456
        r'id[=:](\d{6,8})',  # id=123456 or id:123456
        r'(\d{6,8})\.html',  # 123456.html
    ]
    
    potential_ids = []
    for pattern in patterns:
        matches = re.findall(pattern, page_html)
        potential_ids.extend(matches)
    
    # Remove duplicates and limit to first 20
    unique_ids = list(set(potential_ids))[:20]
    return unique_ids

def analyze_html_structure(driver):
    """Analyze the HTML structure of the page."""
    structure = {
        "body_classes": [],
        "main_elements": [],
        "article_elements": 0,
        "div_elements": 0,
        "a_elements": 0,
        "common_classes": {}
    }
    
    try:
        # Get body classes
        body = driver.find_element(By.TAG_NAME, "body")
        structure["body_classes"] = body.get_attribute("class").split() if body.get_attribute("class") else []
        
        # Count elements
        structure["article_elements"] = len(driver.find_elements(By.TAG_NAME, "article"))
        structure["div_elements"] = len(driver.find_elements(By.TAG_NAME, "div"))
        structure["a_elements"] = len(driver.find_elements(By.TAG_NAME, "a"))
        
        # Find main elements
        main_elements = driver.find_elements(By.CSS_SELECTOR, "main, [role='main'], .main, #main")
        structure["main_elements"] = [elem.get_attribute("class") or elem.get_attribute("id") for elem in main_elements]
        
        # Analyze common classes
        all_elements = driver.find_elements(By.CSS_SELECTOR, "*")
        class_counts = {}
        for elem in all_elements:
            classes = elem.get_attribute("class")
            if classes:
                for cls in classes.split():
                    class_counts[cls] = class_counts.get(cls, 0) + 1
        
        # Get top 10 most common classes
        sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
        structure["common_classes"] = dict(sorted_classes[:10])
        
    except Exception as e:
        print(f"    Error analyzing HTML structure: {e}")
    
    return structure

if __name__ == "__main__":
    diagnose_clarin()
