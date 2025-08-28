#!/usr/bin/env python3
"""
Diagnostic script for Computrabajo website structure.
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

def diagnose_computrabajo():
    """Diagnose Computrabajo website structure."""
    
    # Test URL
    test_url = "https://co.computrabajo.com/trabajo-de-sistemas-en-bogota-dc"
    
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
            result = analyze_page_structure(soup, test_url)
            
            # Save results
            with open("outputs/computrabajo_diagnosis.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            print(f"Diagnosis completed! Results saved to outputs/computrabajo_diagnosis.json")
            
        else:
            print(f"✗ HTTP {response.status_code}")
            
    except Exception as e:
        print(f"Error during diagnosis: {e}")

def analyze_page_structure(soup, url):
    """Analyze the page structure."""
    result = {
        "url": url,
        "title": soup.title.string if soup.title else "",
        "job_cards_found": 0,
        "job_links": [],
        "sample_job_data": [],
        "pagination_info": {},
        "html_structure": {}
    }
    
    # Find job cards (article elements)
    job_cards = soup.find_all('article')
    result["job_cards_found"] = len(job_cards)
    print(f"Found {len(job_cards)} job cards")
    
    # Analyze first few job cards
    for i, card in enumerate(job_cards[:5]):  # Analyze first 5 cards
        job_data = analyze_job_card(card, i + 1)
        result["sample_job_data"].append(job_data)
        
        # Extract job links
        job_link = card.find('h2').find('a') if card.find('h2') else None
        if job_link and job_link.get('href'):
            result["job_links"].append(job_link.get('href'))
    
    # Analyze pagination
    pagination = analyze_pagination(soup)
    result["pagination_info"] = pagination
    
    # Analyze HTML structure
    structure = analyze_html_structure(soup)
    result["html_structure"] = structure
    
    return result

def analyze_job_card(card, card_number):
    """Analyze a single job card."""
    job_data = {
        "card_number": card_number,
        "title": "",
        "company": "",
        "location": "",
        "salary": "",
        "posted_date": "",
        "url": "",
        "html_structure": {}
    }
    
    # Extract title from h2 a
    title_elem = card.find('h2')
    if title_elem:
        title_link = title_elem.find('a')
        if title_link:
            job_data["title"] = title_link.get_text(strip=True)
            job_data["url"] = title_link.get('href', '')
    
    # Extract company from h2 + div a
    company_elem = card.find('h2')
    if company_elem:
        next_div = company_elem.find_next_sibling('div')
        if next_div:
            company_link = next_div.find('a')
            if company_link:
                job_data["company"] = company_link.get_text(strip=True)
    
    # Extract location from p:nth-of-type(1)
    paragraphs = card.find_all('p')
    if len(paragraphs) >= 1:
        job_data["location"] = paragraphs[0].get_text(strip=True)
    
    # Extract salary from p:nth-of-type(2)
    if len(paragraphs) >= 2:
        job_data["salary"] = paragraphs[1].get_text(strip=True)
    
    # Extract posted date from p:last-of-type
    if paragraphs:
        job_data["posted_date"] = paragraphs[-1].get_text(strip=True)
    
    # Analyze HTML structure of the card
    job_data["html_structure"] = {
        "tag_name": card.name,
        "classes": card.get('class', []),
        "has_h2": bool(card.find('h2')),
        "has_links": len(card.find_all('a')),
        "paragraphs": len(paragraphs),
        "child_elements": [child.name for child in card.children if hasattr(child, 'name')]
    }
    
    return job_data

def analyze_pagination(soup):
    """Analyze pagination structure."""
    pagination_info = {
        "has_pagination": False,
        "current_page": 1,
        "total_pages": 0,
        "next_page_url": "",
        "pagination_elements": []
    }
    
    # Look for pagination elements
    pagination_elements = soup.find_all(['nav', 'ul', 'div'], class_=lambda x: x and 'pagination' in x.lower())
    
    if pagination_elements:
        pagination_info["has_pagination"] = True
        
        for elem in pagination_elements:
            pagination_info["pagination_elements"].append({
                "tag": elem.name,
                "classes": elem.get('class', []),
                "text": elem.get_text(strip=True)[:100]  # First 100 chars
            })
    
    # Look for page numbers
    page_links = soup.find_all('a', href=lambda x: x and '?p=' in x)
    if page_links:
        page_numbers = []
        for link in page_links:
            href = link.get('href', '')
            if '?p=' in href:
                try:
                    page_num = int(href.split('?p=')[1])
                    page_numbers.append(page_num)
                except:
                    pass
        
        if page_numbers:
            pagination_info["total_pages"] = max(page_numbers)
    
    return pagination_info

def analyze_html_structure(soup):
    """Analyze overall HTML structure."""
    structure = {
        "body_classes": soup.body.get('class', []) if soup.body else [],
        "main_elements": [],
        "article_elements": len(soup.find_all('article')),
        "h1_elements": len(soup.find_all('h1')),
        "h2_elements": len(soup.find_all('h2')),
        "a_elements": len(soup.find_all('a')),
        "p_elements": len(soup.find_all('p')),
        "common_classes": {}
    }
    
    # Find main elements
    main_elements = soup.find_all(['main', 'div'], role='main')
    for elem in main_elements:
        structure["main_elements"].append({
            "tag": elem.name,
            "classes": elem.get('class', []),
            "id": elem.get('id', '')
        })
    
    # Analyze common classes
    all_elements = soup.find_all()
    class_counts = {}
    for elem in all_elements:
        classes = elem.get('class', [])
        for cls in classes:
            class_counts[cls] = class_counts.get(cls, 0) + 1
    
    # Get top 10 most common classes
    sorted_classes = sorted(class_counts.items(), key=lambda x: x[1], reverse=True)
    structure["common_classes"] = dict(sorted_classes[:10])
    
    return structure

if __name__ == "__main__":
    diagnose_computrabajo()
