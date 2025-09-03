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
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'RANDOMIZE_DOWNLOAD_DELAY': True,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 2,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 2,
        'AUTOTHROTTLE_MAX_DELAY': 5,
        'AUTOTHROTTLE_TARGET_CONCURRENCY': 0.5,
        'ROBOTSTXT_OBEY': False,
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
    
    def start_requests(self):
        """Start requests for the spider."""
        self.logger.info(f"Starting HiringCafe spider for {self.country}")
        print(f"[DEBUG] Starting HiringCafe spider for {self.country}")
        
        # API endpoint
        api_url = 'https://hiring.cafe/api/search-jobs'
        
        # Default parameters
        workplace_types = ["Remote", "Hybrid", "Onsite"]
        seniority_levels = ["No Prior Experience Required", "Entry Level", "Mid Level", "Senior Level"]
        
        country_config = self.countries[self.country]
        print(f"[DEBUG] Country config: {country_config}")
        
        for page in range(1, self.max_pages + 1):
            print(f"[DEBUG] Creating request for page {page}")
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
                # User-Agent will be handled by middleware
            }
            
            yield scrapy.Request(
                url=api_url,
                method='POST',
                body=json.dumps(payload),
                headers=headers,
                callback=self.parse_search_results,
                meta={'page': page, 'country': self.country},
                dont_filter=True
            )
            
            # Note: Scrapy handles delays through DOWNLOAD_DELAY setting
    
    def parse_search_results(self, response):
        """Parse search results from the API response."""
        print(f"[DEBUG] parse_search_results called for page {response.meta['page']}")
        print(f"[DEBUG] Response status: {response.status}")
        print(f"[DEBUG] Response body length: {len(response.body)}")
        
        try:
            data = json.loads(response.text)
            results = data.get('results', [])
            
            print(f"[DEBUG] Parsed {len(results)} results from JSON")
            self.logger.info(f"Page {response.meta['page']}: Found {len(results)} jobs")
            
            if not results:
                self.logger.info("No more results, search complete!")
                return
            
            for job in results:
                yield self.parse_job(job, response.meta['country'])
                
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
            requirements = ""  # Will be extracted from description
            
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
            
            # Add additional fields for hiring.cafe specific data
            item['job_id'] = job_data.get('id', '')
            item['job_category'] = processed_data.get('job_category', '')
            item['role_activities'] = []  # Will be extracted from description
            item['compensation'] = self.extract_compensation_data(job_data)
            item['geolocation'] = self.extract_geolocation(job_data)
            item['source_country'] = country.lower()
            item['scraped_at'] = datetime.now().isoformat()
            
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
