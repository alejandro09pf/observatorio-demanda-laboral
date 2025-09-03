"""
Clarín spider for Labor Market Observatory.
Scrapes job postings from clasificados.clarin.com using Selenium
"""

import scrapy
from urllib.parse import urljoin, urlparse
from datetime import datetime
import re
import json
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from .base_spider import BaseSpider
from ..items import JobItem
from typing import Optional, List, Dict
import logging
import requests

logger = logging.getLogger(__name__)


class ClarinSpider(BaseSpider):
    """Selenium-based spider for Clarín job portal."""

    name = "clarin"
    allowed_domains = ["clasificados.clarin.com"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "clarin"
        self.driver = None
        self.scraped_count = 0
        self.error_count = 0

        # Set start URL based on country
        if self.country == "AR":
            self.start_url = "https://clasificados.clarin.com/empleos"
        elif self.country == "CO":
            self.start_url = "https://clasificados.clarin.com/co/empleos"
        elif self.country == "MX":
            self.start_url = "https://clasificados.clarin.com/mx/empleos"
        else:
            # Default to Argentina
            self.start_url = "https://clasificados.clarin.com/empleos"

        # Override custom settings for this spider
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 2,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 1,
        })

    def setup_driver(self):
        """Setup Chrome WebDriver with anti-detection options."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            # User agent will be handled by middleware - no hardcoded UA
            
            # Anti-detection flags
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("Chrome WebDriver setup completed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome WebDriver: {e}")
            return False

    def cleanup_driver(self):
        """Clean up WebDriver resources."""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver cleanup completed")
            except Exception as e:
                logger.error(f"Error during WebDriver cleanup: {e}")

    def closed(self, reason):
        """Called when spider is closed."""
        self.cleanup_driver()
        self.save_scraping_summary()

    def save_scraping_summary(self):
        """Save scraping summary to file."""
        summary = {
            "spider": self.name,
            "country": self.country,
            "scraped_count": self.scraped_count,
            "error_count": self.error_count,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            with open(f"outputs/clarin_scraping_summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            logger.info(f"Scraping summary saved: {summary}")
        except Exception as e:
            logger.error(f"Failed to save scraping summary: {e}")

    def start_requests(self):
        """Initialize Selenium and start scraping."""
        if not self.setup_driver():
            logger.error("Failed to setup WebDriver, cannot proceed")
            return

        # Yield a dummy request to trigger the parsing
        yield scrapy.Request(
            url=self.start_url,
            callback=self.parse_search_results,
            dont_filter=True
        )

    def parse_search_results(self, response):
        """Parse search results using Selenium."""
        try:
            logger.info(f"Starting Selenium scraping from: {self.start_url}")
            
            # Navigate to the start URL
            self.driver.get(self.start_url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Scroll to load more content (infinite scrolling)
            self.scroll_to_load_content()
            
            # Extract job cards and their IDs
            job_items = self.extract_job_items()
            
            logger.info(f"Found {len(job_items)} job items")
            
            # Process each job item
            for job_item in job_items:
                try:
                    yield job_item
                    self.scraped_count += 1
                except Exception as e:
                    logger.error(f"Error processing job item: {e}")
                    self.error_count += 1
                    continue
                    
        except Exception as e:
            logger.error(f"Error in parse_search_results: {e}")
            self.error_count += 1

    def scroll_to_load_content(self):
        """Scroll down to load more content (infinite scrolling)."""
        try:
            logger.info("Starting infinite scroll to load content...")
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while scroll_attempts < max_scroll_attempts:
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                
                # Wait for new content to load
                time.sleep(2)
                
                # Calculate new scroll height
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                
                if new_height == last_height:
                    # No more content loaded
                    break
                    
                last_height = new_height
                scroll_attempts += 1
                
                logger.info(f"Scroll attempt {scroll_attempts}: loaded more content")
            
            logger.info(f"Finished scrolling after {scroll_attempts} attempts")
            
        except Exception as e:
            logger.error(f"Error during scrolling: {e}")

    def extract_job_items(self) -> List[Dict]:
        """Extract job items from the page."""
        job_items = []
        
        try:
            # Wait for job cards to be present (using Clarín-specific classes)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".item-aviso, .flowGridItem, article"))
            )
            
            # Find all job cards using Clarín-specific selectors
            job_cards = self.driver.find_elements(By.CSS_SELECTOR, 
                ".item-aviso, .flowGridItem, article, div[class*='result']")
            
            logger.info(f"Found {len(job_cards)} potential job cards")
            
            for card in job_cards:
                try:
                    # Extract Advert ID using regex
                    advert_id = self.extract_advert_id(card)
                    
                    if not advert_id:
                        continue
                    
                    # Build detail URL
                    detail_url = f"https://clasificados.clarin.com/aviso/{advert_id}"
                    
                    # Fetch JSON data
                    json_data = self.fetch_job_json(detail_url)
                    
                    if not json_data:
                        continue
                    
                    # Parse job item from JSON
                    job_item = self.parse_job_from_json(json_data, detail_url)
                    
                    if job_item:
                        job_items.append(job_item)
                        
                except Exception as e:
                    logger.error(f"Error extracting job from card: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error extracting job items: {e}")
            
        return job_items

    def extract_advert_id(self, card) -> Optional[str]:
        """Extract Advert ID from job card using regex."""
        try:
            # Get card HTML
            card_html = card.get_attribute('outerHTML')
            
            # Look for 6-8 digit numbers that could be advert IDs
            # Try different patterns
            patterns = [
                r'\b(\d{6,8})\b',  # 6-8 digit numbers
                r'aviso[\/\-](\d{6,8})',  # aviso/123456 or aviso-123456
                r'id[=:](\d{6,8})',  # id=123456 or id:123456
                r'(\d{6,8})\.html',  # 123456.html
            ]
            
            for pattern in patterns:
                match = re.search(pattern, card_html)
                if match:
                    advert_id = match.group(1)
                    logger.debug(f"Found advert ID: {advert_id}")
                    return advert_id
            
            # If no pattern matches, try to extract from href attributes
            try:
                links = card.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute('href')
                    if href:
                        for pattern in patterns:
                            match = re.search(pattern, href)
                            if match:
                                advert_id = match.group(1)
                                logger.debug(f"Found advert ID from href: {advert_id}")
                                return advert_id
            except Exception as e:
                logger.debug(f"Error extracting from href: {e}")
                
            return None
            
        except Exception as e:
            logger.error(f"Error extracting advert ID: {e}")
            return None

    def fetch_job_json(self, detail_url: str) -> Optional[Dict]:
        """Fetch JSON data from job detail URL."""
        try:
            logger.debug(f"Fetching JSON from: {detail_url}")
            
            headers = {
                # User agent will be handled by middleware - no hardcoded UA
                'Accept': 'application/json, text/plain, */*',
                'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
                'Referer': 'https://clasificados.clarin.com/',
                'Origin': 'https://clasificados.clarin.com'
            }
            
            response = requests.get(detail_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                try:
                    json_data = response.json()
                    logger.debug(f"Successfully fetched JSON data")
                    return json_data
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from {detail_url}: {e}")
                    return None
            else:
                logger.error(f"HTTP {response.status_code} for {detail_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching JSON from {detail_url}: {e}")
            return None

    def parse_job_from_json(self, json_data: Dict, detail_url: str) -> Optional[Dict]:
        """Parse job information from JSON data."""
        try:
            # Create job item
            item = JobItem()
            
            # Basic information
            item['portal'] = 'clarin'
            item['country'] = self.country
            item['url'] = detail_url
            
            # Extract the aviso object from the JSON response
            aviso = json_data.get('aviso')
            if not aviso:
                logger.warning(f"No 'aviso' data found in JSON response")
                return None
            
            # Extract title and description from textoLibre
            texto_libre = aviso.get('textoLibre', '')
            if texto_libre:
                # For Clarín, the textoLibre contains the job title
                item['title'] = self.clean_text(texto_libre)
                # Use the title as description since there's no separate description field
                item['description'] = self.clean_text(texto_libre)
            else:
                item['title'] = ""
                item['description'] = ""
            
            # Extract posted date from fechaPublicacion (Unix timestamp to ISO 8601)
            fecha_publicacion = aviso.get('fechaPublicacion')
            if fecha_publicacion:
                try:
                    # Convert Unix timestamp to ISO 8601 (timestamp is in milliseconds)
                    timestamp = int(fecha_publicacion) / 1000  # Convert from milliseconds to seconds
                    date_obj = datetime.fromtimestamp(timestamp)
                    item['posted_date'] = date_obj.isoformat()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Could not parse fechaPublicacion {fecha_publicacion}: {e}")
                    item['posted_date'] = None
            else:
                item['posted_date'] = None
            
            # Extract company information
            nombre_anunciante = aviso.get('nombreAnunciante', '')
            tipo_anunciante = aviso.get('tipoAnunciante', '')
            
            if nombre_anunciante:
                item['company'] = self.clean_text(nombre_anunciante)
            elif tipo_anunciante:
                item['company'] = self.clean_text(tipo_anunciante)
            else:
                item['company'] = ""
            
            # Extract location from individuo
            individuo = aviso.get('individuo', '')
            if individuo:
                # Split by "#" and ";" as specified
                location_parts = individuo.replace('#', ';').split(';')
                location_parts = [part.strip() for part in location_parts if part.strip()]
                item['location'] = self.clean_text(', '.join(location_parts))
            else:
                item['location'] = ""
            
            # Extract requirements from textoLibre (heuristic)
            if texto_libre:
                # Look for common requirement keywords
                requirement_keywords = ['requisitos', 'experiencia', 'conocimientos', 'habilidades', 'perfil']
                requirements = []
                
                lines = texto_libre.split('\n')
                in_requirements_section = False
                
                for line in lines:
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in requirement_keywords):
                        in_requirements_section = True
                        requirements.append(line)
                    elif in_requirements_section and line.strip():
                        requirements.append(line)
                    elif in_requirements_section and not line.strip():
                        # Empty line might end requirements section
                        break
                
                item['requirements'] = self.clean_text('\n'.join(requirements))
            else:
                item['requirements'] = ""
            
            # Extract salary from textoLibre (heuristic)
            salary = self.extract_salary_from_text(texto_libre)
            item['salary_raw'] = salary
            
            # Extract contract type from textoLibre (heuristic)
            contract_type = self.extract_contract_from_text(texto_libre)
            item['contract_type'] = contract_type
            
            # Extract remote type from textoLibre (heuristic)
            remote_type = self.extract_remote_from_text(texto_libre)
            item['remote_type'] = remote_type
            
            # Validate item
            if not self.validate_job_item(item):
                logger.warning(f"Invalid job item: {item.get('title', 'No title')}")
                return None
            
            logger.info(f"Successfully parsed job: {item.get('title', 'No title')}")
            return item
            
        except Exception as e:
            logger.error(f"Error parsing job from JSON: {e}")
            return None

    def extract_salary_from_text(self, text: str) -> str:
        """Extract salary information from text heuristically."""
        if not text:
            return ""
        
        # Look for salary patterns
        salary_patterns = [
            r'\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # $1,000.00
            r'\d{1,3}(?:,\d{3})*\s*pesos',  # 1,000 pesos
            r'\d{1,3}(?:,\d{3})*\s*ars',  # 1,000 ARS
            r'salario[:\s]*(\$?\d{1,3}(?:,\d{3})*)',  # Salario: $1,000
            r'remuneración[:\s]*(\$?\d{1,3}(?:,\d{3})*)',  # Remuneración: $1,000
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return self.clean_text(match.group(0))
        
        return ""

    def extract_contract_from_text(self, text: str) -> str:
        """Extract contract type from text heuristically."""
        if not text:
            return ""
        
        # Look for contract type keywords
        contract_keywords = {
            'tiempo completo': 'Tiempo completo',
            'tiempo parcial': 'Tiempo parcial',
            'contrato': 'Contrato',
            'permanente': 'Permanente',
            'temporal': 'Temporal',
            'indefinido': 'Indefinido',
            'determinado': 'Determinado',
            'freelance': 'Freelance',
            'independiente': 'Independiente'
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
            'mixto': 'Híbrido'
        }
        
        text_lower = text.lower()
        for keyword, value in remote_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
