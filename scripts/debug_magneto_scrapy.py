#!/usr/bin/env python3
"""
Debug script to simulate Scrapy's JSON-LD parsing.
"""

import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json
from scrapy import Selector

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def debug_magneto_scrapy():
    """Debug Magneto JSON-LD parsing as Scrapy would do it."""
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    test_url = "https://www.magneto365.com/co/empleos"
    
    try:
        print(f"Testing URL: {test_url}")
        response = requests.get(test_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✓ Success! Status: {response.status_code}")
            
            # Create Scrapy Selector
            selector = Selector(text=response.text)
            
            # Find JSON-LD scripts using Scrapy's CSS selector
            json_ld_scripts = selector.css('script[type="application/ld+json"]')
            print(f"Found {len(json_ld_scripts)} JSON-LD scripts with Scrapy")
            
            # Analyze each JSON-LD script as Scrapy would
            for i, script in enumerate(json_ld_scripts):
                print(f"\n--- JSON-LD Script {i+1} (Scrapy) ---")
                
                # Get script content using Scrapy's get() method
                script_content = script.get()
                print(f"Script content length: {len(script_content) if script_content else 0}")
                
                if script_content:
                    print(f"First 200 characters: {script_content[:200]}")
                    print(f"Last 200 characters: {script_content[-200:]}")
                    
                    # Try to parse JSON
                    try:
                        json_data = json.loads(script_content)
                        print(f"✓ Successfully parsed JSON")
                        print(f"JSON type: {json_data.get('@type', 'Unknown')}")
                        
                        if json_data.get('@type') == 'ItemList':
                            item_list = json_data.get('itemListElement', [])
                            print(f"ItemList has {len(item_list)} items")
                            
                            # Show first few items
                            for j, item in enumerate(item_list[:3]):
                                print(f"  Item {j+1}: {item}")
                        
                    except json.JSONDecodeError as e:
                        print(f"✗ JSON parsing error: {e}")
                        print(f"Error position: {e.pos}")
                        print(f"Error line: {e.lineno}, column: {e.colno}")
                        
                        # Show the problematic area
                        if e.pos < len(script_content):
                            start = max(0, e.pos - 50)
                            end = min(len(script_content), e.pos + 50)
                            print(f"Context around error: {script_content[start:end]}")
                else:
                    print("✗ Script content is empty or None")
                    
                    # Try alternative methods
                    print("Trying alternative extraction methods:")
                    
                    # Method 1: get_text()
                    script_text = script.get_text()
                    print(f"  get_text() length: {len(script_text) if script_text else 0}")
                    
                    # Method 2: extract()
                    script_extract = script.extract()
                    print(f"  extract() length: {len(script_extract) if script_extract else 0}")
                    
                    # Method 3: xpath
                    script_xpath = script.xpath('.').get()
                    print(f"  xpath('.') length: {len(script_xpath) if script_xpath else 0}")
            
            # Also try to find scripts with different selectors
            print(f"\n--- Alternative Selectors ---")
            
            # Try without type attribute
            all_scripts = selector.css('script')
            print(f"All script tags: {len(all_scripts)}")
            
            # Try with different type patterns
            json_scripts = selector.css('script[type*="json"]')
            print(f"Scripts with 'json' in type: {len(json_scripts)}")
            
            # Try with application/json
            app_json_scripts = selector.css('script[type="application/json"]')
            print(f"Scripts with type='application/json': {len(app_json_scripts)}")
            
            for i, script in enumerate(app_json_scripts):
                content = script.get()
                if content and len(content) > 100:
                    print(f"  Script {i+1}: length={len(content)}")
                    print(f"    Preview: {content[:200]}...")
            
        else:
            print(f"✗ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Debugging Magneto JSON-LD parsing with Scrapy...")
    debug_magneto_scrapy()
    print("\nDebug complete!")
