#!/usr/bin/env python3
"""
Script to test a specific Magneto job detail page.
"""

import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_job_detail_page():
    """Test a specific Magneto job detail page."""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # Test with a specific job URL from the diagnostic
    test_job_url = "https://www.magneto365.com/co/empleos/representante-bilingue-para-campana-presencial-barranquilla-597301"
    
    try:
        print(f"Testing job detail page: {test_job_url}")
        response = requests.get(test_job_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✓ Success! Status: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for JSON-LD scripts
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            print(f"Found {len(json_ld_scripts)} JSON-LD scripts")
            
            # Analyze each JSON-LD script
            for i, script in enumerate(json_ld_scripts):
                try:
                    json_data = json.loads(script.string)
                    print(f"  JSON-LD {i+1}: {json_data.get('@type', 'Unknown type')}")
                    
                    # Check if it's a JobPosting
                    if json_data.get('@type') == 'JobPosting':
                        print(f"    Found JobPosting!")
                        print(f"      Title: {json_data.get('title', 'No title')}")
                        print(f"      Company: {json_data.get('hiringOrganization', {}).get('name', 'No company')}")
                        
                        # Location info
                        job_location = json_data.get('jobLocation', {})
                        address = job_location.get('address', {})
                        print(f"      City: {address.get('addressLocality', 'No city')}")
                        print(f"      Region: {address.get('addressRegion', 'No region')}")
                        print(f"      Country: {address.get('addressCountry', 'No country')}")
                        
                        # Date info
                        print(f"      Posted Date: {json_data.get('datePosted', 'No date')}")
                        
                        # Employment type
                        print(f"      Employment Type: {json_data.get('employmentType', 'No type')}")
                        
                        # Salary info
                        base_salary = json_data.get('baseSalary', {})
                        if base_salary:
                            value = base_salary.get('value', {})
                            if value:
                                print(f"      Salary Value: {value.get('value', 'No value')}")
                                print(f"      Salary Currency: {value.get('currency', 'No currency')}")
                                print(f"      Salary Unit: {base_salary.get('unitText', 'No unit')}")
                        
                        # Description
                        description = json_data.get('description', 'No description')
                        print(f"      Description length: {len(description)} characters")
                        print(f"      Description preview: {description[:200]}...")
                        
                        # Save the full JSON-LD data
                        with open("outputs/magneto_jobposting_sample.json", "w", encoding="utf-8") as f:
                            json.dump(json_data, f, indent=2, ensure_ascii=False)
                        
                        print("      Full JobPosting JSON-LD saved to outputs/magneto_jobposting_sample.json")
                        
                except json.JSONDecodeError as e:
                    print(f"    Error parsing JSON-LD {i+1}: {e}")
            
            # Also check for regular HTML elements as fallback
            print("\nChecking HTML elements as fallback:")
            
            # Title
            title_selectors = ["h1", "h1.job-title", ".job-title", ".title"]
            for selector in title_selectors:
                title = soup.select_one(selector)
                if title:
                    print(f"  Title (HTML): {title.get_text(strip=True)}")
                    break
            
            # Company
            company_selectors = [".company", ".empresa", ".company-name", ".employer"]
            for selector in company_selectors:
                company = soup.select_one(selector)
                if company:
                    print(f"  Company (HTML): {company.get_text(strip=True)}")
                    break
            
            # Location
            location_selectors = [".location", ".ubicacion", ".place", ".city"]
            for selector in location_selectors:
                location = soup.select_one(selector)
                if location:
                    print(f"  Location (HTML): {location.get_text(strip=True)}")
                    break
            
        else:
            print(f"✗ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error testing job detail page: {e}")

if __name__ == "__main__":
    print("Testing Magneto job detail page...")
    test_job_detail_page()
    print("\nTest complete!")
