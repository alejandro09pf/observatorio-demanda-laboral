"""
Direct scraper for hiring.cafe using requests library.
Bypasses Scrapy's bot detection issues.
"""
import requests
import json
import time
import random
import psycopg2
import hashlib
from datetime import datetime
from typing import Dict, Any

# Database connection parameters
DB_PARAMS = {
    'host': '127.0.0.1',
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456',
}

def connect_db():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        return conn
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None

def save_job(conn, job_data: Dict[str, Any], country: str):
    """Save job to database"""
    try:
        cursor = conn.cursor()

        # Extract job information
        job_info = job_data.get('job_information', {})
        processed_data = job_data.get('v5_processed_job_data', {})

        title = job_info.get('title', '')
        company = processed_data.get('company_name', '')
        description = job_info.get('description', '')
        requirements = processed_data.get('requirements_summary', '')

        location = processed_data.get('formatted_workplace_location', country)
        workplace_type = processed_data.get('workplace_type', 'Not specified')
        url = job_info.get('apply_url', '') or job_info.get('url', '')

        # Extract salary
        is_transparent = processed_data.get('is_compensation_transparent', False)
        yearly_min = processed_data.get('yearly_min_compensation')
        yearly_max = processed_data.get('yearly_max_compensation')

        if is_transparent and yearly_min and yearly_max:
            salary_raw = f"{yearly_min}-{yearly_max} USD/year"
        elif is_transparent and yearly_min:
            salary_raw = f"{yearly_min}+ USD/year"
        else:
            salary_raw = "Not disclosed"

        # Extract posted date
        posted_date = job_info.get('posted_date') or job_info.get('created_at')
        if posted_date:
            try:
                posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00')).date().isoformat()
            except:
                posted_date = datetime.today().date().isoformat()
        else:
            posted_date = datetime.today().date().isoformat()

        # Create content hash
        content_string = f"{title}{description}{requirements}"
        content_hash = hashlib.sha256(content_string.encode("utf-8")).hexdigest()

        # Insert into database
        cursor.execute("""
            INSERT INTO raw_jobs (
                portal, country, url, title, company, location,
                description, requirements, salary_raw, contract_type,
                remote_type, posted_date, content_hash, scraped_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (content_hash) DO NOTHING
        """, (
            'hiring_cafe',
            country,
            url,
            title,
            company,
            location,
            description,
            requirements,
            salary_raw,
            'Full-time',
            workplace_type,
            posted_date,
            content_hash
        ))

        conn.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"❌ Error saving job: {e}")
        conn.rollback()
        return False

def scrape_hiring_cafe(country_code: str = 'CO', max_pages: int = None, stop_on_duplicates_threshold: float = 0.95):
    """
    Scrape hiring.cafe for a specific country.

    Args:
        country_code: Country code (CO, MX, AR)
        max_pages: Maximum pages to scrape (None = unlimited, runs until no results)
        stop_on_duplicates_threshold: Stop if duplicate rate exceeds this (0.95 = 95%)
    """

    api_url = 'https://hiring.cafe/api/search-jobs'

    # Country configurations
    countries = {
        'CO': {'formatted_address': 'Colombia', 'lat': '4.5981', 'lon': '-74.0799', 'short_name': 'CO'},
        'MX': {'formatted_address': 'Mexico', 'lat': '23.6345', 'lon': '-102.5528', 'short_name': 'MX'},
        'AR': {'formatted_address': 'Argentina', 'lat': '-38.4161', 'lon': '-63.6167', 'short_name': 'AR'},
    }

    if country_code not in countries:
        print(f"❌ Unsupported country: {country_code}")
        return

    country_config = countries[country_code]

    # Connect to database
    conn = connect_db()
    if not conn:
        return

    print(f"\n{'='*80}")
    print(f"🚀 Starting hiring.cafe scraper for {country_config['formatted_address']}")
    if max_pages:
        print(f"📄 Max pages: {max_pages}")
    else:
        print(f"📄 Mode: Scrape until no more results (unlimited)")
    print(f"🛑 Stop if duplicate rate > {stop_on_duplicates_threshold*100:.0f}%")
    print(f"{'='*80}\n")

    workplace_types = ["Remote", "Hybrid", "Onsite"]
    seniority_levels = ["No Prior Experience Required", "Entry Level", "Mid Level", "Senior Level"]

    total_jobs = 0
    inserted_jobs = 0
    duplicate_jobs = 0
    consecutive_empty_pages = 0

    page = 1
    while True:
        # Check stopping conditions
        if max_pages and page > max_pages:
            print(f"\n✅ Reached max_pages limit ({max_pages}). Stopping.")
            break
        if page > 1:
            delay = random.uniform(15, 18)
            print(f"⏱️  Waiting {delay:.2f} seconds before page {page}...")
            time.sleep(delay)

        payload = {
            "size": 100,
            "page": page,
            "searchState": {
                "locations": [{
                    "formatted_address": country_config['formatted_address'],
                    "types": ["country"],
                    "geometry": {
                        "location": {
                            "lat": country_config['lat'],
                            "lon": country_config['lon']
                        }
                    },
                    "id": "user_country",
                    "address_components": [{
                        "long_name": country_config['formatted_address'],
                        "short_name": country_config['short_name'],
                        "types": ["country"]
                    }],
                    "options": {
                        "flexible_regions": ["anywhere_in_continent", "anywhere_in_world"]
                    }
                }],
                "workplaceTypes": workplace_types,
                "defaultToUserLocation": True,
                "userLocation": None,
                "physicalEnvironments": ["Office", "Outdoor", "Vehicle", "Industrial", "Customer-Facing"],
                "physicalLaborIntensity": ["Low", "Medium", "High"],
                "physicalPositions": ["Sitting", "Standing"],
                "oralCommunicationLevels": ["Low", "Medium", "High"],
                "computerUsageLevels": ["Low", "Medium", "High"],
                "cognitiveDemandLevels": ["Low", "Medium", "High"],
                "currency": {"label": "Any", "value": None},
                "frequency": {"label": "Any", "value": None},
                "minCompensationLowEnd": None,
                "minCompensationHighEnd": None,
                "maxCompensationLowEnd": None,
                "maxCompensationHighEnd": None,
                "restrictJobsToTransparentSalaries": False,
                "calcFrequency": "Yearly",
                "commitmentTypes": ["Full Time", "Part Time", "Contract", "Internship", "Temporary", "Seasonal", "Volunteer"],
                "jobTitleQuery": "",
                "jobDescriptionQuery": "",
                "associatesDegreeFieldsOfStudy": [],
                "excludedAssociatesDegreeFieldsOfStudy": [],
                "bachelorsDegreeFieldsOfStudy": [],
                "excludedBachelorsDegreeFieldsOfStudy": [],
                "mastersDegreeFieldsOfStudy": [],
                "excludedMastersDegreeFieldsOfStudy": [],
                "doctorateDegreeFieldsOfStudy": [],
                "excludedDoctorateDegreeFieldsOfStudy": [],
                "associatesDegreeRequirements": [],
                "bachelorsDegreeRequirements": [],
                "mastersDegreeRequirements": [],
                "doctorateDegreeRequirements": [],
                "licensesAndCertifications": [],
                "excludedLicensesAndCertifications": [],
                "excludeAllLicensesAndCertifications": False,
                "seniorityLevel": seniority_levels,
                "roleTypes": ["Individual Contributor", "People Manager"],
                "roleYoeRange": [0, 20],
                "excludedCompanyNames": [],
                "usaGovPref": None,
                "industries": [],
                "excludedIndustries": [],
                "companyKeywords": [],
                "companyKeywordsBooleanOperator": "OR",
                "excludedCompanyKeywords": [],
                "hideJobTypes": [],
                "encouragedToApply": [],
                "searchQuery": ""
            }
        }

        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        try:
            response = requests.post(api_url, json=payload, headers=headers)

            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])

                # Check if no results found
                if not results:
                    consecutive_empty_pages += 1
                    print(f"⚠️  Page {page}: No results found (empty page #{consecutive_empty_pages})")

                    if consecutive_empty_pages >= 3:
                        print(f"\n✅ Found 3 consecutive empty pages. All jobs scraped!")
                        break

                    page += 1
                    continue

                # Reset empty page counter
                consecutive_empty_pages = 0

                print(f"📄 Page {page}: Found {len(results)} jobs")

                page_inserted = 0
                page_duplicates = 0

                for job in results:
                    if save_job(conn, job, country_code):
                        page_inserted += 1
                        inserted_jobs += 1
                    else:
                        page_duplicates += 1
                        duplicate_jobs += 1
                    total_jobs += 1

                # Calculate duplicate rate for this page
                duplicate_rate = page_duplicates / len(results) if results else 0

                print(f"   ✅ Inserted: {page_inserted}, ⏭️  Duplicates: {page_duplicates} ({duplicate_rate*100:.1f}% dup rate)")

                # Check if we should stop due to CONSECUTIVE pages with high duplicate rate
                # Don't stop on single high-duplicate pages - keep going to find older jobs
                # (Recent jobs might be duplicates, but older jobs further in pagination are new)
                # Commented out to ensure we scrape all historical data
                # if total_jobs > 500 and duplicate_rate > stop_on_duplicates_threshold:
                #     print(f"\n🛑 High duplicate rate ({duplicate_rate*100:.1f}% > {stop_on_duplicates_threshold*100:.0f}%)")
                #     print(f"   This suggests we've already scraped most recent jobs. Stopping.")
                #     break

            elif response.status_code == 429:
                print(f"❌ Rate limited at page {page}. Stopping.")
                break
            else:
                print(f"⚠️  Error {response.status_code} at page {page}. Stopping.")
                break

        except Exception as e:
            print(f"💥 Exception at page {page}: {e}")
            break

        page += 1

    # Close database connection
    conn.close()

    print(f"\n{'='*80}")
    print(f"📊 SCRAPING SUMMARY")
    print(f"{'='*80}")
    print(f"✅ Total jobs found: {total_jobs}")
    print(f"✅ Jobs inserted: {inserted_jobs}")
    print(f"⏭️  Duplicates skipped: {duplicate_jobs}")
    print(f"📊 Pages scraped: {page}")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    import sys

    country = sys.argv[1] if len(sys.argv) > 1 else 'CO'
    max_pages = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].lower() != 'unlimited' else None

    scrape_hiring_cafe(country, max_pages)
