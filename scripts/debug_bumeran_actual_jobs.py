#!/usr/bin/env python3
"""
Debug script to find actual job postings on Bumeran México.
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

def find_actual_job_postings():
    """Find actual job postings on Bumeran."""
    print("=== Finding Actual Job Postings on Bumeran ===")
    
    driver = setup_driver()
    
    try:
        # Navigate to the page
        url = "https://www.bumeran.com.mx/empleos.html"
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Find all links with job-related hrefs
        all_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo']")
        print(f"Found {len(all_links)} total links with 'empleo'")
        
        # Filter for actual job postings
        actual_jobs = []
        navigation_links = []
        
        for link in all_links:
            try:
                href = link.get_attribute('href')
                text = link.text.strip()
                
                # Check if this is a navigation/filter link
                if any(nav_pattern in href for nav_pattern in [
                    'seniority-', 'landing-', 'relevantes=true', 'recientes=true',
                    'empleos-seniority-', 'empleos.html?'
                ]):
                    navigation_links.append({
                        'href': href,
                        'text': text[:50] + '...' if len(text) > 50 else text
                    })
                # Check if this looks like an actual job posting
                elif (href.endswith('.html') and 
                      '/empleos/' in href and 
                      len(text) > 10 and
                      not href.endswith('empleos.html')):
                    actual_jobs.append({
                        'href': href,
                        'text': text[:100] + '...' if len(text) > 100 else text
                    })
                
            except Exception as e:
                print(f"Error processing link: {e}")
        
        print(f"\n=== Results ===")
        print(f"Navigation/Filter links: {len(navigation_links)}")
        print(f"Actual job postings: {len(actual_jobs)}")
        
        print(f"\n=== Navigation Links (first 5) ===")
        for i, link in enumerate(navigation_links[:5]):
            print(f"{i+1}. {link['text']}")
            print(f"   URL: {link['href']}")
            print()
        
        print(f"\n=== Actual Job Postings (first 10) ===")
        for i, job in enumerate(actual_jobs[:10]):
            print(f"{i+1}. {job['text']}")
            print(f"   URL: {job['href']}")
            print()
        
        # If we found actual jobs, test the first one
        if actual_jobs:
            first_job_url = actual_jobs[0]['href']
            print(f"\n=== Testing First Job Details ===")
            print(f"URL: {first_job_url}")
            
            # Navigate to the job detail page
            driver.get(first_job_url)
            time.sleep(3)
            
            print(f"Job page title: {driver.title}")
            print(f"Job page URL: {driver.current_url}")
            
            # Try to extract job details
            job_details = extract_job_details_from_page(driver)
            print(f"Job details: {json.dumps(job_details, indent=2, ensure_ascii=False)}")
        
        return {
            'navigation_links': navigation_links,
            'actual_jobs': actual_jobs
        }
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        return None
    
    finally:
        driver.quit()

def extract_job_details_from_page(driver):
    """Extract job details from a job detail page."""
    job_details = {}
    
    try:
        # Extract title
        title_selectors = ["h1", ".job-title", ".title", "h2"]
        for selector in title_selectors:
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['title'] = title_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract company
        company_selectors = ["h1 + div span", ".company", ".employer", "span[class*='company']"]
        for selector in company_selectors:
            try:
                company_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['company'] = company_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract location
        location_selectors = ["div[aria-label='location']", ".location", ".place", "span[class*='location']"]
        for selector in location_selectors:
            try:
                location_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['location'] = location_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract description
        desc_selectors = [".description", ".job-description", "div[class*='description']", "p"]
        for selector in desc_selectors:
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, selector)
                desc_text = desc_elem.text.strip()
                if len(desc_text) > 50:  # Only if it's substantial
                    job_details['description'] = desc_text[:200] + '...' if len(desc_text) > 200 else desc_text
                    break
            except NoSuchElementException:
                continue
        
        # Extract posted date
        date_selectors = ["time", "span[aria-label='Publicado']", ".date", ".posted"]
        for selector in date_selectors:
            try:
                date_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['posted_date'] = date_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
    except Exception as e:
        print(f"Error extracting job details: {e}")
    
    return job_details

if __name__ == "__main__":
    results = find_actual_job_postings()
    
    if results:
        # Save results
        with open('outputs/bumeran_actual_jobs_analysis.json', 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n=== Analysis Complete ===")
        print(f"Results saved to: outputs/bumeran_actual_jobs_analysis.json")
