#!/usr/bin/env python3
"""
Advanced diagnostic script for ZonaJobs website structure
Waits for dynamic content to load and tries different approaches
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

def diagnose_zonajobs_advanced():
    """Advanced analysis of ZonaJobs website structure."""
    
    print("=" * 60)
    print("🔍 Advanced ZonaJobs Website Analysis")
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
        
        # Wait for initial content
        time.sleep(3)
        
        # Get page title
        title = driver.title
        print(f"Page title: {title}")
        
        # Try different waiting strategies
        wait = WebDriverWait(driver, 20)
        
        print("\n" + "=" * 60)
        print("⏳ WAITING FOR CONTENT TO LOAD")
        print("=" * 60)
        
        # Strategy 1: Wait for any job-related content
        print("Strategy 1: Waiting for job-related content...")
        try:
            # Wait for any element that might contain job listings
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='empleo']")))
            print("✅ Found links with 'empleo' in href")
        except TimeoutException:
            print("❌ No links with 'empleo' found after waiting")
        
        # Strategy 2: Wait for specific job card patterns
        print("\nStrategy 2: Looking for job card patterns...")
        
        # Try different selectors that might contain job cards
        job_card_selectors = [
            "div[data-testid*='job']",
            "div[class*='JobCard']",
            "div[class*='job-card']",
            "div[class*='JobItem']",
            "div[class*='job-item']",
            "div[class*='OfferCard']",
            "div[class*='offer-card']",
            "div[class*='VacancyCard']",
            "div[class*='vacancy-card']",
            "div[class*='PositionCard']",
            "div[class*='position-card']",
            "article",
            "section",
            "div[role='article']",
            "div[data-cy*='job']",
            "div[data-test*='job']",
        ]
        
        found_job_cards = []
        for selector in job_card_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    found_job_cards.append((selector, len(elements)))
                    print(f"✅ {selector}: {len(elements)} elements")
                    
                    # Show sample content
                    for i, element in enumerate(elements[:2]):
                        try:
                            text = element.text.strip()[:150]
                            print(f"   Sample {i+1}: {text}...")
                        except:
                            print(f"   Sample {i+1}: [Could not extract text]")
            except Exception as e:
                print(f"❌ {selector}: Error - {e}")
        
        # Strategy 3: Look for job links and analyze their structure
        print("\nStrategy 3: Analyzing job links structure...")
        
        try:
            job_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo']")
            print(f"Found {len(job_links)} links with 'empleo' in href")
            
            if job_links:
                # Analyze the first few job links
                for i, link in enumerate(job_links[:5]):
                    try:
                        href = link.get_attribute("href")
                        text = link.text.strip()
                        parent_tag = link.find_element(By.XPATH, "..").tag_name
                        parent_class = link.find_element(By.XPATH, "..").get_attribute("class")
                        
                        print(f"  Link {i+1}:")
                        print(f"    Text: {text}")
                        print(f"    Href: {href}")
                        print(f"    Parent: <{parent_tag} class='{parent_class}'>")
                        
                        # Look for job title in parent elements
                        try:
                            title_element = link.find_element(By.XPATH, ".//h1 | .//h2 | .//h3 | .//h4")
                            print(f"    Title element: {title_element.text.strip()}")
                        except:
                            print(f"    No title element found")
                        
                    except Exception as e:
                        print(f"  Link {i+1}: Error analyzing - {e}")
        except Exception as e:
            print(f"Error analyzing job links: {e}")
        
        # Strategy 4: Look for job titles and companies
        print("\nStrategy 4: Looking for job titles and companies...")
        
        # Common patterns for job titles
        title_selectors = [
            "h1", "h2", "h3", "h4",
            "div[class*='title']",
            "div[class*='Title']",
            "span[class*='title']",
            "span[class*='Title']",
            "a[class*='title']",
            "a[class*='Title']",
        ]
        
        found_titles = []
        for selector in title_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 5 and len(text) < 200:  # Reasonable title length
                        # Check if it looks like a job title
                        job_keywords = ['desarrollador', 'analista', 'ingeniero', 'manager', 'coordinador', 
                                      'developer', 'analyst', 'engineer', 'assistant', 'vendedor', 'operario']
                        if any(keyword in text.lower() for keyword in job_keywords):
                            found_titles.append((selector, text))
                            print(f"  Potential job title: {text}")
            except Exception as e:
                continue
        
        # Strategy 5: Look for company names
        print("\nStrategy 5: Looking for company names...")
        
        company_selectors = [
            "div[class*='company']",
            "div[class*='Company']",
            "span[class*='company']",
            "span[class*='Company']",
            "a[class*='company']",
            "a[class*='Company']",
        ]
        
        found_companies = []
        for selector in company_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text and len(text) > 2 and len(text) < 100:
                        found_companies.append((selector, text))
                        print(f"  Potential company: {text}")
            except Exception as e:
                continue
        
        # Strategy 6: Check if content is loaded via JavaScript
        print("\nStrategy 6: Checking for JavaScript-loaded content...")
        
        # Wait a bit more for any delayed content
        time.sleep(5)
        
        # Check if more content appeared
        job_links_after_wait = driver.find_elements(By.CSS_SELECTOR, "a[href*='empleo']")
        print(f"Job links after additional wait: {len(job_links_after_wait)}")
        
        # Look for any dynamic content containers
        dynamic_selectors = [
            "div[id*='root']",
            "div[id*='app']",
            "div[id*='content']",
            "div[class*='container']",
            "div[class*='main']",
            "div[class*='content']",
        ]
        
        for selector in dynamic_selectors:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    print(f"  {selector}: {len(elements)} elements")
                    for element in elements:
                        text = element.text.strip()
                        if text and len(text) > 100:
                            print(f"    Content preview: {text[:200]}...")
            except Exception as e:
                continue
        
        # Save comprehensive analysis
        analysis = {
            'url': url,
            'title': title,
            'found_job_cards': found_job_cards,
            'found_titles': found_titles,
            'found_companies': found_companies,
            'job_links_count': len(job_links_after_wait),
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        output_file = Path("outputs/zonajobs_advanced_diagnosis.json")
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(analysis, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 Advanced analysis saved to: {output_file}")
        
        # Final recommendations
        print("\n" + "=" * 60)
        print("💡 FINAL RECOMMENDATIONS")
        print("=" * 60)
        
        if found_job_cards:
            print("✅ Found potential job card containers")
            print(f"   Best selector: {found_job_cards[0][0]}")
        else:
            print("❌ No job card containers found")
        
        if found_titles:
            print("✅ Found potential job titles")
            print(f"   Count: {len(found_titles)}")
        else:
            print("❌ No job titles found")
        
        if found_companies:
            print("✅ Found potential company names")
            print(f"   Count: {len(found_companies)}")
        else:
            print("❌ No company names found")
        
        if job_links_after_wait > 0:
            print(f"✅ Found {job_links_after_wait} job links")
            print("   Strategy: Extract job URLs from links and visit each one")
        else:
            print("❌ No job links found")
        
        print("\n" + "=" * 60)
        print("✅ Advanced diagnosis completed!")
        
    except Exception as e:
        print(f"❌ Error during advanced diagnosis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            driver.quit()

if __name__ == "__main__":
    diagnose_zonajobs_advanced()
