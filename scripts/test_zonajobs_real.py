#!/usr/bin/env python3
"""
Test script for real ZonaJobs spider
Runs the Selenium-based spider to scrape real job data
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_zonajobs_real():
    """Test the real ZonaJobs spider."""
    
    print("=" * 60)
    print(" Testing Real ZonaJobs Spider")
    print("=" * 60)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Country: AR (Argentina)")
    print("Max Pages: 3")
    print("Strategy: Selenium WebDriver for React SPA")
    print("=" * 60)
    
    try:
        # Import Scrapy components
        from scrapy.crawler import CrawlerProcess
        from scrapy.utils.project import get_project_settings
        
        # Import our spider
        from src.scraper.spiders.zonajobs_spider import ZonaJobsSpider
        
        # Setup project settings
        os.environ.setdefault('SCRAPY_SETTINGS_MODULE', 'src.scraper.settings')
        settings = get_project_settings()
        
        # Configure settings for Selenium spider - disable database pipeline
        settings.update({
            'FEEDS': {
                'outputs/zonajobs_real.json': {
                    'format': 'json',
                    'encoding': 'utf8',
                    'indent': 2,
                    'overwrite': True,
                }
            },
            'LOG_LEVEL': 'INFO',
            'DOWNLOAD_DELAY': 3,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
            'DOWNLOAD_TIMEOUT': 60,
            # Disable database pipeline for standalone testing
            'ITEM_PIPELINES': {},
        })
        
        # Create crawler process
        process = CrawlerProcess(settings)
        
        # Add spider to process
        process.crawl(
            ZonaJobsSpider,
            country='AR',
            max_pages=3
        )
        
        # Start crawling
        print("Starting ZonaJobs spider...")
        process.start()
        
        # Check results
        output_file = Path("outputs/zonajobs_real.json")
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                jobs = json.load(f)
            
            print("\n" + "=" * 60)
            print("📊 SCRAPING RESULTS")
            print("=" * 60)
            print(f"Total jobs scraped: {len(jobs)}")
            print(f"Output file: {output_file}")
            print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if jobs:
                print("\n📋 SAMPLE JOBS:")
                print("-" * 60)
                for i, job in enumerate(jobs[:5], 1):  # Show first 5 jobs
                    print(f"{i}. {job.get('title', 'No title')}")
                    print(f"   Company: {job.get('company', 'No company')}")
                    print(f"   Location: {job.get('location', 'No location')}")
                    print(f"   URL: {job.get('url', 'No URL')}")
                    print(f"   Posted: {job.get('posted_date', 'No date')}")
                    print("-" * 60)
                
                print("\n SUCCESS: Real job data scraped successfully!")
                print(f" Full results saved to: {output_file}")
                
                # Check for scraping summary
                summary_file = Path("outputs/zonajobs_scraping_summary.json")
                if summary_file.exists():
                    print(f" Scraping summary: {summary_file}")
            else:
                print("  No jobs were scraped.")
        
        else:
            print(" Output file not found.")
        
        print("=" * 60)
        print(" Test completed!")
        
    except Exception as e:
        print(f"\n Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_zonajobs_real()
