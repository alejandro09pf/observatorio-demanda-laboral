#!/usr/bin/env python3
"""
Debug script to test Bumeran job card extraction logic.
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

def test_job_card_extraction():
    """Test job card extraction logic."""
    print("=== Testing Bumeran Job Card Extraction ===")
    
    driver = setup_driver()
    
    try:
        # Navigate to the page
        url = "https://www.bumeran.com.mx/empleos.html"
        driver.get(url)
        time.sleep(5)  # Wait for page load
        
        print(f"Page title: {driver.title}")
        print(f"Current URL: {driver.current_url}")
        
        # Find job cards using the selector that worked
        selector = "div[class*='sc-'] a[href*='empleo']"
        job_cards = driver.find_elements(By.CSS_SELECTOR, selector)
        
        print(f"Found {len(job_cards)} job cards with selector: {selector}")
        
        # Test extraction on first few job cards
        for i, job_card in enumerate(job_cards[:3]):
            print(f"\n--- Job Card {i+1} ---")
            
            try:
                # Get the link element (which is the job card)
                job_url = job_card.get_attribute('href')
                job_title = job_card.text.strip()
                
                print(f"URL: {job_url}")
                print(f"Title: {job_title[:100]}...")
                
                # Try to extract company
                company = extract_company_from_card(job_card)
                print(f"Company: {company}")
                
                # Try to extract location
                location = extract_location_from_card(job_card)
                print(f"Location: {location}")
                
                # Try to extract description
                description = extract_description_from_card(job_card)
                print(f"Description: {description[:100]}...")
                
                # Check if this looks like a valid job
                if job_url and job_title and len(job_title) > 10:
                    print("✓ Valid job found!")
                else:
                    print("✗ Invalid job - missing URL or title")
                
            except Exception as e:
                print(f"Error processing job card {i+1}: {e}")
        
        # Test getting job details for the first job
        if job_cards:
            first_job_url = job_cards[0].get_attribute('href')
            print(f"\n--- Testing Job Details Extraction ---")
            print(f"Testing URL: {first_job_url}")
            
            job_details = get_job_details(driver, first_job_url)
            print(f"Job details: {json.dumps(job_details, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"Error during testing: {e}")
    
    finally:
        driver.quit()

def extract_company_from_card(job_card):
    """Extract company name from job card."""
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
            company_elem = job_card.find_element(By.CSS_SELECTOR, selector)
            company_text = company_elem.text.strip()
            if company_text and len(company_text) > 2:
                return company_text
        except NoSuchElementException:
            continue
    
    return ""

def extract_location_from_card(job_card):
    """Extract location from job card."""
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
            location_elem = job_card.find_element(By.CSS_SELECTOR, selector)
            location_text = location_elem.text.strip()
            if location_text and len(location_text) > 2:
                return location_text
        except NoSuchElementException:
            continue
    
    return ""

def extract_description_from_card(job_card):
    """Extract description from job card."""
    desc_selectors = [
        "p",
        ".description",
        ".summary",
        "div[class*='description']"
    ]
    
    for selector in desc_selectors:
        try:
            desc_elem = job_card.find_element(By.CSS_SELECTOR, selector)
            desc_text = desc_elem.text.strip()
            if desc_text and len(desc_text) > 20:
                return desc_text
        except NoSuchElementException:
            continue
    
    return ""

def get_job_details(driver, job_url):
    """Get detailed job information from job detail page."""
    try:
        print(f"Getting job details: {job_url}")
        
        driver.get(job_url)
        time.sleep(3)  # Wait for page load
        
        job_details = {}
        
        # Extract title
        title_selectors = ["h1", ".job-title", ".title"]
        for selector in title_selectors:
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['title'] = title_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract company
        company_selectors = ["h1 + div span", ".company", ".employer"]
        for selector in company_selectors:
            try:
                company_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['company'] = company_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract posted date
        date_selectors = ["time", "span[aria-label='Publicado']", ".date", ".posted"]
        for selector in date_selectors:
            try:
                date_elem = driver.find_element(By.CSS_SELECTOR, selector)
                date_text = date_elem.text.strip()
                job_details['posted_date'] = date_text
                break
            except NoSuchElementException:
                continue
        
        # Extract location
        location_selectors = ["div[aria-label='location']", ".location", ".place"]
        for selector in location_selectors:
            try:
                location_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['location'] = location_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        # Extract description
        desc_selectors = [
            ".description",
            "section h2:contains('Descripción del puesto') + div",
            ".job-description",
            "div[class*='description']"
        ]
        for selector in desc_selectors:
            try:
                desc_elem = driver.find_element(By.CSS_SELECTOR, selector)
                job_details['description'] = desc_elem.text.strip()
                break
            except NoSuchElementException:
                continue
        
        return job_details
        
    except Exception as e:
        print(f"Error getting job details: {e}")
        return {}

if __name__ == "__main__":
    test_job_card_extraction()
