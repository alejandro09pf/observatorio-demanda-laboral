"""
Elempleo spider for Labor Market Observatory.
Scrapes job listings from https://www.elempleo.com/co using server-rendered HTML.
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

class ElempleoSpider(BaseSpider):
    """Spider for Elempleo job portal - Colombia jobs."""
    
    name = "elempleo"
    allowed_domains = ["elempleo.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "elempleo"
        
        # Force Colombia as Elempleo only works for Colombia
        self.country = "CO"
        
        # Start URLs for different cities and modalities
        self.start_urls = [
            "https://www.elempleo.com/co/ofertas-empleo/bogota",
            "https://www.elempleo.com/co/ofertas-empleo/medellin",
            "https://www.elempleo.com/co/ofertas-empleo/cali",
            "https://www.elempleo.com/co/ofertas-empleo/barranquilla",
            "https://www.elempleo.com/co/ofertas-empleo/remoto",
            "https://www.elempleo.com/co/ofertas-empleo/modalidad-remoto"
        ]
        
        # Track scraped URLs to avoid duplicates
        self.scraped_urls = set()
        
        # Statistics tracking
        self.stats = {
            'total_jobs_found': 0,
            'total_jobs_scraped': 0,
            'duplicates_skipped': 0,
            'pages_processed': 0,
            'errors': 0
        }
        
        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2.0,  # Respect rate limits
            'CONCURRENT_REQUESTS_PER_DOMAIN': 2,  # Conservative concurrency
            'ROBOTSTXT_OBEY': False,  # Disable robots.txt
            'AUTOTHROTTLE_ENABLED': True,  # Enable autothrottle
            'AUTOTHROTTLE_START_DELAY': 1,
            'AUTOTHROTTLE_MAX_DELAY': 10,
            'DOWNLOADER_MIDDLEWARES': {
                'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
            }
        })
    
    def start_requests(self):
        """Start requests with execution lock check and proxy support."""
        # Check execution lock BEFORE starting requests
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                f"This spider '{self.__class__.__name__}' can only be executed through the orchestrator.\n"
                f"Use: python -m src.orchestrator run-once {self.__class__.__name__.lower()} --country <COUNTRY>\n"
                f"Or: python -m src.orchestrator run {self.__class__.__name__.lower()} --country <COUNTRY>"
            )
        
        logger.info(f"Starting Elempleo spider for {self.country}")
        logger.info(f"Start URLs: {len(self.start_urls)} listing pages")
        
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_listing_page,
                meta={
                    'page': 1,
                    # 'proxy': self.get_proxy(),  # Temporarily disabled for testing
                    'dont_cache': True
                },
                headers=self.get_headers(),
                errback=self.handle_error
            )
    
    def get_proxy(self):
        """Get proxy from orchestrator's proxy service."""
        try:
            # This should call your orchestrator's proxy service
            # For now, we'll use the proxy middleware
            return None  # Let middleware handle proxy rotation
        except Exception as e:
            logger.warning(f"Could not get proxy: {e}")
            return None
    
    def get_headers(self):
        """Get headers with Colombian browser simulation."""
        return {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-CO,es;q=0.9,en;q=0.8',  # Colombian Spanish
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.elempleo.com/co/'
        }
    
    def parse_listing_page(self, response):
        """Parse job listing page to extract job links."""
        current_page = response.meta.get('page', 1)
        logger.info(f"Parsing listing page {current_page}: {response.url}")
        
        # Extract job links from the page
        job_links = response.css("a[href^='/co/ofertas-trabajo/']")
        logger.info(f"Found {len(job_links)} job links on page {current_page}")
        
        # Debug: Log first few job links to see their structure
        for i, link in enumerate(job_links[:3]):
            href = link.attrib.get('href', 'NO_HREF')
            text = link.css("::text").get() or 'NO_TEXT'
            logger.info(f"Job link {i+1}: href='{href}', text='{text[:50]}...'")
        
        if not job_links:
            logger.warning(f"No job links found on page {current_page}")
            return
        
        # Process each job link
        for job_link in job_links:
            try:
                # FIXED: Extract href attribute properly, not the entire element
                job_url = job_link.attrib.get('href')
                if not job_url:
                    continue
                
                # Build absolute URL
                absolute_url = urljoin(response.url, job_url)
                
                # Update statistics
                self.stats['total_jobs_found'] += 1
                
                # Skip if already scraped (DUPLICATE PREVENTION)
                if absolute_url in self.scraped_urls:
                    self.stats['duplicates_skipped'] += 1
                    logger.debug(f"⏭️ Skipping duplicate job: {absolute_url}")
                    continue
                
                # Mark as scraped to prevent future duplicates
                self.scraped_urls.add(absolute_url)
                logger.info(f"🔍 New job found: {absolute_url}")
                
                # Extract basic info from listing
                job_title = job_link.css("::text").get()
                
                # Follow to job detail page
                yield scrapy.Request(
                    url=absolute_url,
                    callback=self.parse_job_detail,
                    meta={
                        'proxy': self.get_proxy(),  # Re-enabled proxy support
                        'listing_title': job_title,
                        'source_page': response.url,
                        'is_new_job': True  # Flag to track new jobs
                    },
                    headers=self.get_headers(),
                    errback=self.handle_error
                )
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error processing job link: {e}")
                continue
        
        # Update page statistics
        self.stats['pages_processed'] += 1
        
        # Handle pagination
        if current_page < self.max_pages:
            next_page = current_page + 1
            next_url = self.get_next_page_url(response.url, next_page)
            
            if next_url:
                logger.info(f"📄 Following to page {next_page}: {next_url}")
                yield scrapy.Request(
                    url=next_url,
                    callback=self.parse_listing_page,
                    meta={
                        'page': next_page,
                        'proxy': self.get_proxy(),  # Re-enabled proxy support
                        'dont_cache': True
                    },
                    headers=self.get_headers(),
                    errback=self.handle_error
                )
        else:
            logger.info(f"🏁 Reached max pages limit ({self.max_pages})")
    
    def get_next_page_url(self, current_url: str, next_page: int) -> Optional[str]:
        """Generate next page URL based on current URL pattern."""
        # Try different pagination patterns
        pagination_patterns = [
            f"{current_url}?page={next_page}",
            f"{current_url}?pagina={next_page}",
            f"{current_url}?p={next_page}",
            f"{current_url}/page/{next_page}"
        ]
        
        # For now, return the first pattern
        # In a real implementation, you'd test which one works
        return pagination_patterns[0]
    
    def parse_job_detail(self, response):
        """Parse individual job detail page."""
        try:
            logger.info(f"Parsing job detail: {response.url}")
            
            # Create job item
            item = JobItem()
            item['portal'] = self.portal
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract job title - FIXED: Use correct Elempleo selectors
            title = response.css("h1.ee-offer-title .js-jobOffer-title::text, .js-jobOffer-title::text, h1.ee-offer-title::text").get()
            if not title:
                title = response.meta.get('listing_title', '')
            item['title'] = self.clean_text(title) if title else ""
            
            # Extract company name - FIXED: Use correct Elempleo selectors with nested text
            # Try different approaches for Scrapy CSS selectors
            company = ""
            
            # Method 1: Try to get text from spans
            company_spans = response.css(".js-company-name span, .joboffer-companyname span, .ee-company-title span")
            if company_spans:
                company_texts = [span.get() for span in company_spans if span.get()]
                company = " ".join(company_texts)
                logger.info(f"Company from spans: '{company}'")
            
            # Method 2: If no spans, try direct text
            if not company:
                company = response.css(".js-company-name::text, .joboffer-companyname::text").get()
                logger.info(f"Company from direct text: '{company}'")
            
            # Method 3: Try getting all text from company elements
            if not company:
                company_elements = response.css(".js-company-name, .joboffer-companyname")
                if company_elements:
                    company = company_elements[0].get()
                    logger.info(f"Company from element: '{company}'")
            
            # Clean company name by removing HTML tags and duplicates
            if company:
                # Remove HTML tags
                company = re.sub(r'<[^>]+>', '', company)
                # Remove extra whitespace
                company = re.sub(r'\s+', ' ', company).strip()
                # Remove duplicate company names (common in Elempleo)
                companies = company.split()
                unique_companies = []
                for comp in companies:
                    if comp not in unique_companies and len(comp) > 2:  # Filter out short words
                        unique_companies.append(comp)
                company = " ".join(unique_companies[:3])  # Take first 3 unique companies
            
            item['company'] = self.clean_text(company) if company else ""
            
            # Extract salary - Look for salary in JavaScript data first, then visible text
            salary = ""
            
            # Method 1: Look for salary in JavaScript data (most reliable)
            # Try to get all script content and search for salary
            script_contents = response.xpath("//script/text()").getall()
            salary = ""
            
            for script_content in script_contents:
                if script_content and 'salary' in script_content:
                    salary_match = re.search(r"salary:\s*['\"]([^'\"]+)['\"]", script_content)
                    if salary_match:
                        salary = salary_match.group(1)
                        logger.info(f"Salary from JavaScript: '{salary}'")
                        break
            
            # Method 2: Look for visible salary text
            if not salary:
                salary = response.xpath("//*[contains(., 'COP') or contains(., '$') or contains(., 'Salario confidencial')][1]//text()").get(default='').strip()
                if salary:
                    logger.info(f"Salary from visible text: '{salary}'")
            
            # Method 3: Fallback to CSS selectors
            if not salary:
                salary = response.css("[class*='salary']::text, [class*='salario']::text, .salary-info::text").get()
                if salary:
                    logger.info(f"Salary from CSS: '{salary}'")
            
            item['salary_raw'] = self.clean_text(salary) if salary else None
            
            # Extract location/city - Look for location in JavaScript data first, then visible text
            location = ""
            
            # Method 1: Look for location in JavaScript data (most reliable)
            # Try to get all script content and search for location
            script_contents = response.xpath("//script/text()").getall()
            location = ""
            
            for script_content in script_contents:
                if script_content and 'location' in script_content:
                    # Look for location in offerData or _objectDataJob
                    location_match = re.search(r"location:\s*['\"]([^'\"]+)['\"]", script_content)
                    if location_match:
                        location = location_match.group(1)
                        logger.info(f"Location from JavaScript: '{location}'")
                        break
                    else:
                        # Try alternative patterns
                        location_match = re.search(r"'location':\s*['\"]([^'\"]+)['\"]", script_content)
                        if location_match:
                            location = location_match.group(1)
                            logger.info(f"Location from JavaScript (alt): '{location}'")
                            break
            
            # Method 2: Look for "Ciudades de la oferta" section
            if not location:
                ciudades_h3 = response.xpath("//h3[contains(., 'Ciudades de la oferta')]")
                if ciudades_h3:
                    # Look for next sibling or nearby text
                    next_elem = ciudades_h3.xpath("following-sibling::*[1]//text()").get()
                    if next_elem:
                        location = next_elem.strip()
                        logger.info(f"Location from Ciudades section: '{location}'")
            
            # Method 3: Look for joboffer__city class
            if not location:
                location = response.xpath("//*[contains(@class, 'joboffer__city')]//text()").get(default='').strip()
                if location:
                    logger.info(f"Location from joboffer__city: '{location}'")
            
            # Method 4: Try to extract from title or URL (only if it looks like a city)
            if not location:
                title_text = item.get('title', '')
                if title_text and 'en' in title_text.lower():
                    # Extract city from title like "Asistente en Medellín"
                    parts = title_text.split('en')
                    if len(parts) > 1:
                        potential_city = parts[-1].strip()
                        # Only use if it looks like a city name (not too long, contains common city indicators)
                        if (len(potential_city) < 30 and 
                            any(city_indicator in potential_city.lower() for city_indicator in 
                                ['bogotá', 'medellín', 'cali', 'barranquilla', 'cartagena', 'bucaramanga', 'pereira', 'manizales', 'ibagué', 'villavicencio', 'neiva', 'popayán', 'montería', 'valledupar', 'tunja', 'florencia', 'mocoa', 'leticia', 'mitú', 'puerto carreño'])):
                            location = potential_city
                            logger.info(f"Location from title (city): '{location}'")
                        else:
                            logger.info(f"Location from title (not a city): '{potential_city}'")
            
            # Method 5: Fallback to CSS selectors
            if not location:
                location = response.css("[class*='location']::text, [class*='city']::text, .city-info::text").get()
                if location:
                    logger.info(f"Location from CSS: '{location}'")
            
            item['location'] = self.clean_text(location) if location else None
            
            # Extract posting date - Look for date information
            posted_date = response.css("[class*='date']::text, [class*='posted']::text, .posting-date::text").get()
            item['posted_date'] = self.parse_date(posted_date) if posted_date else datetime.today().date().isoformat()
            
            # Extract job description - Use XPath to find description under "Descripción general" heading
            description = ' '.join(t.strip() for t in response.xpath("//h2[contains(., 'Descripción general')]/following-sibling::*[self::p or self::div][1]//text()").getall())
            if not description:
                # Fallback: Try CSS selectors
                description = response.css(".js-description::text, .description-block p::text, .job-description::text").get()
            if not description:
                # Fallback: Try to get description from multiple elements with nested text
                desc_elements = response.css(".description-block p, .js-description, .job-content")
                description = " ".join([elem.get() for elem in desc_elements if elem.get()])
            if not description:
                # Fallback: Try alternative selectors for description
                description = response.css(".description-block p span::text, .js-description span::text").get()
            item['description'] = self.clean_text(description) if description else None
            
            # Extract requirements - Use XPath to find requirements under "Requisitos" heading
            requirements = ' '.join(t.strip() for t in response.xpath("//h2[contains(., 'Requisitos')]/following-sibling::*[self::p or self::ul][1]//text()").getall())
            if not requirements:
                # Fallback: Look for requirements-related CSS classes
                requirements = response.css("[class*='requirements']::text, [class*='requisitos']::text, .job-requirements::text").get()
            item['requirements'] = self.clean_text(requirements) if requirements else None
            
            # Extract contract type - Look for contract in JavaScript data first, then visible text
            contract_type = ""
            
            # Method 1: Look for contract in JavaScript data (most reliable)
            # Try to get all script content and search for contract
            script_contents = response.xpath("//script/text()").getall()
            contract_type = ""
            
            for script_content in script_contents:
                if script_content and 'contract' in script_content:
                    contract_match = re.search(r"contract:\s*['\"]([^'\"]+)['\"]", script_content)
                    if contract_match:
                        contract_type = contract_match.group(1)
                        logger.info(f"Contract from JavaScript: '{contract_type}'")
                        break
            
            # Method 2: Look for contract in "Datos complementarios" section
            if not contract_type:
                contract_type = response.xpath("//h2[contains(., 'Datos complementarios')]/following::*[contains(., 'Contrato')][1]//text()").get(default='').strip()
                if contract_type:
                    logger.info(f"Contract from Datos complementarios: '{contract_type}'")
            
            # Method 3: Fallback to CSS selectors
            if not contract_type:
                contract_type = response.css("[class*='contract']::text, [class*='contrato']::text, .contract-type::text").get()
                if contract_type:
                    logger.info(f"Contract from CSS: '{contract_type}'")
            
            item['contract_type'] = self.clean_text(contract_type) if contract_type else None
            
            # Extract remote type (modality) - Look for remote/hybrid/presential in JavaScript data first, then visible text
            remote_type = ""
            
            # Method 1: Look for remote type in JavaScript data (most reliable)
            # Try to get all script content and search for location to extract remote type
            script_contents = response.xpath("//script/text()").getall()
            remote_type = ""
            
            for script_content in script_contents:
                if script_content and 'location' in script_content:
                    # Look for hybrid/remote/presential in location field
                    location_match = re.search(r"location:\s*['\"]([^'\"]+)['\"]", script_content)
                    if location_match:
                        location_text = location_match.group(1)
                        if 'Hibrido' in location_text or 'Híbrido' in location_text:
                            remote_type = "Híbrido"
                            logger.info(f"Remote type from JavaScript location (Híbrido): '{remote_type}'")
                            break
                        elif 'Remoto' in location_text:
                            remote_type = "Remoto"
                            logger.info(f"Remote type from JavaScript location (Remoto): '{remote_type}'")
                            break
                        elif 'Presencial' in location_text:
                            remote_type = "Presencial"
                            logger.info(f"Remote type from JavaScript location (Presencial): '{remote_type}'")
                            break
            
            # Method 2: Look for visible remote type tags
            if not remote_type:
                remote_type = response.xpath("//*[contains(., 'Remoto') or contains(., 'Híbrido') or contains(., 'Presencial')][1]//text()").get(default='').strip()
                if remote_type:
                    logger.info(f"Remote type from visible text: '{remote_type}'")
            
            # Method 3: Fallback to CSS selectors
            if not remote_type:
                remote_type = response.css("[class*='modality']::text, [class*='modalidad']::text, .remote-type::text").get()
                if remote_type:
                    logger.info(f"Remote type from CSS: '{remote_type}'")
            
            item['remote_type'] = self.clean_text(remote_type) if remote_type else None
            
            # Debug: Log what was extracted
            logger.info(f"Extracted data for {response.url}:")
            logger.info(f"  Title: '{item.get('title', 'NO_TITLE')}'")
            logger.info(f"  Company: '{item.get('company', 'NO_COMPANY')}'")
            logger.info(f"  Location: '{item.get('location', 'NO_LOCATION')}'")
            logger.info(f"  Salary: '{item.get('salary_raw', 'NO_SALARY')}'")
            logger.info(f"  Description length: {len(item.get('description', '') or '')}")
            logger.info(f"  Requirements length: {len(item.get('requirements', '') or '')}")
            logger.info(f"  Contract Type: '{item.get('contract_type', 'NO_CONTRACT')}'")
            logger.info(f"  Remote Type: '{item.get('remote_type', 'NO_REMOTE')}'")
            
            # Validate and yield item
            if self.validate_job_item(item):
                # Update statistics for successful scraping
                self.stats['total_jobs_scraped'] += 1
                
                # Check if this is a new job (not a duplicate)
                is_new_job = response.meta.get('is_new_job', False)
                if is_new_job:
                    logger.info(f"✅ Successfully scraped NEW job: {item['title'][:50]}...")
                else:
                    logger.info(f"✅ Successfully scraped job: {item['title'][:50]}...")
                
                yield item
            else:
                logger.warning(f"❌ Invalid job item - missing fields:")
                for field in ['title', 'company', 'portal', 'country']:
                    if not item.get(field):
                        logger.warning(f"    Missing: {field}")
                
        except Exception as e:
            self.stats['errors'] += 1
            logger.error(f"Error parsing job detail {response.url}: {e}")
    
    def parse_date(self, date_string: str) -> str:
        """Parse Elempleo date format."""
        if not date_string:
            return datetime.today().date().isoformat()
        
        try:
            # Common Spanish date patterns
            date_patterns = [
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'(\d{1,2}) de (\w+) de (\d{4})',  # "23 de Agosto de 2025"
            ]
            
            # Spanish month mappings
            month_map = {
                'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04',
                'may': '05', 'jun': '06', 'jul': '07', 'ago': '08',
                'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12',
                'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04',
                'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08',
                'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'
            }
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'hace' in pattern:
                        # Handle relative dates
                        return datetime.today().date().isoformat()
                    elif len(match.groups()) == 3:
                        # Handle absolute dates
                        if pattern == r'(\d{1,2}) de (\w+) de (\d{4})':
                            day, month, year = match.groups()
                        else:
                            day, month, year = match.groups()
                        
                        # Convert month name to number
                        month_lower = month.lower()[:3]
                        if month_lower in month_map:
                            month_num = month_map[month_lower]
                            return f"{year}-{month_num}-{day.zfill(2)}"
            
            # If no pattern matches, return today's date
            return datetime.today().date().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return datetime.today().date().isoformat()
    
    def handle_error(self, failure):
        """Handle request errors and retry with different proxy if needed."""
        request = failure.request
        response = failure.value
        
        if hasattr(response, 'status'):
            if response.status in [429, 403]:  # Rate limited or forbidden
                logger.warning(f"Request failed with status {response.status}, retrying with new proxy")
                
                # Retry with new proxy
                yield scrapy.Request(
                    url=request.url,
                    callback=request.callback,
                    meta={
                        **request.meta,
                        'proxy': self.get_proxy(),
                        'dont_cache': True
                    },
                    headers=request.headers,
                    errback=self.handle_error
                )
            else:
                logger.error(f"Request failed: {response.status} - {request.url}")
        else:
            logger.error(f"Request failed: {failure.value} - {request.url}")
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        cleaned = re.sub(r'\s+', ' ', text.strip())
        return cleaned
    
    def validate_job_item(self, item: JobItem) -> bool:
        """Validate job item has required fields."""
        required_fields = ['title', 'company', 'portal', 'country']
        for field in required_fields:
            if not item.get(field):
                logger.warning(f"Missing required field: {field}")
                return False
        return True
    
    def closed(self, reason):
        """Called when spider is closed - log final statistics."""
        logger.info("=" * 60)
        logger.info("🏁 ELEMPLEO SPIDER FINAL STATISTICS")
        logger.info("=" * 60)
        logger.info(f"📊 Total jobs found: {self.stats['total_jobs_found']}")
        logger.info(f"✅ Total jobs scraped: {self.stats['total_jobs_scraped']}")
        logger.info(f"⏭️ Duplicates skipped: {self.stats['duplicates_skipped']}")
        logger.info(f"📄 Pages processed: {self.stats['pages_processed']}")
        logger.info(f"❌ Errors encountered: {self.stats['errors']}")
        logger.info(f"🔗 Unique URLs tracked: {len(self.scraped_urls)}")
        logger.info("=" * 60)
        
        # Calculate efficiency metrics
        if self.stats['total_jobs_found'] > 0:
            duplicate_rate = (self.stats['duplicates_skipped'] / self.stats['total_jobs_found']) * 100
            success_rate = (self.stats['total_jobs_scraped'] / self.stats['total_jobs_found']) * 100
            logger.info(f"📈 Duplicate rate: {duplicate_rate:.1f}%")
            logger.info(f"📈 Success rate: {success_rate:.1f}%")
        
        logger.info("=" * 60)
