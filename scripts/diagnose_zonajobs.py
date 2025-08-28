#!/usr/bin/env python3
"""
Diagnostic script for ZonaJobs website structure
Analyzes the actual HTML structure to understand why the spider isn't finding job cards
"""

import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import json
from pathlib import Path

def diagnose_zonajobs_structure():
    """Analyze ZonaJobs website structure."""
    
    print("=" * 60)
    print("🔍 Diagnosing ZonaJobs Website Structure")
    print("=" * 60)
    
    # Setup Chrome WebDriver
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(30)
        
        # Test URL
        url = "https://www.zonajobs.com.ar/empleos.html"
        print(f"Testing URL: {url}")
        
        # Navigate to the page
        driver.get(url)
        print("Page loaded successfully")
        
        # Wait a bit for content to load
        time.sleep(5)
        
        # Get page title
        title = driver.title
        print(f"Page title: {title}")
        
        # Get current URL (in case of redirects)
        current_url = driver.current_url
        print(f"Current URL: {current_url}")
        
        # Get page source length
        page_source = driver.page_source
        print(f"Page source length: {len(page_source)} characters")
        
        # Look for various job-related elements
        selectors_to_test = [
            "article",
            "div[class*='job']",
            "div[class*='card']",
            "div[class*='item']",
            "div[class*='listing']",
            "div[class*='offer']",
            "div[class*='vacancy']",
            "div[class*='position']",
            "div[class*='empleo']",
            "div[class*='trabajo']",
            "h2",
            "h3",
            "a[href*='empleo']",
            "a[href*='trabajo']",
            "a[href*='job']",
        ]
        
        print("\n" + "=" * 60)
        print("🔍 TESTING SELECTORS")
        print("=" * 60)
        
        results = {}
        for selector in selectors_to_test:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                results[selector] = len(elements)
                print(f"{selector}: {len(elements)} elements found")
                
                # Show first few elements for job-related selectors
                if len(elements) > 0 and any(keyword in selector for keyword in ['job', 'card', 'item', 'listing', 'offer', 'empleo', 'trabajo']):
                    print(f"  Sample elements for {selector}:")
                    for i, element in enumerate(elements[:3]):
                        try:
                            text = element.text.strip()[:100]
                            print(f"    {i+1}. {text}...")
                        except:
                            print(f"    {i+1}. [Could not extract text]")
            except Exception as e:
                results[selector] = f"Error: {e}"
                print(f"{selector}: Error - {e}")
        
        # Look for specific patterns in the HTML
        print("\n" + "=" * 60)
        print("🔍 HTML PATTERN ANALYSIS")
        print("=" * 60)
        
        html_lower = page_source.lower()
        
        patterns_to_check = [
            'job', 'card', 'item', 'listing', 'offer', 'vacancy', 'position',
            'empleo', 'trabajo', 'oferta', 'puesto', 'vacante',
            'article', 'section', 'div', 'span', 'a', 'h1', 'h2', 'h3'
        ]
        
        for pattern in patterns_to_check:
            count = html_lower.count(pattern)
            print(f"'{pattern}': {count} occurrences")
        
        # Check for JavaScript/React indicators
        print("\n" + "=" * 60)
        print("🔍 JAVASCRIPT/REACT ANALYSIS")
        print("=" * 60)
        
        js_indicators = [
            'react', 'vue', 'angular', 'javascript', 'js', 'script',
            'data-', 'aria-', 'class=', 'id=', 'onclick', 'onload'
        ]
        
        for indicator in js_indicators:
            count = html_lower.count(indicator)
            print(f"'{indicator}': {count} occurrences")
        
        # Save detailed analysis
        analysis = {
            'url': url,
            'current_url': current_url,
            'title': title,
            'page_source_length': len(page_source),
            'selector_results': results,
            'html_patterns': {pattern: html_lower.count(pattern) for pattern in patterns_to_check},
            'js_indicators': {indicator: html_lower.count(indicator) for indicator in js_indicators},
            'sample_html': page_source[:5000]  # First 5000 characters
        }
        
        output_file = Path("outputs/zonajobs_diagnosis.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Detailed analysis saved to: {output_file}")
        
        # Recommendations
        print("\n" + "=" * 60)
        print("💡 RECOMMENDATIONS")
        print("=" * 60)
        
        if results.get('article', 0) > 0:
            print("✅ Found <article> elements - these might be job cards")
        else:
            print("❌ No <article> elements found")
        
        if results.get('div[class*="job"]', 0) > 0:
            print("✅ Found div elements with 'job' in class name")
        else:
            print("❌ No div elements with 'job' in class name")
        
        if 'react' in html_lower:
            print("✅ React detected - this confirms it's a React SPA")
        else:
            print("❓ React not clearly detected")
        
        if 'data-' in html_lower:
            print("✅ Data attributes found - good for targeting")
        else:
            print("❌ No data attributes found")
        
        print("\n" + "=" * 60)
        print("✅ Diagnosis completed!")
        
    except Exception as e:
        print(f"❌ Error during diagnosis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    diagnose_zonajobs_structure()
