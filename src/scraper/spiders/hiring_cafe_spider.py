"""
Hiring.cafe spider for Labor Market Observatory.
Scrapes jobs from Colombia, Mexico, and Argentina using the hiring.cafe API.
"""

import scrapy
import json
import random
import time
from datetime import datetime
from typing import Dict, Any, List
from ..items import JobItem
from .base_spider import BaseSpider

class HiringCafeSpider(BaseSpider):
    name = 'hiring_cafe'
    allowed_domains = ['hiring.cafe']
    
    # Spider configuration - override base settings for API calls
    # Conservative settings to avoid 429 rate limiting
    custom_settings = {
        'DOWNLOAD_DELAY': 5,  # Increased from 2 to 5 seconds
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 1,  # Reduced from 2 to 1 (sequential)
        'CONCURRENT_REQUESTS': 1,  # Only 1 request at a time globally
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 5,  # Increased from 2 to 5
        'AUTOTHROTTLE_MAX_DELAY': 60,  # Increased from 5 to 60 seconds
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,
        'ROBOTSTXT_OBEY': False,
        'RETRY_TIMES': 3,  # Retry up to 3 times on 429
        'RETRY_HTTP_CODES': [429, 500, 502, 503, 504, 408],  # Include 429
        'HTTPCACHE_ENABLED': False,  # Disable cache to prevent replaying 429 errors
    }
    
    def __init__(self, *args, **kwargs):
        # Initialize base spider first
        super().__init__(*args, **kwargs)
        
        # Override portal name
        self.portal = 'hiring_cafe'
        
        # Country configurations
        self.countries = {
            'CO': {
                'formatted_address': 'Colombia',
                'lat': '4.5981',
                'lon': '-74.0799',
                'short_name': 'CO'
            },
            'MX': {
                'formatted_address': 'Mexico',
                'lat': '23.6345',
                'lon': '-102.5528',
                'short_name': 'MX'
            },
            'AR': {
                'formatted_address': 'Argentina',
                'lat': '-38.4161',
                'lon': '-63.6167',
                'short_name': 'AR'
            }
        }
        
        # User agents will be handled by middleware - no hardcoded rotation logic
        
        # Validate country
        if self.country not in self.countries:
            raise ValueError(f"Unsupported country: {self.country}. Supported: {list(self.countries.keys())}")
    
    def generate_page_request(self, page: int):
        """Generate a single page request."""
        # API endpoint
        api_url = 'https://hiring.cafe/api/search-jobs'

        # Default parameters
        workplace_types = ["Remote", "Hybrid", "Onsite"]
        seniority_levels = ["No Prior Experience Required", "Entry Level", "Mid Level", "Senior Level"]

        country_config = self.countries[self.country]

        # Use the exact payload structure from the working scraper
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
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9,es;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Origin': 'https://hiring.cafe',
            'Referer': 'https://hiring.cafe/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            # User-Agent will be handled by middleware
        }

        return scrapy.Request(
            url=api_url,
            method='POST',
            body=json.dumps(payload),
            headers=headers,
            callback=self.parse_search_results,
            meta={'page': page, 'country': self.country},
            dont_filter=True
        )

    def start_requests(self):
        """Start requests for the spider - only generates first page."""
        self.logger.info(f"Starting HiringCafe spider for {self.country}")
        print(f"[DEBUG] Starting HiringCafe spider for {self.country}")
        print(f"[DEBUG] Generating ONLY first page request (sequential mode)")

        # Only yield the first page - subsequent pages will be generated in parse_search_results
        yield self.generate_page_request(1)
    
    def parse_search_results(self, response):
        """Parse search results from the API response."""
        current_page = response.meta['page']
        print(f"[DEBUG] parse_search_results called for page {current_page}")
        print(f"[DEBUG] Response status: {response.status}")
        print(f"[DEBUG] Response body length: {len(response.body)}")

        try:
            data = json.loads(response.text)
            results = data.get('results', [])

            print(f"[DEBUG] Parsed {len(results)} results from JSON")
            self.logger.info(f"Page {current_page}: Found {len(results)} jobs")

            if not results:
                self.logger.info("No more results, search complete!")
                return

            # Yield all jobs from current page
            for job in results:
                yield self.parse_job(job, response.meta['country'])

            # Generate next page request if we haven't reached max_pages
            if current_page < self.max_pages:
                next_page = current_page + 1
                delay_seconds = random.uniform(15, 18)
                self.logger.info(f"⏱️ Waiting {delay_seconds:.1f} seconds before requesting page {next_page}...")
                print(f"[DEBUG] Waiting {delay_seconds:.1f}s before page {next_page}")
                time.sleep(delay_seconds)

                print(f"[DEBUG] Generating request for page {next_page}")
                yield self.generate_page_request(next_page)
            else:
                self.logger.info(f"✅ Reached max_pages limit ({self.max_pages}). Stopping.")

        except json.JSONDecodeError as e:
            print(f"[DEBUG] JSON decode error: {e}")
            self.logger.error(f"Failed to parse JSON response: {e}")
        except Exception as e:
            print(f"[DEBUG] Exception in parse_search_results: {e}")
            self.logger.error(f"Error parsing search results: {e}")
    
    def parse_job(self, job_data: Dict[str, Any], country: str) -> JobItem:
        """Parse individual job posting."""
        print(f"[DEBUG] parse_job called for job {job_data.get('id', 'unknown')}")
        
        try:
            # Extract job information from the correct structure
            job_info = job_data.get('job_information', {})
            processed_data = job_data.get('v5_processed_job_data', {})
            
            # Extract basic information
            title = job_info.get('title', '')
            company = processed_data.get('company_name', '')
            description = job_info.get('description', '')
            requirements = processed_data.get('requirements_summary', '')
            
            print(f"[DEBUG] Extracted title: {title[:50]}...")
            print(f"[DEBUG] Extracted company: {company}")
            
            # Extract location information
            location_data = processed_data.get('formatted_workplace_location', '')
            location = location_data if location_data else f"{country}"
            
            # Extract workplace type
            workplace_type = processed_data.get('workplace_type', '')
            remote_type = self.map_workplace_type(workplace_type)
            
            # Extract salary information
            salary_raw = self.extract_salary_from_processed(job_data)
            
            # Extract contract type (default to full-time if not specified)
            contract_type = 'Full-time'
            
            # Extract posted date
            posted_date = job_info.get('posted_date') or job_info.get('created_at')
            if posted_date:
                try:
                    # Convert to ISO format if possible
                    posted_date = datetime.fromisoformat(posted_date.replace('Z', '+00:00')).date().isoformat()
                except:
                    posted_date = datetime.today().date().isoformat()
            else:
                posted_date = datetime.today().date().isoformat()
            
            # Create JobItem
            item = JobItem()
            item['portal'] = 'hiring_cafe'
            item['country'] = country
            item['url'] = job_info.get('apply_url', '') or job_info.get('url', '')
            item['title'] = title
            item['company'] = company
            item['location'] = location
            item['description'] = description
            item['requirements'] = requirements
            item['salary_raw'] = salary_raw
            item['contract_type'] = contract_type
            item['remote_type'] = remote_type
            item['posted_date'] = posted_date
            
            print(f"[DEBUG] Created JobItem successfully")
            return item
            
        except Exception as e:
            print(f"[DEBUG] Exception in parse_job: {e}")
            self.logger.error(f"Error parsing job: {e}")
            return None
    
    def map_workplace_type(self, workplace_type: str) -> str:
        """Map workplace type to standard values."""
        if not workplace_type:
            return "Not specified"
        
        workplace_type = workplace_type.strip().lower()
        
        workplace_map = {
            'remote': 'Remote',
            'work from home': 'Remote',
            'wfh': 'Remote',
            'hybrid': 'Hybrid',
            'hybrid remote': 'Hybrid',
            'onsite': 'Onsite',
            'on-site': 'Onsite',
            'in-office': 'Onsite',
            'office': 'Onsite'
        }
        
        return workplace_map.get(workplace_type, workplace_type.title())
    
    def extract_salary(self, job_data: Dict[str, Any]) -> str:
        """Extract salary information from job data."""
        compensation = job_data.get('compensation', {})
        
        if not compensation:
            return ""
        
        is_transparent = compensation.get('isTransparent', False)
        if not is_transparent:
            return "Not disclosed"
        
        yearly_min = compensation.get('yearlyMin')
        yearly_max = compensation.get('yearlyMax')
        currency = compensation.get('currency', 'USD')
        
        if yearly_min and yearly_max:
            return f"{yearly_min}-{yearly_max} {currency}/year"
        elif yearly_min:
            return f"{yearly_min}+ {currency}/year"
        elif yearly_max:
            return f"Up to {yearly_max} {currency}/year"
        else:
            return "Not disclosed"
    
    def extract_salary_from_processed(self, job_data: Dict[str, Any]) -> str:
        """Extract salary information from processed job data."""
        processed_data = job_data.get('v5_processed_job_data', {})
        
        is_transparent = processed_data.get('is_compensation_transparent', False)
        if not is_transparent:
            return "Not disclosed"
        
        yearly_min = processed_data.get('yearly_min_compensation')
        yearly_max = processed_data.get('yearly_max_compensation')
        currency = 'USD' if yearly_min else None
        
        if yearly_min and yearly_max:
            return f"{yearly_min}-{yearly_max} {currency}/year"
        elif yearly_min:
            return f"{yearly_min}+ {currency}/year"
        elif yearly_max:
            return f"Up to {yearly_max} {currency}/year"
        else:
            return "Not disclosed"
    
    def extract_compensation_data(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract compensation data structure."""
        processed_data = job_data.get('v5_processed_job_data', {})
        
        return {
            'is_transparent': processed_data.get('is_compensation_transparent', False),
            'yearly_min': processed_data.get('yearly_min_compensation'),
            'yearly_max': processed_data.get('yearly_max_compensation'),
            'currency': 'USD' if processed_data.get('yearly_min_compensation') else None
        }
    
    def extract_geolocation(self, job_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract geolocation data."""
        processed_data = job_data.get('v5_processed_job_data', {})
        location = processed_data.get('formatted_workplace_location', '')
        
        if not location:
            return []
        
        # Try to extract coordinates if available
        try:
            # This is a simplified extraction - in practice you might need more complex logic
            return [{
                'lat': 0.0,  # Default values
                'lon': 0.0
            }]
        except:
            return []
    
    def closed(self, reason):
        """Called when spider is closed."""
        self.logger.info(f"HiringCafe spider closed: {reason}")
        self.logger.info(f"Total pages processed: {self.current_page}")
