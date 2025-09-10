#!/usr/bin/env python3
"""
Extractor directo de OCC que funciona fuera del contexto de Scrapy
"""

import os
import time
import random
import logging
import re
import json
from typing import List, Dict, Optional
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class OCCDirectExtractor:
    """Extractor directo de OCC que funciona independientemente de Scrapy"""
    
    def __init__(self, country: str = "MX", max_pages: int = 3, limit: int = 50):
        self.country = country
        self.max_pages = max_pages
        self.limit = limit
        self.scraped_urls = set()
        self.driver = None
        self.items = []
        
    def setup_driver(self):
        """Configurar driver con undetected-chromedriver"""
        try:
            import undetected_chromedriver as uc
            logger.info("🚀 Using undetected-chromedriver for OCC extraction...")
            
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-images")
            options.add_argument("--disable-web-security")
            options.add_argument("--allow-running-insecure-content")
            
            # User agent realista
            options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36")
            
            # NO headless para evitar detección
            logger.info("🔧 Running in non-headless mode to avoid OCC detection")
            
            self.driver = uc.Chrome(options=options, version_main=139)
            logger.info("✅ Created undetected-chromedriver")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error setting up undetected-chromedriver: {e}")
            return False
    
    def apply_stealth_measures(self):
        """Aplicar medidas de stealth"""
        try:
            # Aplicar medidas de stealth adicionales
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_script("Object.defineProperty(navigator, 'languages', {get: () => ['es-MX','es','en']})")
            self.driver.execute_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            self.driver.execute_script("Object.defineProperty(navigator, 'permissions', {get: () => ({query: () => Promise.resolve({state: 'granted'})})})")
            self.driver.execute_script("Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})")
            self.driver.execute_script("Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})")
            self.driver.execute_script("Object.defineProperty(navigator, 'deviceMemory', {get: () => 8})")
            self.driver.execute_script("Object.defineProperty(navigator, 'maxTouchPoints', {get: () => 0})")
            self.driver.execute_script("Object.defineProperty(navigator, 'connection', {get: () => ({effectiveType: '4g', rtt: 50, downlink: 2})})")
            self.driver.execute_script("Object.defineProperty(navigator, 'getBattery', {get: () => () => Promise.resolve({level: 0.8, charging: false})})")
            self.driver.execute_script("Object.defineProperty(navigator, 'geolocation', {get: () => ({getCurrentPosition: () => {}, watchPosition: () => {}})})")
            self.driver.execute_script("Object.defineProperty(navigator, 'mediaDevices', {get: () => ({enumerateDevices: () => Promise.resolve([])})})")
            
            # Remover indicadores de automatización
            self.driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array")
            self.driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise")
            self.driver.execute_script("delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol")
            
            # Override toString methods
            self.driver.execute_script("window.chrome = {runtime: {}}")
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("✅ Applied advanced stealth measures")
            
        except Exception as e:
            logger.error(f"❌ Error applying stealth measures: {e}")
    
    def try_accept_cookies(self):
        """Intentar aceptar cookies"""
        try:
            from selenium.webdriver.common.by import By
            cookie_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Aceptar') or contains(text(), 'Accept') or contains(text(), 'OK')]")
            cookie_button.click()
            logger.info("✅ Cookies accepted")
            time.sleep(2)
        except:
            logger.info("ℹ️ No cookie banner found")
    
    def human_scroll(self, total_scrolls: int = 5):
        """Scroll humano simulado"""
        try:
            for i in range(total_scrolls):
                scroll_amount = random.randint(200, 800)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(0.5, 1.5))
            logger.info(f"✅ Completed {total_scrolls} human-like scrolls")
        except Exception as e:
            logger.error(f"❌ Error during human scroll: {e}")
    
    def extract_job_ids_from_page(self, page_source: str) -> List[str]:
        """Extraer job IDs del page source"""
        try:
            # Patrones para encontrar job IDs
            js_patterns = [
                r'oi:\s*[\'"](\d{7,8})[\'"]',  # oi: '20720591'
                r'OccLytics\.SendEventOcc.*?(\d{7,8})',  # From the analytics call
                r'/empleo/oferta/(\d{7,8})-',  # Direct URL pattern
                r'jobid[=:](\d{7,8})',  # jobid=20720591
                r'window\.conversionData.*?oi:\s*[\'"](\d{7,8})[\'"]',  # From conversion data
                r'data-id="(\d{7,8})"',  # data-id="20720591"
                r'"OfferId":"(\d{7,8})"',  # "OfferId":"20720591"
                r'ID:\s*(\d{7,8})',  # ID: 20720591
                r'empleo/oferta/(\d{7,8})-',  # URL pattern from OCC
            ]
            
            found_jobids = set()
            for pattern in js_patterns:
                matches = re.findall(pattern, page_source)
                found_jobids.update(matches)
            
            logger.info(f"✅ Found {len(found_jobids)} unique job IDs")
            return list(found_jobids)
            
        except Exception as e:
            logger.error(f"❌ Error extracting job IDs: {e}")
            return []
    
    def extract_title_for_jobid(self, jobid: str, page_source: str) -> str:
        """Extraer título para un job ID específico"""
        try:
            # Patrones para encontrar títulos
            title_patterns = [
                rf'ot:\s*[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}.*?oi:\s*[\'"]{jobid}[\'"]',  # ot: 'title' ... oi: 'jobid'
                rf'oi:\s*[\'"]{jobid}[\'"].*?ot:\s*[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}',  # oi: 'jobid' ... ot: 'title'
                rf'OccLytics\.SendEventOcc.*?[\'"]{{0,2}}([^\'"]{{20,100}})[\'"]{{0,2}}.*?{jobid}',  # From analytics
            ]
            
            for pattern in title_patterns:
                title_match = re.search(pattern, page_source, re.IGNORECASE | re.DOTALL)
                if title_match:
                    title_text = title_match.group(1).strip()
                    # Limpiar título
                    title_text = re.sub(r'[^\w\s\-/]', '', title_text).strip()
                    if len(title_text) >= 10:
                        return title_text
            
            return f"Job {jobid}"
            
        except Exception as e:
            logger.error(f"❌ Error extracting title for {jobid}: {e}")
            return f"Job {jobid}"
    
    def fetch_job_detail(self, jobid: str, title: str) -> Optional[Dict]:
        """Obtener detalles de un trabajo específico"""
        try:
            # Generar URL del trabajo
            slug = title.lower().replace(' ', '-').replace('/', '-')
            detail_url = f"https://www.occ.com.mx/empleo/oferta/{jobid}-{slug}/"
            
            if detail_url in self.scraped_urls:
                return None
            
            self.scraped_urls.add(detail_url)
            
            logger.info(f"🌐 Fetching job detail: {detail_url}")
            self.driver.get(detail_url)
            time.sleep(random.uniform(2.0, 3.0))
            
            # Crear item básico
            item = {
                'portal': 'occ',
                'country': self.country,
                'url': detail_url,
                'title': title,
                'company': 'OCC Company',
                'location': 'México',
                'salary_raw': '',
                'contract_type': 'Tiempo completo',
                'remote_type': 'Presencial',
                'description': 'Descripción no disponible',
                'requirements': 'Requisitos no especificados',
                'scraped_at': datetime.now().isoformat(),
                'job_id': jobid
            }
            
            # Intentar extraer más detalles si es posible
            try:
                from selenium.webdriver.common.by import By
                
                # Buscar título más específico
                title_elem = self.driver.find_element(By.CSS_SELECTOR, 'h1, h2, .title, [class*="title"]')
                if title_elem:
                    item['title'] = title_elem.text.strip() or title
                
                # Buscar empresa
                company_elem = self.driver.find_element(By.CSS_SELECTOR, '[class*="company"], [class*="empresa"]')
                if company_elem:
                    item['company'] = company_elem.text.strip() or 'OCC Company'
                
                # Buscar ubicación
                location_elem = self.driver.find_element(By.CSS_SELECTOR, '[class*="location"], [class*="ubicacion"]')
                if location_elem:
                    item['location'] = location_elem.text.strip() or 'México'
                
            except:
                pass  # Usar valores por defecto si no se pueden extraer
            
            logger.info(f"✅ Extracted job: {item['title']} at {item['company']}")
            return item
            
        except Exception as e:
            logger.error(f"❌ Error fetching job detail for {jobid}: {e}")
            return None
    
    def scrape_page(self, url: str, page_num: int) -> List[Dict]:
        """Scrapear una página específica"""
        try:
            logger.info(f"🌐 Loading page {page_num}: {url}")
            self.driver.get(url)
            
            # Esperar a que cargue
            time.sleep(random.uniform(3.0, 5.0))
            
            # Aceptar cookies
            self.try_accept_cookies()
            
            # Aplicar medidas de stealth
            self.apply_stealth_measures()
            
            # Scroll para cargar contenido dinámico
            self.human_scroll(total_scrolls=5)
            time.sleep(random.uniform(2.0, 3.0))
            
            # Obtener page source
            page_source = self.driver.page_source
            
            # Extraer job IDs
            job_ids = self.extract_job_ids_from_page(page_source)
            
            if not job_ids:
                logger.warning(f"⚠️ No job IDs found on page {page_num}")
                return []
            
            # Procesar cada job ID
            page_items = []
            for jobid in job_ids[:self.limit]:  # Limitar por página
                if len(self.items) >= self.limit:
                    break
                
                # Extraer título
                title = self.extract_title_for_jobid(jobid, page_source)
                
                # Obtener detalles del trabajo
                item = self.fetch_job_detail(jobid, title)
                if item:
                    page_items.append(item)
                    self.items.append(item)
            
            logger.info(f"✅ Scraped {len(page_items)} jobs from page {page_num}")
            return page_items
            
        except Exception as e:
            logger.error(f"❌ Error scraping page {page_num}: {e}")
            return []
    
    def scrape_all(self) -> List[Dict]:
        """Scrapear todas las páginas"""
        try:
            if not self.setup_driver():
                return []
            
            # URL base
            base_url = "https://www.occ.com.mx/empleos"
            
            # Scrapear páginas
            for page in range(1, self.max_pages + 1):
                if len(self.items) >= self.limit:
                    break
                
                page_url = base_url if page == 1 else f"{base_url}?page={page}"
                page_items = self.scrape_page(page_url, page)
                
                if not page_items:
                    logger.warning(f"⚠️ No items found on page {page}, stopping")
                    break
            
            logger.info(f"🎉 Scraping completed! Total items: {len(self.items)}")
            return self.items
            
        except Exception as e:
            logger.error(f"❌ Error during scraping: {e}")
            return []
        
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("🔚 Driver closed")
    
    def save_to_json(self, filename: str = "outputs/occ_real.json"):
        """Guardar resultados en JSON"""
        try:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.items, f, ensure_ascii=False, indent=2)
            
            logger.info(f"💾 Saved {len(self.items)} items to {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving to JSON: {e}")
            return False

def main():
    """Función principal para testing"""
    extractor = OCCDirectExtractor(country="MX", max_pages=2, limit=10)
    items = extractor.scrape_all()
    extractor.save_to_json()
    return items

if __name__ == "__main__":
    main()

