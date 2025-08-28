#!/usr/bin/env python3
"""
Analyze job-related links on Bumeran México to understand job listing structure.
"""

import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException

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

def analyze_job_links(driver, url):
    """Analyze job-related links on the page."""
    print(f"=== Analyzing job links on: {url} ===")
    
    try:
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        # Find all links with job-related hrefs
        job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo'], a[href*='job'], a[href*='trabajo']")
        print(f"Found {len(job_links)} job-related links")
        
        # Analyze each link
        link_details = []
        for i, link in enumerate(job_links[:20]):  # Analyze first 20 links
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                tag_name = link.tag_name
                
                # Get parent element info
                parent = link.find_element(By.XPATH, "..")
                parent_tag = parent.tag_name
                parent_class = parent.get_attribute('class') or 'No class'
                
                # Get grandparent element info
                try:
                    grandparent = parent.find_element(By.XPATH, "..")
                    grandparent_tag = grandparent.tag_name
                    grandparent_class = grandparent.get_attribute('class') or 'No class'
                except:
                    grandparent_tag = "N/A"
                    grandparent_class = "N/A"
                
                # Check if this looks like a job listing
                is_job_listing = any(keyword in text.lower() for keyword in ['desarrollador', 'programador', 'ingeniero', 'analista', 'coordinador', 'gerente', 'director'])
                
                link_info = {
                    'index': i + 1,
                    'href': href,
                    'text': text,
                    'tag_name': tag_name,
                    'parent_tag': parent_tag,
                    'parent_class': parent_class,
                    'grandparent_tag': grandparent_tag,
                    'grandparent_class': grandparent_class,
                    'is_job_listing': is_job_listing
                }
                
                link_details.append(link_info)
                
                print(f"Link {i+1}:")
                print(f"  Text: '{text}'")
                print(f"  Href: {href}")
                print(f"  Tag: {tag_name}")
                print(f"  Parent: {parent_tag} (class: {parent_class})")
                print(f"  Grandparent: {grandparent_tag} (class: {grandparent_class})")
                print(f"  Looks like job: {is_job_listing}")
                print()
                
            except Exception as e:
                print(f"Error analyzing link {i+1}: {e}")
        
        # Look for any divs that might contain job listings
        print("=== Looking for job container divs ===")
        
        # Try different selectors for job containers
        selectors_to_try = [
            "div[class*='job']",
            "div[class*='card']", 
            "div[class*='listing']",
            "div[class*='item']",
            "div[class*='result']",
            "div[class*='post']",
            "div[class*='offer']",
            "div[class*='vacancy']",
            "div[class*='position']",
            "div[class*='opportunity']",
            "div[class*='sc-']",  # React components
            "section[class*='job']",
            "section[class*='card']",
            "section[class*='listing']"
        ]
        
        for selector in selectors_to_try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            if elements:
                print(f"Found {len(elements)} elements with selector: {selector}")
                for j, elem in enumerate(elements[:3]):  # Show first 3
                    try:
                        text = elem.text.strip()[:100]
                        class_attr = elem.get_attribute('class')
                        print(f"  Element {j+1}: class='{class_attr}', text='{text}...'")
                    except:
                        print(f"  Element {j+1}: [Error reading]")
                print()
        
        # Look for any elements with specific data attributes
        print("=== Looking for elements with data attributes ===")
        data_elements = driver.find_elements(By.CSS_SELECTOR, "[data-*]")
        print(f"Found {len(data_elements)} elements with data attributes")
        
        # Look for elements with job-related data attributes
        job_data_elements = driver.find_elements(By.CSS_SELECTOR, "[data-job], [data-id], [data-url]")
        print(f"Found {len(job_data_elements)} elements with job-related data attributes")
        
        # Check for any elements that might be job cards based on structure
        print("=== Looking for potential job card structures ===")
        
        # Look for divs that contain links and have multiple child elements
        all_divs = driver.find_elements(By.TAG_NAME, "div")
        potential_job_divs = []
        
        for div in all_divs[:50]:  # Check first 50 divs
            try:
                children = div.find_elements(By.XPATH, "*")
                links = div.find_elements(By.TAG_NAME, "a")
                
                # If div has multiple children and at least one link, it might be a job card
                if len(children) >= 3 and len(links) >= 1:
                    text = div.text.strip()
                    if len(text) > 50 and any(keyword in text.lower() for keyword in ['empleo', 'trabajo', 'vacante', 'puesto']):
                        potential_job_divs.append({
                            'text': text[:200],
                            'children_count': len(children),
                            'links_count': len(links),
                            'class': div.get_attribute('class') or 'No class'
                        })
            except:
                continue
        
        print(f"Found {len(potential_job_divs)} potential job divs")
        for i, div_info in enumerate(potential_job_divs[:5]):
            print(f"  Potential job div {i+1}:")
            print(f"    Text: {div_info['text']}...")
            print(f"    Children: {div_info['children_count']}")
            print(f"    Links: {div_info['links_count']}")
            print(f"    Class: {div_info['class']}")
            print()
        
        return {
            'url': url,
            'total_job_links': len(job_links),
            'analyzed_links': link_details,
            'potential_job_divs': potential_job_divs
        }
        
    except Exception as e:
        print(f"Error analyzing page: {e}")
        return None

def main():
    """Main analysis function."""
    print("=== Bumeran México Job Links Analysis ===")
    
    driver = setup_driver()
    
    try:
        # Analyze the main empleos page
        url = "https://www.bumeran.com.mx/empleos.html"
        results = analyze_job_links(driver, url)
        
        # Save results
        if results:
            with open('outputs/bumeran_links_analysis.json', 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            
            print(f"\n=== Analysis Complete ===")
            print(f"Results saved to: outputs/bumeran_links_analysis.json")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
    
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
