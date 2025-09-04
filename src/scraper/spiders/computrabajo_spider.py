"""
Computrabajo spider for Labor Market Observatory.
Scrapes job postings from co.computrabajo.com using static listing pages
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ComputrabajoSpider(BaseSpider):
    """Spider for Computrabajo Colombia using static listing pages."""
    
    name = "computrabajo"
    allowed_domains = ["co.computrabajo.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "computrabajo"
        
        # Get keyword and city parameters
        self.keyword = kwargs.get('keyword', 'sistemas')
        
        # Set country-specific city defaults
        if self.country == "CO":
            self.city = kwargs.get('city', 'bogota-dc')
        elif self.country == "MX":
            self.city = kwargs.get('city', 'distrito-federal')
        elif self.country == "AR":
            self.city = kwargs.get('city', 'capital-federal')
        else:
            # Default to Colombia
            self.city = kwargs.get('city', 'bogota-dc')
        
        # Build start URL using SEO-friendly format
        if self.country == "CO":
            self.start_url = f"https://co.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        elif self.country == "MX":
            self.start_url = f"https://mx.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        elif self.country == "AR":
            self.start_url = f"https://ar.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        else:
            # Default to Colombia
            self.start_url = f"https://co.computrabajo.com/trabajo-de-{self.keyword}-en-{self.city}"
        
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
            'DOWNLOAD_DELAY': 1.5,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
            'ROBOTSTXT_OBEY': False,  # Disable robots.txt for anti-bot protection
            'DOWNLOADER_MIDDLEWARES': {
                'scrapy.downloadermiddlewares.robotstxt.RobotsTxtMiddleware': None,
            }
        })
    
    def start_requests(self):
        """Start with the first page."""
        # Check execution lock BEFORE starting requests
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                f"This spider '{self.__class__.__name__}' can only be executed through the orchestrator.\n"
                f"Use: python -m src.orchestrator run-once {self.__class__.__name__.lower()} --country <COUNTRY>\n"
                f"Or: python -m src.orchestrator run {self.__class__.__name__.lower()} --country <COUNTRY>"
            )
        
        logger.info(f"Starting Computrabajo spider for {self.country}")
        logger.info(f"Start URL: {self.start_url}")
        
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_search_results,
            meta={
                'page': 1,
                # 'proxy': self.get_proxy(),  # Temporarily disabled for testing
                'dont_cache': True
            },
            headers=self.get_headers(),
            errback=self.handle_error
        )
    
    def get_headers(self):
        """Get headers to avoid anti-bot detection."""
        return {
            # User agent will be handled by middleware - no hardcoded UA
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }
    
    def get_proxy(self):
        """Get proxy from orchestrator's proxy service."""
        try:
            # This should call your orchestrator's proxy service
            # For now, we'll use the proxy middleware
            return None  # Let middleware handle proxy rotation
        except Exception as e:
            logger.warning(f"Could not get proxy: {e}")
            return None
    
    def parse_search_results(self, response):
        """Parse search results page."""
        logger.info(f"Parsing search results: {response.url}")
        
        # Extract job listings using structural selectors
        job_cards = response.css("article")
        
        if not job_cards:
            logger.warning("No job cards found on page")
            return
        
        logger.info(f"Found {len(job_cards)} job cards")
        
        for i, job_card in enumerate(job_cards):
            try:
                # Extract job URL from article h2 a
                job_url = job_card.css("h2 a::attr(href)").get()
                if not job_url:
                    continue
                
                job_url = self.build_absolute_url(job_url, response.url)
                
                # Update statistics
                self.stats['total_jobs_found'] += 1
                
                # Skip if already scraped (DUPLICATE PREVENTION)
                if job_url in self.scraped_urls:
                    self.stats['duplicates_skipped'] += 1
                    logger.debug(f"⏭️ Skipping duplicate job: {job_url}")
                    continue
                
                # Mark as scraped to prevent future duplicates
                self.scraped_urls.add(job_url)
                logger.info(f"🔍 New job found: {job_url}")
                
                # Extract basic info from listing for fallback
                title = job_card.css("h2 a::text").get()
                # Company is actually in the first paragraph (location field)
                company = job_card.css("p:nth-of-type(1)::text").get()
                # Location is actually in the second paragraph (salary field)
                location = job_card.css("p:nth-of-type(2)::text").get()
                # Salary might be in a different field or not available
                salary_raw = job_card.css("p:nth-of-type(3)::text").get()
                posted_date = job_card.css("p:last-of-type::text").get()
                
                # Follow job detail page
                yield scrapy.Request(
                    url=job_url,
                    callback=self.parse_job,
                    meta={
                        # 'proxy': self.get_proxy(),  # Temporarily disabled for testing
                        'job_card': job_card,
                        'listing_title': title,
                        'listing_company': company,
                        'listing_location': location,
                        'listing_salary': salary_raw,
                        'listing_date': posted_date,
                        'is_new_job': True  # Flag to track new jobs
                    },
                    headers=self.get_headers(),
                    errback=self.handle_error
                )
                
                # Log progress
                self.log_progress(i + 1, len(job_cards))
                
            except Exception as e:
                self.stats['errors'] += 1
                logger.error(f"Error processing job card {i}: {e}")
                continue
        
        # Update page statistics
        self.stats['pages_processed'] += 1
        
        # Handle pagination - go up to 5 pages
        current_page = response.meta.get('page', 1)
        if current_page < 5:
            next_page = current_page + 1
            next_url = f"{self.start_url}?p={next_page}"
            
            logger.info(f"Following pagination to page {next_page}: {next_url}")
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={
                    'page': next_page,
                    # 'proxy': self.get_proxy(),  # Temporarily disabled for testing
                    'dont_cache': True
                },
                headers=self.get_headers(),
                errback=self.handle_error
            )
    
    def parse_job(self, response):
        """Parse individual job posting with comprehensive field extraction."""
        try:
            logger.info(f"Parsing job: {response.url}")
            
            # Create job item
            item = JobItem()
            
            # Basic information
            item['portal'] = 'computrabajo'
            item['country'] = self.country
            item['url'] = response.url
            
            # Parse JSON-LD structured data first
            json_ld_data = self.parse_json_ld(response)
            
            # Extract title from JSON-LD or fallback to HTML
            title = json_ld_data.get('title') or response.css("h1::text").get()
            if not title:
                title = response.meta.get('listing_title', '')
            item['title'] = self.clean_text(title) if title else ""
            logger.info(f"📝 Title extracted: {item['title'][:50]}...")
            
            # Extract company from JSON-LD or fallback to HTML
            company = json_ld_data.get('company') or self.extract_company_from_html(response)
            if not company:
                company = response.meta.get('listing_company', '')
            item['company'] = self.clean_text(company) if company else ""
            logger.info(f"🏢 Company extracted: {item['company'][:30]}...")
            
            # Extract location from JSON-LD or fallback to HTML
            location = json_ld_data.get('location') or self.extract_location_from_html(response)
            if not location:
                location = response.meta.get('listing_location', '')
            item['location'] = self.clean_text(location) if location else ""
            logger.info(f"📍 Location extracted: {item['location']}")
            
            # Extract description and requirements from the current HTML structure
            description_html = response.xpath("//h3[contains(text(), 'Descripción de la oferta')]/following-sibling::p[1]").get()
            if description_html:
                # Clean the description HTML
                item['description'] = self.clean_html_tags(description_html)
                logger.info(f"📄 Description extracted: {len(item['description'])} characters")
                
                # Extract salary from description
                salary_raw = self.extract_salary_from_description(item['description'])
                if salary_raw:
                    item['salary_raw'] = salary_raw
                else:
                    # Don't use listing_salary if it contains date information
                    listing_salary = response.meta.get('listing_salary', '')
                    if listing_salary and not any(word in listing_salary.lower() for word in ['hace', 'días', 'horas', 'semanas']):
                        item['salary_raw'] = listing_salary
                    else:
                        item['salary_raw'] = ""
                logger.info(f"💰 Salary extracted: {item['salary_raw']}")
            else:
                item['description'] = ""
                item['salary_raw'] = response.meta.get('listing_salary', '')
                logger.info(f"📄 Description extracted: 0 characters")
                logger.info(f"💰 Salary extracted: {item['salary_raw']}")
            
            # Extract requirements from the requirements section or from description text
            requirements_html = response.xpath("//h3[contains(text(), 'Requerimientos')]/following-sibling::ul[1]").get()
            if requirements_html:
                req_items = response.xpath("//h3[contains(text(), 'Requerimientos')]/following-sibling::ul[1]/li//text()").getall()
                if req_items:
                    requirements = '; '.join([item.strip() for item in req_items if item.strip()])
                    item['requirements'] = requirements
                    logger.info(f"📋 Requirements extracted from HTML: {len(item['requirements'])} characters")
                else:
                    item['requirements'] = ""
                    logger.info(f"📋 Requirements extracted from HTML: 0 characters")
            else:
                # Try to extract requirements from description text
                if item['description']:
                    requirements = self.extract_requirements_from_text(item['description'])
                    item['requirements'] = requirements
                    logger.info(f"📋 Requirements extracted from text: {len(item['requirements'])} characters")
                else:
                    item['requirements'] = ""
                    logger.info(f"📋 Requirements extracted: 0 characters")
            

            
            # Extract contract type from JSON-LD or HTML
            contract_type = json_ld_data.get('contract_type') or self.extract_contract_from_html(response)
            if not contract_type:
                contract_type = self.extract_contract_from_text(item['salary_raw'] + " " + item['description'])
            item['contract_type'] = contract_type
            logger.info(f"📋 Contract type extracted: {item['contract_type']}")
            
            # Extract remote type from HTML
            remote_type = self.extract_remote_from_html(response)
            if not remote_type:
                remote_type = self.extract_remote_from_text(item['salary_raw'] + " " + item['description'])
            item['remote_type'] = remote_type
            logger.info(f"🏠 Remote type extracted: {item['remote_type']}")
            
            # Extract posted date from JSON-LD or HTML
            posted_date = json_ld_data.get('posted_date') or self.extract_posted_date_from_html(response)
            if not posted_date:
                posted_date = response.meta.get('listing_date', '')
            item['posted_date'] = self.parse_date(posted_date) if posted_date else None
            logger.info(f"📅 Posted date extracted: {item['posted_date']}")
            
            # Validate item
            if not self.validate_job_item(item):
                logger.warning(f"Invalid job item: {item.get('title', 'No title')}")
                return
            
            # Update statistics for successful scraping
            self.stats['total_jobs_scraped'] += 1
            
            # Check if this is a new job (not a duplicate)
            is_new_job = response.meta.get('is_new_job', False)
            if is_new_job:
                logger.info(f"✅ Successfully scraped NEW job: {item['title'][:50]}...")
            else:
                logger.info(f"✅ Successfully scraped job: {item['title'][:50]}...")
            
            yield item
            
        except Exception as e:
            logger.error(f"Error parsing job {response.url}: {e}")
            return
    
    def parse_json_ld(self, response):
        """Parse JSON-LD structured data from the page."""
        try:
            import json
            
            # Find all script tags with application/ld+json
            script_tags = response.xpath("//script[@type='application/ld+json']/text()").getall()
            
            for script_content in script_tags:
                try:
                    data = json.loads(script_content)
                    
                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        for item in data:
                            if self.is_job_posting(item):
                                return self.extract_job_posting_data(item)
                    elif self.is_job_posting(data):
                        return self.extract_job_posting_data(data)
                        
                except json.JSONDecodeError:
                    continue
            
            logger.debug("No valid JSON-LD JobPosting found")
            return {}
            
        except Exception as e:
            logger.warning(f"Error parsing JSON-LD: {e}")
            return {}
    
    def is_job_posting(self, data):
        """Check if the JSON-LD object is a JobPosting."""
        return isinstance(data, dict) and data.get('@type') == 'JobPosting'
    
    def extract_job_posting_data(self, job_data):
        """Extract relevant fields from JobPosting JSON-LD."""
        try:
            result = {}
            
            # Title
            result['title'] = job_data.get('title', '')
            
            # Company name
            hiring_org = job_data.get('hiringOrganization', {})
            if isinstance(hiring_org, dict):
                result['company'] = hiring_org.get('name', '')
            else:
                result['company'] = str(hiring_org) if hiring_org else ''
            
            # Location
            job_location = job_data.get('jobLocation', {})
            if isinstance(job_location, dict):
                address = job_location.get('address', {})
                if isinstance(address, dict):
                    locality = address.get('addressLocality', '')
                    region = address.get('addressRegion', '')
                    if locality and region:
                        result['location'] = f"{locality}, {region}"
                    elif locality:
                        result['location'] = locality
                    else:
                        result['location'] = ''
                else:
                    result['location'] = str(job_location) if job_location else ''
            else:
                result['location'] = str(job_location) if job_location else ''
            
            # Description and requirements
            description = job_data.get('description', '')
            if description and '-Requerimientos-' in description:
                parts = description.split('-Requerimientos-')
                result['description'] = parts[0].strip()
                result['requirements'] = parts[1].strip() if len(parts) > 1 else ''
            else:
                result['description'] = description
                result['requirements'] = ''
            
            # Salary
            base_salary = job_data.get('baseSalary', {})
            if isinstance(base_salary, dict):
                value = base_salary.get('value', {})
                if isinstance(value, dict):
                    salary_value = value.get('value', '')
                    currency = value.get('currency', 'COP')
                    unit = base_salary.get('unitText', 'Mensual')
                    if salary_value:
                        result['salary_raw'] = f"$ {salary_value} {currency} ({unit})"
                    else:
                        result['salary_raw'] = ''
                else:
                    result['salary_raw'] = str(value) if value else ''
            else:
                result['salary_raw'] = str(base_salary) if base_salary else ''
            
            # Contract type
            employment_type = job_data.get('employmentType', '')
            if employment_type:
                result['contract_type'] = self.map_employment_type(employment_type)
            else:
                result['contract_type'] = ''
            
            # Posted date
            date_posted = job_data.get('datePosted', '')
            if date_posted:
                result['posted_date'] = self.parse_iso_date(date_posted)
            else:
                result['posted_date'] = ''
            
            logger.info(f"✅ JSON-LD data extracted: {len(result)} fields")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting JobPosting data: {e}")
            return {}
    
    def map_employment_type(self, employment_type):
        """Map employment type to human-friendly contract type."""
        mapping = {
            'FULL_TIME': 'Tiempo completo',
            'PART_TIME': 'Medio tiempo',
            'CONTRACTOR': 'Contratista',
            'TEMPORARY': 'Temporal',
            'INTERN': 'Pasante',
            'VOLUNTEER': 'Voluntario',
            'PER_DIEM': 'Por día',
            'OTHER': 'Otro'
        }
        return mapping.get(employment_type, employment_type)
    
    def parse_iso_date(self, date_string):
        """Parse ISO date string to our format."""
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            return dt.date().isoformat()
        except Exception as e:
            logger.warning(f"Could not parse ISO date '{date_string}': {e}")
            return date_string
    
    def extract_company_from_html(self, response):
        """Extract company name from HTML fallback."""
        # Try h1 + p (split on "–")
        company_line = response.css("h1 + p::text").get()
        if company_line:
            parts = company_line.split('–')
            if len(parts) >= 2:
                return parts[0].strip()
            else:
                return company_line.strip()
        
        # Try alternative selectors
        selectors = [
            ".company::text",
            ".employer::text",
            "[class*='company']::text",
            "[class*='employer']::text"
        ]
        
        for selector in selectors:
            company = response.css(selector).get()
            if company:
                return company.strip()
        
        return ""
    
    def extract_location_from_html(self, response):
        """Extract location from HTML fallback."""
        # Try h1 + p (split on "–")
        company_line = response.css("h1 + p::text").get()
        if company_line:
            parts = company_line.split('–')
            if len(parts) >= 2:
                location = parts[1].strip()
                # Filter out location permission messages
                if 'autorizaci' not in location.lower() and 'configuraci' not in location.lower():
                    return location
        
        # Try to extract from the job title or company info
        title = response.css("h1::text").get()
        if title:
            # Look for city names in the title
            city_indicators = ['Bogotá', 'Medellín', 'Cali', 'Barranquilla', 'Cartagena', 'Bucaramanga', 'Fontibón', 'Montevideo']
            for city in city_indicators:
                if city in title:
                    return city
        
        # Try to extract from the URL path
        url = response.url
        if 'bogota' in url.lower():
            return 'Bogotá'
        elif 'medellin' in url.lower():
            return 'Medellín'
        elif 'cali' in url.lower():
            return 'Cali'
        elif 'barranquilla' in url.lower():
            return 'Barranquilla'
        elif 'cartagena' in url.lower():
            return 'Cartagena'
        elif 'bucaramanga' in url.lower():
            return 'Bucaramanga'
        
        # Try alternative selectors
        selectors = [
            ".location::text",
            ".city::text",
            "[class*='location']::text",
            "[class*='city']::text"
        ]
        
        for selector in selectors:
            location = response.css(selector).get()
            if location:
                location = location.strip()
                # Filter out location permission messages
                if 'autorizaci' not in location.lower() and 'configuraci' not in location.lower():
                    return location
        
        return ""
    
    def extract_description_and_requirements(self, response):
        """Extract description and requirements from the main content."""
        try:
            # Find the main description section
            desc_section = response.xpath("//h3[contains(text(), 'Descripción de la oferta')]")
            if not desc_section:
                # Try alternative selectors
                desc_section = response.xpath("//h3[contains(text(), 'Descripción')]")
            
            if desc_section:
                # Get all content between description heading and requirements heading
                desc_content = []
                req_content = []
                
                # Get the description heading element
                desc_heading = desc_section[0]
                
                # Get all following siblings until we hit requirements or another heading
                current_element = desc_heading.getnext()
                in_description = True
                
                while current_element is not None:
                    tag = current_element.tag
                    
                    # Stop if we hit another h3 heading
                    if tag == 'h3':
                        break
                    
                    # Check if this is the requirements section
                    if tag in ['p', 'div'] and 'Requerimientos' in current_element.text_content():
                        in_description = False
                        current_element = current_element.getnext()
                        continue
                    
                    # Collect content based on current section
                    if in_description:
                        if tag == 'p':
                            text = current_element.text_content().strip()
                            if text and not text.startswith('Palabras clave:'):
                                desc_content.append(text)
                    else:
                        # We're in requirements section
                        if tag == 'ul':
                            # Get list items
                            li_elements = current_element.xpath('.//li//text()')
                            for li_text in li_elements:
                                text = li_text.strip()
                                if text:
                                    req_content.append(text)
                        elif tag == 'p':
                            text = current_element.text_content().strip()
                            if text and not text.startswith('Palabras clave:'):
                                req_content.append(text)
                    
                    current_element = current_element.getnext()
                
                # Join the content
                description = ' '.join(desc_content) if desc_content else ""
                requirements = '; '.join(req_content) if req_content else ""
                
                logger.info(f"📄 Raw description length: {len(description)}")
                logger.info(f"📋 Raw requirements length: {len(requirements)}")
                
                return description, requirements
            
            # Fallback: try to get the entire content and split manually
            full_content = response.xpath("//div[contains(@class, 'content') or contains(@class, 'description')]//text()").getall()
            if full_content:
                full_text = ' '.join([text.strip() for text in full_content if text.strip()])
                
                # Try to split on common patterns
                if '-Requerimientos-' in full_text:
                    parts = full_text.split('-Requerimientos-')
                    description = parts[0].strip()
                    requirements = parts[1].strip() if len(parts) > 1 else ""
                elif 'Requerimientos' in full_text:
                    parts = full_text.split('Requerimientos')
                    description = parts[0].strip()
                    requirements = parts[1].strip() if len(parts) > 1 else ""
                else:
                    description = full_text
                    requirements = ""
                
                return description, requirements
            
            return "", ""
            
        except Exception as e:
            logger.error(f"Error extracting description and requirements: {e}")
            return "", ""
    
    def extract_requirements_from_text(self, description_text):
        """Extract requirements from description text."""
        if not description_text:
            return ""
        
        import re
        
        # Look for common requirement patterns in the text
        requirement_patterns = [
            r'Se requiere[^.]*(?:\.|$)',
            r'Requisitos[^.]*(?:\.|$)',
            r'Experiencia[^.]*(?:\.|$)',
            r'Educación[^.]*(?:\.|$)',
            r'Formación[^.]*(?:\.|$)',
            r'Conocimientos[^.]*(?:\.|$)',
            r'Habilidades[^.]*(?:\.|$)',
            r'Competencias[^.]*(?:\.|$)',
            r'Certificaciones[^.]*(?:\.|$)',
            r'Licencia[^.]*(?:\.|$)',
            r'Edad[^.]*(?:\.|$)',
            r'Género[^.]*(?:\.|$)',
            r'Disponibilidad[^.]*(?:\.|$)',
            r'Horario[^.]*(?:\.|$)',
            r'Modalidad[^.]*(?:\.|$)'
        ]
        
        requirements = []
        for pattern in requirement_patterns:
            matches = re.findall(pattern, description_text, re.IGNORECASE)
            for match in matches:
                if match.strip() and len(match.strip()) > 10:  # Filter out very short matches
                    requirements.append(match.strip())
        
        # Also look for specific phrases that indicate requirements
        requirement_phrases = [
            'mínimo de', 'mínima de', 'al menos', 'por lo menos',
            'preferiblemente', 'deseable', 'opcional', 'obligatorio',
            'indispensable', 'necesario', 'requerido', 'exigido'
        ]
        
        sentences = re.split(r'[.!?]', description_text)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(phrase in sentence.lower() for phrase in requirement_phrases):
                if sentence and len(sentence) > 10:
                    requirements.append(sentence)
        
        # Remove duplicates and join
        unique_requirements = list(set(requirements))
        if unique_requirements:
            return '; '.join(unique_requirements)
        
        return ""
    
    def extract_requirements_from_html(self, response):
        """Extract requirements from HTML fallback."""
        # Try the structured requirements section
        req_section = response.xpath("//h3[contains(text(), 'Requerimientos')]")
        if req_section:
            req_items = req_section.xpath("following-sibling::ul[1]/li//text()").getall()
            if req_items:
                requirements = '; '.join([item.strip() for item in req_items if item.strip()])
                if requirements:
                    return requirements
        
        # Try alternative selectors
        selectors = [
            ".requirements::text",
            ".skills::text",
            ".profile::text",
            "div[class*='requirements']::text"
        ]
        
        for selector in selectors:
            text = response.css(selector).get()
            if text:
                return text.strip()
        
        return ""
    
    def extract_contract_from_html(self, response):
        """Extract contract type from HTML tags."""
        # Look for contract tags in the offer section
        contract_selectors = [
            "//section[contains(@class, 'offer')]//p[@class='fs16 fc_aux']/span[contains(text(), 'Contrato')]/text()",
            "//span[contains(text(), 'Contrato')]/text()",
            "//*[contains(text(), 'Contrato de')]/text()",
            "//*[contains(text(), 'Tiempo')]/text()"
        ]
        
        for selector in contract_selectors:
            contract = response.xpath(selector).get()
            if contract:
                return contract.strip()
        
        return ""
    
    def extract_remote_from_html(self, response):
        """Extract remote type from HTML."""
        remote_selectors = [
            "//*[contains(text(), 'Remoto') or contains(text(), 'Híbrido') or contains(text(), 'Presencial')][1]/text()",
            "//span[contains(text(), 'Remoto')]/text()",
            "//span[contains(text(), 'Híbrido')]/text()",
            "//span[contains(text(), 'Presencial')]/text()"
        ]
        
        for selector in remote_selectors:
            remote = response.xpath(selector).get()
            if remote:
                return remote.strip()
        
        return ""
    
    def extract_posted_date_from_html(self, response):
        """Extract posted date from HTML fallback."""
        # Look for relative dates like "Hace X días"
        date_selectors = [
            "//*[contains(normalize-space(.), 'Hace') and contains(., 'día')]/text()",
            "//p[contains(text(), 'Hace')]/text()",
            "//*[contains(text(), 'Hace')]/text()"
        ]
        
        for selector in date_selectors:
            date_text = response.xpath(selector).get()
            if date_text and 'hace' in date_text.lower():
                return date_text.strip()
        
        return ""
    
    def extract_salary_from_description(self, description):
        """Extract salary information from job description."""
        if not description:
            return ""
        
        # Look for salary patterns in the description
        import re
        
        # Pattern for Colombian peso format: $ X.XXX.XXX or $ X,XXX,XXX
        salary_patterns = [
            r'\$\s*([\d.,]+)\s*(?:COP|pesos?|pesos colombianos?)',
            r'Salario:\s*\$\s*([\d.,]+)',
            r'\$\s*([\d.,]+)\s*\+?\s*prestaciones',
            r'([\d.,]+)\s*COP',
            r'([\d.,]+)\s*pesos',
            r'Salario:\s*([\d.,]+)',
            r'Apoyo\s+económico\s+de\s*\$\s*([\d.,]+)',
            r'([\d.,]+)\s*\+?\s*prestaciones'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                salary_value = match.group(1)
                # Clean up the salary value
                salary_value = salary_value.replace('.', '').replace(',', '')
                if salary_value.isdigit():
                    # Format as Colombian peso
                    formatted_salary = f"$ {int(salary_value):,} COP"
                    return formatted_salary
        
        # Look for "Salario confidencial" or similar
        if re.search(r'salario\s+confidencial', description, re.IGNORECASE):
            return "Salario confidencial"
        
        return ""
    
    def clean_html_tags(self, text):
        """Clean HTML tags from text, converting <br/> to spaces."""
        if not text:
            return ""
        
        # Convert <br/> tags to spaces
        text = text.replace('<br/>', ' ').replace('<br>', ' ').replace('<br />', ' ')
        
        # Remove other HTML tags
        import re
        clean_text = re.sub(r'<[^>]+>', '', text)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        return clean_text
    
    def extract_contract_from_text(self, text: str) -> str:
        """Extract contract type from text heuristically."""
        if not text:
            return ""
        
        # Look for contract type keywords
        contract_keywords = {
            'tiempo completo': 'Tiempo completo',
            'tiempo parcial': 'Medio tiempo',
            'contrato': 'Contrato',
            'permanente': 'Permanente',
            'temporal': 'Temporal',
            'indefinido': 'Indefinido',
            'determinado': 'Determinado',
            'freelance': 'Freelance',
            'independiente': 'Independiente',
            'plazo fijo': 'Plazo fijo',
            'obra labor': 'Obra labor'
        }
        
        text_lower = text.lower()
        for keyword, value in contract_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
    
    def extract_remote_from_text(self, text: str) -> str:
        """Extract remote work type from text heuristically."""
        if not text:
            return ""
        
        # Look for remote work keywords
        remote_keywords = {
            'remoto': 'Remoto',
            'teletrabajo': 'Remoto',
            'home office': 'Remoto',
            'presencial': 'Presencial',
            'híbrido': 'Híbrido',
            'hibrido': 'Híbrido',
            'mixto': 'Híbrido',
            'a distancia': 'Remoto'
        }
        
        text_lower = text.lower()
        for keyword, value in remote_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse Computrabajo date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in Computrabajo
            date_patterns = [
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'hace (\d+) semanas?',  # "hace X semanas"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, date_string, re.IGNORECASE)
                if match:
                    if 'hace' in pattern:
                        # Handle relative dates - return today's date
                        return datetime.today().date().isoformat()
                    else:
                        # Handle absolute dates
                        day, month, year = match.groups()
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            
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
    
    def closed(self, reason):
        """Called when spider is closed - log final statistics."""
        logger.info("=" * 60)
        logger.info("🏁 COMPUTRABAJO SPIDER FINAL STATISTICS")
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
            
