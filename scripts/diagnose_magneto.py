#!/usr/bin/env python3
"""
Script to diagnose Magneto365 Colombia website structure.
"""

import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json
import re

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def diagnose_magneto():
    """Diagnose Magneto365 Colombia website structure."""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    # Test URLs for Magneto365 Colombia
    test_urls = [
        "https://www.magneto365.com/co/empleos",
        "https://www.magneto365.com/co/empleos?page=1",
        "https://www.magneto365.com/co/empleos?page=2",
    ]

    results = {}

    for test_url in test_urls:
        try:
            print(f"Testing URL: {test_url}")
            response = requests.get(test_url, headers=headers, timeout=30)

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
                        
                        # Check if it's an ItemList
                        if json_data.get('@type') == 'ItemList':
                            print(f"    Found ItemList with {len(json_data.get('itemListElement', []))} items")
                            for j, item in enumerate(json_data.get('itemListElement', [])[:3]):  # Show first 3
                                print(f"      Item {j+1}: {item}")
                        
                        # Check if it's a JobPosting
                        if json_data.get('@type') == 'JobPosting':
                            print(f"    Found JobPosting: {json_data.get('title', 'No title')}")
                            print(f"      Company: {json_data.get('hiringOrganization', {}).get('name', 'No company')}")
                            print(f"      Location: {json_data.get('jobLocation', {}).get('address', {}).get('addressLocality', 'No location')}")
                            
                    except json.JSONDecodeError as e:
                        print(f"    Error parsing JSON-LD {i+1}: {e}")
                
                # Look for job cards/links
                job_links = soup.find_all('a', href=True)
                job_urls = []
                
                for link in job_links:
                    href = link.get('href', '')
                    if any(keyword in href for keyword in ['/empleo/', '/trabajo/', '/job/', '/oferta/', '/puesto/']):
                        job_urls.append(href)
                
                print(f"Found {len(job_urls)} potential job URLs")
                
                # Show first few job URLs
                for i, url in enumerate(job_urls[:5]):
                    print(f"  Job URL {i+1}: {url}")
                
                # Look for pagination
                pagination_links = soup.find_all('a', href=True)
                page_urls = [link.get('href') for link in pagination_links if 'page=' in link.get('href', '')]
                print(f"Found {len(page_urls)} pagination links")
                
                # Store results
                results[test_url] = {
                    'status': response.status_code,
                    'json_ld_count': len(json_ld_scripts),
                    'job_urls_count': len(job_urls),
                    'pagination_count': len(page_urls),
                    'sample_job_urls': job_urls[:5],
                    'sample_page_urls': page_urls[:5]
                }

            else:
                print(f"✗ HTTP {response.status_code}")
                results[test_url] = {'status': response.status_code, 'error': 'HTTP Error'}

        except Exception as e:
            print(f"Error testing {test_url}: {e}")
            results[test_url] = {'error': str(e)}

    # Save results
    with open("outputs/magneto_diagnosis.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDiagnosis results saved to outputs/magneto_diagnosis.json")
    
    return results

def test_job_detail_page():
    """Test a specific job detail page to see its structure."""
    
    # Try to find a real job URL first
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    
    try:
        # Get the listing page first
        response = requests.get("https://www.magneto365.com/co/empleos", headers=headers, timeout=30)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find job links
            job_links = soup.find_all('a', href=True)
            job_urls = []
            
            for link in job_links:
                href = link.get('href', '')
                if any(keyword in href for keyword in ['/empleo/', '/trabajo/', '/job/', '/oferta/', '/puesto/']):
                    if href.startswith('/'):
                        job_urls.append(f"https://www.magneto365.com{href}")
                    elif href.startswith('http'):
                        job_urls.append(href)
                    else:
                        job_urls.append(f"https://www.magneto365.com/{href}")
            
            if job_urls:
                # Test the first job URL
                test_job_url = job_urls[0]
                print(f"\nTesting job detail page: {test_job_url}")
                
                job_response = requests.get(test_job_url, headers=headers, timeout=30)
                
                if job_response.status_code == 200:
                    job_soup = BeautifulSoup(job_response.content, 'html.parser')
                    
                    # Check for JSON-LD in job detail page
                    json_ld_scripts = job_soup.find_all('script', type='application/ld+json')
                    print(f"Found {len(json_ld_scripts)} JSON-LD scripts in job detail page")
                    
                    for i, script in enumerate(json_ld_scripts):
                        try:
                            json_data = json.loads(script.string)
                            print(f"  JSON-LD {i+1}: {json_data.get('@type', 'Unknown type')}")
                            
                            if json_data.get('@type') == 'JobPosting':
                                print(f"    Title: {json_data.get('title', 'No title')}")
                                print(f"    Company: {json_data.get('hiringOrganization', {}).get('name', 'No company')}")
                                print(f"    Location: {json_data.get('jobLocation', {}).get('address', {}).get('addressLocality', 'No location')}")
                                print(f"    Posted Date: {json_data.get('datePosted', 'No date')}")
                                print(f"    Employment Type: {json_data.get('employmentType', 'No type')}")
                                
                                # Check for salary info
                                base_salary = json_data.get('baseSalary', {})
                                if base_salary:
                                    value = base_salary.get('value', {})
                                    if value:
                                        print(f"    Salary: {value.get('value', 'No value')} {value.get('currency', 'No currency')}")
                                
                        except json.JSONDecodeError as e:
                            print(f"    Error parsing JSON-LD {i+1}: {e}")
                    
                    # Save the job detail page structure
                    with open("outputs/magneto_job_detail_sample.html", "w", encoding="utf-8") as f:
                        f.write(str(job_soup))
                    
                    print("Job detail page HTML saved to outputs/magneto_job_detail_sample.html")
                    
                else:
                    print(f"Failed to load job detail page: HTTP {job_response.status_code}")
            else:
                print("No job URLs found on listing page")
        else:
            print(f"Failed to load listing page: HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error testing job detail page: {e}")

if __name__ == "__main__":
    print("Diagnosing Magneto365 Colombia website structure...")
    
    # Run diagnosis
    results = diagnose_magneto()
    
    # Test job detail page
    test_job_detail_page()
    
    print("\nDiagnosis complete!")
