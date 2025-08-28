#!/usr/bin/env python3
"""
Debug script to examine Magneto JSON-LD scripts in detail.
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

def debug_magneto_json():
    """Debug Magneto JSON-LD scripts."""
    
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
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find JSON-LD scripts
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            print(f"Found {len(json_ld_scripts)} JSON-LD scripts")
            
            # Analyze each JSON-LD script in detail
            for i, script in enumerate(json_ld_scripts):
                print(f"\n--- JSON-LD Script {i+1} ---")
                
                # Get the script content
                script_content = script.string
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
            
            # Also check for any script tags that might contain JSON-LD
            all_scripts = soup.find_all('script')
            print(f"\n--- All Script Tags ({len(all_scripts)} total) ---")
            
            for i, script in enumerate(all_scripts):
                script_type = script.get('type', 'No type')
                script_content = script.string
                
                if script_content and len(script_content) > 100:
                    print(f"Script {i+1}: type='{script_type}', length={len(script_content)}")
                    
                    # Check if it looks like JSON-LD
                    if script_content.strip().startswith('{') and '@context' in script_content:
                        print(f"  Looks like JSON-LD!")
                        try:
                            json_data = json.loads(script_content)
                            print(f"  JSON type: {json_data.get('@type', 'Unknown')}")
                        except json.JSONDecodeError as e:
                            print(f"  JSON parsing error: {e}")
            
        else:
            print(f"✗ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("Debugging Magneto JSON-LD scripts...")
    debug_magneto_json()
    print("\nDebug complete!")
