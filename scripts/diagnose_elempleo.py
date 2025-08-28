#!/usr/bin/env python3
"""
Diagnostic script for Elempleo job detail page structure.
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

def diagnose_elempleo():
    """Diagnose Elempleo job detail page structure."""
    
    # Test URL - using a real job detail page
    test_url = "https://www.elempleo.com/co/ofertas-trabajo/ingeniero-comercial-de-proyectos-bogota-825424"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    try:
        print(f"Testing URL: {test_url}")
        response = requests.get(test_url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            print(f"✓ Success! Status: {response.status_code}")
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Analyze structure
            result = analyze_job_page_structure(soup, test_url)
            
            # Save results
            with open("outputs/elempleo_diagnosis.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Diagnosis completed! Results saved to outputs/elempleo_diagnosis.json")
            
        else:
            print(f"✗ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error during diagnosis: {e}")

def analyze_job_page_structure(soup, url):
    """Analyze the job detail page structure."""
    result = {
        "url": url,
        "title": soup.title.string if soup.title else "",
        "extracted_data": {},
        "selectors_found": {},
        "html_structure": {}
    }
    
    # Test specific selectors mentioned in requirements
    selectors_to_test = {
        "title": [
            "h1.ee-offer-title .js-jobOffer-title",
            "h1.ee-offer-title",
            "h1",
            ".js-jobOffer-title"
        ],
        "company": [
            "h2.ee-company-title strong",
            "h2.ee-company-title",
            ".company-name",
            ".employer"
        ],
        "salary": [
            "span.js-joboffer-salary",
            ".salary",
            ".wage",
            "[class*='salary']"
        ],
        "location": [
            "span.js-joboffer-city",
            ".location",
            ".city",
            "[class*='location']"
        ],
        "posted_date": [
            "span.js-publish-date",
            ".date",
            ".posted",
            "[class*='date']"
        ],
        "category": [
            "span.js-position-area",
            ".category",
            ".position-area"
        ],
        "profession": [
            "span.js-profession",
            ".profession"
        ],
        "education_level": [
            "span.js-education-level",
            ".education-level"
        ],
        "sector": [
            "span.js-sector",
            ".sector"
        ],
        "description": [
            "div.description-block p span",
            "div.description-block p",
            ".description",
            ".job-description"
        ],
        "requirements": [
            "h2:contains('Requisitos') + p span",
            ".requirements",
            ".skills"
        ]
    }
    
    # Test each selector
    for field, selector_list in selectors_to_test.items():
        result["selectors_found"][field] = {}
        
        for selector in selector_list:
            try:
                if "contains" in selector:
                    # Handle XPath-like contains selector
                    if "h2:contains('Requisitos')" in selector:
                        h2_elements = soup.find_all('h2')
                        for h2 in h2_elements:
                            if 'requisitos' in h2.get_text().lower():
                                next_p = h2.find_next_sibling('p')
                                if next_p:
                                    spans = next_p.find_all('span')
                                    if spans:
                                        result["selectors_found"][field][selector] = [span.get_text(strip=True) for span in spans]
                                        break
                else:
                    # Handle CSS selector
                    elements = soup.select(selector)
                    if elements:
                        if field == "description":
                            # For description, get all text from all matching elements
                            texts = []
                            for elem in elements:
                                if elem.name == 'span':
                                    texts.append(elem.get_text(strip=True))
                                else:
                                    # Get all span texts within the element
                                    spans = elem.find_all('span')
                                    for span in spans:
                                        texts.append(span.get_text(strip=True))
                            result["selectors_found"][field][selector] = texts
                        else:
                            # For other fields, get text from first element
                            result["selectors_found"][field][selector] = elements[0].get_text(strip=True)
                    else:
                        result["selectors_found"][field][selector] = None
                        
            except Exception as e:
                result["selectors_found"][field][selector] = f"Error: {str(e)}"
    
    # Extract actual data using best available selectors
    result["extracted_data"] = {
        "title": extract_best_value(result["selectors_found"]["title"]),
        "company": extract_best_value(result["selectors_found"]["company"]),
        "salary": extract_best_value(result["selectors_found"]["salary"]),
        "location": extract_best_value(result["selectors_found"]["location"]),
        "posted_date": extract_best_value(result["selectors_found"]["posted_date"]),
        "category": extract_best_value(result["selectors_found"]["category"]),
        "profession": extract_best_value(result["selectors_found"]["profession"]),
        "education_level": extract_best_value(result["selectors_found"]["education_level"]),
        "sector": extract_best_value(result["selectors_found"]["sector"]),
        "description": extract_best_value(result["selectors_found"]["description"], is_list=True),
        "requirements": extract_best_value(result["selectors_found"]["requirements"], is_list=True)
    }
    
    # Analyze HTML structure
    result["html_structure"] = {
        "h1_elements": len(soup.find_all('h1')),
        "h2_elements": len(soup.find_all('h2')),
        "span_elements": len(soup.find_all('span')),
        "div_elements": len(soup.find_all('div')),
        "p_elements": len(soup.find_all('p')),
        "classes_with_js": [cls for cls in soup.find_all(class_=True) if 'js-' in str(cls.get('class'))],
        "classes_with_ee": [cls for cls in soup.find_all(class_=True) if 'ee-' in str(cls.get('class'))],
        "common_classes": get_common_classes(soup)
    }
    
    return result

def extract_best_value(selector_results, is_list=False):
    """Extract the best available value from selector results."""
    for selector, value in selector_results.items():
        if value is not None and value != "":
            if is_list and isinstance(value, list):
                return " ".join(value) if value else ""
            elif not is_list and isinstance(value, str):
                return value
            elif is_list and isinstance(value, str):
                return value
    return ""

def get_common_classes(soup):
    """Get the most common CSS classes on the page."""
    all_elements = soup.find_all()
    class_counts = {}
    
    for elem in all_elements:
        classes = elem.get('class', [])
        if isinstance(classes, str):
            classes = [classes]
        for cls in classes:
            class_counts[cls] = class_counts.get(cls, 0) + 1
    
    # Get top 15 most common classes
    sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
    return dict(sorted_classes[:15])

if __name__ == "__main__":
    diagnose_elempleo()
