#!/usr/bin/env python3
"""
Test script for Clarín API endpoints.
"""

import sys
import os
from pathlib import Path
import requests
import json
import time

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_clarin_api():
    """Test Clarín API endpoints with sample advert IDs."""
    
    # Sample advert IDs from the diagnosis
    sample_ids = [
        "31094346",
        "8488308", 
        "8488394",
        "8488019",
        "8488446"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Referer': 'https://clasificados.clarin.com/',
        'Origin': 'https://clasificados.clarin.com'
    }
    
    results = {}
    
    for advert_id in sample_ids:
        print(f"\nTesting advert ID: {advert_id}")
        
        # Test different URL patterns
        url_patterns = [
            f"https://clasificados.clarin.com/aviso/{advert_id}",
            f"https://clasificados.clarin.com/api/aviso/{advert_id}",
            f"https://clasificados.clarin.com/empleos/aviso/{advert_id}",
            f"https://clasificados.clarin.com/aviso/{advert_id}.json"
        ]
        
        advert_result = {
            "advert_id": advert_id,
            "successful_urls": [],
            "failed_urls": [],
            "sample_data": None
        }
        
        for url in url_patterns:
            try:
                print(f"  Testing URL: {url}")
                response = requests.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        advert_result["successful_urls"].append(url)
                        
                        # Save first successful response as sample
                        if advert_result["sample_data"] is None:
                            advert_result["sample_data"] = json_data
                        
                        print(f"    ✓ Success! Status: {response.status_code}")
                        print(f"    ✓ JSON keys: {list(json_data.keys())}")
                        
                    except json.JSONDecodeError as e:
                        advert_result["failed_urls"].append(f"{url} (JSON decode error: {e})")
                        print(f"    ✗ JSON decode error: {e}")
                        
                else:
                    advert_result["failed_urls"].append(f"{url} (HTTP {response.status_code})")
                    print(f"    ✗ HTTP {response.status_code}")
                    
            except Exception as e:
                advert_result["failed_urls"].append(f"{url} (Exception: {e})")
                print(f"    ✗ Exception: {e}")
            
            # Small delay between requests
            time.sleep(1)
        
        results[advert_id] = advert_result
    
    # Save results
    with open("outputs/clarin_api_test.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nAPI test completed! Results saved to outputs/clarin_api_test.json")
    
    # Print summary
    print("\nSummary:")
    for advert_id, result in results.items():
        print(f"  Advert {advert_id}: {len(result['successful_urls'])} successful, {len(result['failed_urls'])} failed")

if __name__ == "__main__":
    test_clarin_api()
