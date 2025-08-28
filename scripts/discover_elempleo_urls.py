#!/usr/bin/env python3
"""
Script to discover real Elempleo job URLs.
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

def discover_elempleo_urls():
    """Discover real Elempleo job URLs."""
    
    # Try to find real job URLs by searching for common patterns
    # We'll try to access some public pages that might contain job links
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    discovered_urls = []
    
    # Try different approaches to find real job URLs
    test_urls = [
        "https://www.elempleo.com/co",
        "https://www.elempleo.com/co/empresas",
        "https://www.elempleo.com/co/buscar-empleo",
        "https://www.elempleo.com/co/ofertas-empleo",
    ]
    
    for test_url in test_urls:
        try:
            print(f"Testing URL: {test_url}")
            response = requests.get(test_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print(f"✓ Success! Status: {response.status_code}")
                
                # Parse HTML
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for job links
                job_links = find_job_links(soup, test_url)
                discovered_urls.extend(job_links)
                
                print(f"Found {len(job_links)} potential job links")
                
            else:
                print(f"✗ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"Error testing {test_url}: {e}")
    
    # Remove duplicates and save results
    unique_urls = list(set(discovered_urls))
    
    print(f"\nTotal unique job URLs discovered: {len(unique_urls)}")
    
    # Save discovered URLs
    with open("outputs/elempleo_discovered_urls.json", "w", encoding="utf-8") as f:
        json.dump({
            "discovered_urls": unique_urls,
            "total_count": len(unique_urls)
        }, f, indent=2, ensure_ascii=False)
    
    print(f"Discovered URLs saved to outputs/elempleo_discovered_urls.json")
    
    return unique_urls

def find_job_links(soup, base_url):
    """Find job links in the HTML."""
    job_links = []
    
    # Look for links that match job URL patterns
    all_links = soup.find_all('a', href=True)
    
    for link in all_links:
        href = link.get('href', '')
        
        # Check if it's a job URL
        if is_job_url(href):
            # Make absolute URL
            if href.startswith('/'):
                full_url = f"https://www.elempleo.com{href}"
            elif href.startswith('http'):
                full_url = href
            else:
                full_url = f"{base_url.rstrip('/')}/{href.lstrip('/')}"
            
            job_links.append(full_url)
    
    return job_links

def is_job_url(href):
    """Check if a URL is likely a job detail page."""
    job_patterns = [
        r'/ofertas-trabajo/',
        r'/ofertas-empleo/',
        r'/empleo/',
        r'/trabajo/',
        r'/oferta/',
        r'/job/',
        r'/vacante/',
        r'/puesto/'
    ]
    
    for pattern in job_patterns:
        if re.search(pattern, href, re.IGNORECASE):
            return True
    
    return False

def create_sample_urls():
    """Create a list of sample URLs based on common Elempleo patterns."""
    # These are example URLs based on the typical Elempleo URL structure
    # In a real scenario, these would be discovered from actual searches
    
    sample_urls = [
        # These are example patterns - they may not be real
        "https://www.elempleo.com/co/ofertas-trabajo/desarrollador-software-bogota-123456",
        "https://www.elempleo.com/co/ofertas-trabajo/ingeniero-sistemas-medellin-123457",
        "https://www.elempleo.com/co/ofertas-trabajo/analista-datos-cali-123458",
        "https://www.elempleo.com/co/ofertas-trabajo/tecnico-soporte-bogota-123459",
        "https://www.elempleo.com/co/ofertas-trabajo/arquitecto-software-medellin-123460",
        "https://www.elempleo.com/co/ofertas-trabajo/devops-engineer-bogota-123461",
        "https://www.elempleo.com/co/ofertas-trabajo/data-scientist-cali-123462",
        "https://www.elempleo.com/co/ofertas-trabajo/qa-engineer-medellin-123463",
        "https://www.elempleo.com/co/ofertas-trabajo/full-stack-developer-bogota-123464",
        "https://www.elempleo.com/co/ofertas-trabajo/frontend-developer-cali-123465"
    ]
    
    return sample_urls

if __name__ == "__main__":
    print("Attempting to discover real Elempleo job URLs...")
    
    # Try to discover real URLs
    discovered_urls = discover_elempleo_urls()
    
    if not discovered_urls:
        print("\nNo real URLs discovered. Creating sample URLs for testing...")
        sample_urls = create_sample_urls()
        
        with open("outputs/elempleo_sample_urls.json", "w", encoding="utf-8") as f:
            json.dump({
                "sample_urls": sample_urls,
                "note": "These are sample URLs for testing purposes. Real URLs would need to be discovered from actual searches or external sources."
            }, f, indent=2, ensure_ascii=False)
        
        print(f"Sample URLs saved to outputs/elempleo_sample_urls.json")
        print("Note: These sample URLs may not work as they are examples only.")
