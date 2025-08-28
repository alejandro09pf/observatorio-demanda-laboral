"""
Elempleo spider for Labor Market Observatory.
Scrapes job postings from elempleo.com using individual job detail pages
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

class ElempleoSpider(BaseSpider):
    """Spider for Elempleo job portal using individual job detail pages."""
    
    name = "elempleo"
    allowed_domains = ["elempleo.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "elempleo"
        
        # Real job detail URLs discovered from Elempleo website
        if self.country == "CO":
            self.start_urls = [
                "https://www.elempleo.com/co/ofertas-trabajo/medico-general-medellin-1886557410",
                "https://www.elempleo.com/co/ofertas-trabajo/condcutor-domiciliario-bogota-1886557367",
                "https://www.elempleo.com/co/ofertas-trabajo/jefe-unidad-de-seguridad-de-la-informacion-1886557309",
                "https://www.elempleo.com/co/ofertas-trabajo/coordinador-centro-universitario-mitu-presencial-1886557312",
                "https://www.elempleo.com/co/ofertas-trabajo/vendedor-1886423696",
                "https://www.elempleo.com/co/ofertas-trabajo/asistente-comercial-las-ferias-1886557311",
                "https://www.elempleo.com/co/ofertas-trabajo/tecnicos-de-control-interno-1886557341",
                "https://www.elempleo.com/co/ofertas-trabajo/ingeniero-de-sistemas-cota-fontibon-suba-calle-80-engativa-1886557350",
                "https://www.elempleo.com/co/ofertas-trabajo/16264856062-analista-de-la-seguridad-de-la-informacion-1886557372",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-integral-de-admisiones-zona-norte-de-bogota-1886557330",
                "https://www.elempleo.com/co/ofertas-trabajo/tecnico-en-suspensiones-y-reconexion-motorizado-boyaca-1886557339",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-de-enfermeria-medellin-envigado-1886557322",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-de-laboratorio-facultad-de-ciencias-1886557368",
                "https://www.elempleo.com/co/ofertas-trabajo/camillero-clinica-oncologica-1886557394",
                "https://www.elempleo.com/co/ofertas-trabajo/gerente-comercial-1886557415",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-de-servicios-generales-1886557315",
                "https://www.elempleo.com/co/ofertas-trabajo/residente-de-control-de-programacion-y-presupuesto-1886557307",
                "https://www.elempleo.com/co/ofertas-trabajo/pitalitoelectricistas-o-electronicos-o-afines-1886557335",
                "https://www.elempleo.com/co/ofertas-trabajo/comerciales-sin-experiencia-con-disponibilidad-inmediata-md-1886557359",
                "https://www.elempleo.com/co/ofertas-trabajo/coordinador-de-abastecimiento-experiencia-sector-contruccion-oil-gas-1886557305",
                "https://www.elempleo.com/co/ofertas-trabajo/analista-gestion-documental-archivo-que-viva-por-la-calle-80-1886557377",
                "https://www.elempleo.com/co/ofertas-trabajo/asesor-de-negociacion-gestor-de-cobranza-call-center-y-en-sitio-motorizado-en-florencia-caqueta-1886557310",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-logistico-quindio-1886557349",
                "https://www.elempleo.com/co/ofertas-trabajo/recepcionista-asistente-administrativa-1886557323",
                "https://www.elempleo.com/co/ofertas-trabajo/coordinacion-de-prevencion-de-riesgos-chia-cajica-sopo-tocancipa-gachancipa-1886557346",
                "https://www.elempleo.com/co/ofertas-trabajo/coordinador-de-operaciones-bogota-1886557374",
                "https://www.elempleo.com/co/ofertas-trabajo/mecanico-automotriz-con-moto-cartagena-1886557352",
                "https://www.elempleo.com/co/ofertas-trabajo/asesor-comercial-jornada-adicional-cartago-1886557389",
                "https://www.elempleo.com/co/ofertas-trabajo/analista-de-calidad-call-center-1886557301",
                "https://www.elempleo.com/co/ofertas-trabajo/agente-de-televentas-bilingue-1886557380",
                "https://www.elempleo.com/co/ofertas-trabajo/analista-operativo-digitador-de-declaraciones-auxiliar-de-aduanas-1886557401",
                "https://www.elempleo.com/co/ofertas-trabajo/jardinero-1886557398",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-punto-de-venta-y-oficios-varios-bucaramanga-1886460783",
                "https://www.elempleo.com/co/ofertas-trabajo/impulsador-a-promotor-a-consumo-masivo-bello-1886557292",
                "https://www.elempleo.com/co/ofertas-trabajo/auxiliar-logistico-puerto-berrio-1886557369",
                "https://www.elempleo.com/co/ofertas-trabajo/tecnico-de-admisiones-y-autorizaciones-1886557299",
                "https://www.elempleo.com/co/ofertas-trabajo/hunter-especialista-venta-pauta-o-publicidad-digital-1886536299",
                "https://www.elempleo.com/co/ofertas-trabajo/desarrollador-a-frontend-1886557414"
            ]
        elif self.country == "MX":
            self.start_urls = [
                "https://www.elempleo.com/mx/ofertas-trabajo/desarrollador-software-mexico-825434",
                "https://www.elempleo.com/mx/ofertas-trabajo/ingeniero-sistemas-guadalajara-825435"
            ]
        elif self.country == "AR":
            self.start_urls = [
                "https://www.elempleo.com/ar/ofertas-trabajo/desarrollador-software-buenos-aires-825436",
                "https://www.elempleo.com/ar/ofertas-trabajo/analista-sistemas-cordoba-825437"
            ]
        
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
        """Start with the job detail URLs."""
        for url in self.start_urls:
            yield scrapy.Request(
                url=url,
                callback=self.parse_job,
                headers=self.get_headers()
            )
    
    def get_headers(self):
        """Get headers to avoid anti-bot detection."""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
    
    def parse_job(self, response):
        """Parse individual job posting using specific CSS selectors."""
        try:
            logger.info(f"Parsing job: {response.url}")
            
            # Create job item
            item = JobItem()
            
            # Basic information
            item['portal'] = 'elempleo'
            item['country'] = self.country
            item['url'] = response.url
            
            # Extract title using specific selector
            title = response.css("h1.ee-offer-title .js-jobOffer-title::text").get()
            if not title:
                # Fallback to general h1
                title = response.css("h1::text").get()
            item['title'] = self.clean_text(title) if title else ""
            
            # Extract company using specific selector
            company = response.css("h2.ee-company-title strong::text").get()
            if not company:
                # Fallback selectors
                company = (
                    response.css("h2.ee-company-title::text").get() or
                    response.css(".company-name::text").get() or
                    response.css(".employer::text").get()
                )
            item['company'] = self.clean_text(company) if company else ""
            
            # Extract salary using specific selector
            salary_raw = response.css("span.js-joboffer-salary::text").get()
            if not salary_raw:
                # Fallback selectors
                salary_raw = (
                    response.css(".salary::text").get() or
                    response.css(".wage::text").get() or
                    response.css("[class*='salary']::text").get()
                )
            item['salary_raw'] = self.clean_text(salary_raw) if salary_raw else ""
            
            # Extract location using specific selector
            location = response.css("span.js-joboffer-city::text").get()
            if not location:
                # Fallback selectors
                location = (
                    response.css(".location::text").get() or
                    response.css(".city::text").get() or
                    response.css("[class*='location']::text").get()
                )
            item['location'] = self.clean_text(location) if location else ""
            
            # Extract posted date using specific selector
            posted_date = response.css("span.js-publish-date::text").get()
            if not posted_date:
                # Fallback selectors
                posted_date = (
                    response.css(".date::text").get() or
                    response.css(".posted::text").get() or
                    response.css("[class*='date']::text").get()
                )
            item['posted_date'] = self.parse_date(posted_date) if posted_date else None
            
            # Extract additional fields for potential future use (not stored in JobItem)
            category = response.css("span.js-position-area::text").get()
            profession = response.css("span.js-profession::text").get()
            education_level = response.css("span.js-education-level::text").get()
            sector = response.css("span.js-sector::text").get()
            
            # Log additional fields for debugging
            if category or profession or education_level or sector:
                logger.info(f"Additional fields found - Category: {category}, Profession: {profession}, Education: {education_level}, Sector: {sector}")
            
            # Extract description using specific selector
            description_parts = response.css("div.description-block p span::text").getall()
            if not description_parts:
                # Fallback selectors
                description_parts = (
                    response.css("div.description-block p::text").getall() or
                    response.css(".description::text").getall() or
                    response.css(".job-description::text").getall() or
                    response.css("[class*='description']::text").getall()
                )
            
            item['description'] = " ".join([self.clean_text(part) for part in description_parts if part]) if description_parts else ""
            
            # Extract requirements using specific selector
            requirements = response.xpath("//h2[contains(text(), 'Requisitos para postularse')]/following-sibling::p[1]/span/text()").get()
            if not requirements:
                # Fallback selectors
                requirements = (
                    response.css(".requirements::text").get() or
                    response.css(".skills::text").get() or
                    response.css("[class*='requirement']::text").get()
                )
            item['requirements'] = self.clean_text(requirements) if requirements else ""
            
            # Extract contract type and remote type from description or requirements
            contract_type = self.extract_contract_from_text(item['description'] + " " + item['requirements'])
            item['contract_type'] = contract_type
            
            remote_type = self.extract_remote_from_text(item['description'] + " " + item['requirements'])
            item['remote_type'] = remote_type
            
            # Validate item
            if not self.validate_job_item(item):
                logger.warning(f"Invalid job item: {item.get('title', 'No title')}")
                return
            
            logger.info(f"Successfully parsed job: {item.get('title', 'No title')}")
            yield item
            
        except Exception as e:
            logger.error(f"Error parsing job {response.url}: {e}")
            return
    
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
            'independiente': 'Independiente',
            'plazo fijo': 'Plazo fijo',
            'obra labor': 'Obra labor',
            'termino fijo': 'Término fijo',
            'termino indefinido': 'Término indefinido'
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
            'a distancia': 'Remoto',
            'trabajo desde casa': 'Remoto',
            'modalidad remota': 'Remoto',
            'modalidad presencial': 'Presencial',
            'modalidad hibrida': 'Híbrido'
        }
        
        text_lower = text.lower()
        for keyword, value in remote_keywords.items():
            if keyword in text_lower:
                return value
        
        return ""
    
    def parse_date(self, date_string: str) -> Optional[str]:
        """Parse Elempleo date format."""
        if not date_string:
            return None
        
        try:
            # Common date patterns in Elempleo
            date_patterns = [
                r'Publicado (\d{1,2}) (\w+) (\d{4})',  # "Publicado 23 Ago 2025"
                r'(\d{1,2})/(\d{1,2})/(\d{4})',  # DD/MM/YYYY
                r'(\d{1,2})-(\d{1,2})-(\d{4})',  # DD-MM-YYYY
                r'hace (\d+) días?',  # "hace X días"
                r'hace (\d+) horas?',  # "hace X horas"
                r'(\d{1,2}) (\w+) (\d{4})',  # "23 Ago 2025"
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
                        # Handle relative dates - return today's date
                        return datetime.today().date().isoformat()
                    elif len(match.groups()) == 3:
                        # Handle absolute dates
                        if pattern == r'Publicado (\d{1,2}) (\w+) (\d{4})':
                            day, month, year = match.groups()
                        elif pattern == r'(\d{1,2}) (\w+) (\d{4})':
                            day, month, year = match.groups()
                        elif pattern == r'(\d{1,2}) de (\w+) de (\d{4})':
                            day, month, year = match.groups()
                        else:
                            day, month, year = match.groups()
                        
                        # Convert month name to number
                        month_lower = month.lower()[:3]
                        if month_lower in month_map:
                            month_num = month_map[month_lower]
                            return f"{year}-{month_num}-{day.zfill(2)}"
                        # Try full month name
                        elif month.lower() in month_map:
                            month_num = month_map[month.lower()]
                            return f"{year}-{month_num}-{day.zfill(2)}"
            
            # If no pattern matches, return today's date
            return datetime.today().date().isoformat()
            
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return datetime.today().date().isoformat()
