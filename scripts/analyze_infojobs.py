#!/usr/bin/env python3
"""
Analyze Infojobs website structure to understand real selectors
"""

import requests
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
import time

def analyze_infojobs_structure():
    """Analyze Infojobs website structure."""
    
    # Test different country URLs
    test_urls = {
        'CO': 'https://co.infojobs.net/empleos',
        'MX': 'https://mx.infojobs.net/empleos', 
        'AR': 'https://ar.infojobs.net/empleos'
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    results = {}
    
    for country, url in test_urls.items():
        print(f"Analyzing {country}: {url}")
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"Status: {response.status_code}")
            
            if response.status_code == 200:
                html = response.text
                
                # Look for job listings
                job_indicators = [
                    'job-card', 'job-item', 'job-listing', 'offer-card',
                    'vacancy', 'position', 'empleo', 'trabajo'
                ]
                
                found_selectors = []
                for indicator in job_indicators:
                    if indicator in html:
                        found_selectors.append(indicator)
                
                # Look for pagination
                pagination_indicators = [
                    'pagination', 'next', 'siguiente', 'page', 'página'
                ]
                
                pagination_found = []
                for indicator in pagination_indicators:
                    if indicator in html:
                        pagination_found.append(indicator)
                
                results[country] = {
                    'status': response.status_code,
                    'url': url,
                    'content_length': len(html),
                    'job_indicators': found_selectors,
                    'pagination_indicators': pagination_found,
                    'sample_html': html[:2000] if len(html) > 2000 else html
                }
                
                print(f"  Content length: {len(html)}")
                print(f"  Job indicators found: {found_selectors}")
                print(f"  Pagination indicators: {pagination_found}")
                
            else:
                results[country] = {
                    'status': response.status_code,
                    'url': url,
                    'error': f"HTTP {response.status_code}"
                }
                print(f"  Error: HTTP {response.status_code}")
                
        except Exception as e:
            results[country] = {
                'url': url,
                'error': str(e)
            }
            print(f"  Error: {e}")
        
        print("-" * 50)
        time.sleep(2)  # Be respectful
    
    # Save analysis results
    output_file = Path("outputs/infojobs_analysis.json")
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"Analysis saved to: {output_file}")
    
    return results

if __name__ == "__main__":
    analyze_infojobs_structure()
