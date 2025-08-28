#!/usr/bin/env python3
"""
Diagnostic script to analyze current Bumeran México website structure.
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

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

def analyze_page_structure(driver, url, page_name):
    """Analyze the structure of a page and find potential job-related elements."""
    print(f"\n=== Analyzing {page_name} ===")
    print(f"URL: {url}")
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        # Get page title
        title = driver.title
        print(f"Page Title: {title}")
        
        # Check current URL (in case of redirects)
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # Look for common job-related elements
        print("\n--- Looking for job-related elements ---")
        
        # Check for any article elements
        articles = driver.find_elements(By.TAG_NAME, "article")
        print(f"Found {len(articles)} article elements")
        for i, article in enumerate(articles[:3]):  # Show first 3
            try:
                print(f"  Article {i+1}: {article.get_attribute('outerHTML')[:200]}...")
            except:
                print(f"  Article {i+1}: [Error reading content]")
        
        # Check for div elements with job-related classes
        job_divs = driver.find_elements(By.CSS_SELECTOR, "div[class*='job'], div[class*='card'], div[class*='listing']")
        print(f"Found {len(job_divs)} divs with job-related classes")
        
        # Check for links with job-related hrefs
        job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo'], a[href*='job'], a[href*='trabajo']")
        print(f"Found {len(job_links)} links with job-related hrefs")
        
        # Check for search input fields
        search_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text'], input[placeholder*='buscar'], input[placeholder*='search']")
        print(f"Found {len(search_inputs)} potential search inputs")
        for i, inp in enumerate(search_inputs[:5]):
            try:
                placeholder = inp.get_attribute('placeholder') or 'No placeholder'
                name = inp.get_attribute('name') or 'No name'
                id_attr = inp.get_attribute('id') or 'No id'
                print(f"  Input {i+1}: placeholder='{placeholder}', name='{name}', id='{id_attr}'")
            except:
                print(f"  Input {i+1}: [Error reading attributes]")
        
        # Check for any elements with job-related text
        job_text_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'empleo') or contains(text(), 'trabajo') or contains(text(), 'vacante')]")
        print(f"Found {len(job_text_elements)} elements with job-related text")
        
        # Check for React components (sc- classes)
        react_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='sc-']")
        print(f"Found {len(react_elements)} React components (sc- classes)")
        
        # Look for any clickable elements that might trigger job listings
        buttons = driver.find_elements(By.TAG_NAME, "button")
        print(f"Found {len(buttons)} button elements")
        
        # Check for any forms
        forms = driver.find_elements(By.TAG_NAME, "form")
        print(f"Found {len(forms)} form elements")
        
        # Look for any iframes
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        print(f"Found {len(iframes)} iframe elements")
        
        # Check for any loading indicators
        loading_indicators = driver.find_elements(By.CSS_SELECTOR, "[class*='loading'], [class*='spinner'], [class*='loader']")
        print(f"Found {len(loading_indicators)} loading indicators")
        
        return {
            'url': current_url,
            'title': title,
            'articles': len(articles),
            'job_divs': len(job_divs),
            'job_links': len(job_links),
            'search_inputs': len(search_inputs),
            'job_text_elements': len(job_text_elements),
            'react_elements': len(react_elements),
            'buttons': len(buttons),
            'forms': len(forms),
            'iframes': len(iframes),
            'loading_indicators': len(loading_indicators)
        }
        
    except Exception as e:
        print(f"Error analyzing {page_name}: {e}")
        return None

def try_different_approaches(driver, base_url):
    """Try different approaches to find job listings."""
    print("\n=== Trying Different Approaches ===")
    
    approaches = [
        ("Direct empleos page", f"{base_url}/empleos.html"),
        ("With page parameter", f"{base_url}/empleos.html?page=1"),
        ("With search parameter", f"{base_url}/empleos.html?q=desarrollador"),
        ("Main page", base_url),
        ("Jobs section", f"{base_url}/empleos"),
    ]
    
    results = {}
    
    for name, url in approaches:
        print(f"\n--- Trying: {name} ---")
        result = analyze_page_structure(driver, url, name)
        if result:
            results[name] = result
            
        # Wait between requests
        time.sleep(3)
    
    return results

def main():
    """Main diagnostic function."""
    print("=== Bumeran México Website Structure Analysis ===")
    
    driver = setup_driver()
    
    try:
        base_url = "https://www.bumeran.com.mx"
        
        # Try different approaches
        results = try_different_approaches(driver, base_url)
        
        # Save results
        with open('outputs/bumeran_current_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: outputs/bumeran_current_analysis.json")
        
        # Print summary
        print("\n=== Summary ===")
        for name, result in results.items():
            if result:
                print(f"{name}:")
                print(f"  Articles: {result['articles']}")
                print(f"  Job divs: {result['job_divs']}")
                print(f"  Job links: {result['job_links']}")
                print(f"  Search inputs: {result['search_inputs']}")
                print(f"  React elements: {result['react_elements']}")
                print()
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
