"""
OCCMundial spider - OPTIMIZED VERSION.
Pure Scrapy approach with smart request handling for speed.
Target: 800-1000 jobs/hour with aggressive parallelization.
"""

import re
import logging
from datetime import datetime
from urllib.parse import urljoin
from typing import Optional, Set

import scrapy
from .base_spider import BaseSpider
from ..items import JobItem

logger = logging.getLogger(__name__)


class OCCMundialSpider(BaseSpider):
    """OPTIMIZED OCC spider: Pure Scrapy with aggressive parallelization."""

    name = "occmundial"
    allowed_domains = ["occ.com.mx", "www.occ.com.mx"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "occmundial"
        self.scraped_urls: Set[str] = set()

        logger.info(f"🔥 OPTIMIZED MODE: Pure Scrapy with smart requests")
        logger.info(f"🎯 Target: ~1000 jobs/hora (aggressive parallelization)")

        # ULTRA-AGGRESSIVE Scrapy settings
        self.custom_settings.update({
            'DOWNLOAD_DELAY': 0.3,  # Very fast
            'RANDOMIZE_DOWNLOAD_DELAY': False,
            'CONCURRENT_REQUESTS_PER_DOMAIN': 16,  # High concurrency
            'CONCURRENT_REQUESTS': 32,
            'ROBOTSTXT_OBEY': False,
            'HTTPCACHE_ENABLED': False,
            'AUTOTHROTTLE_ENABLED': False,  # Disable autothrottle for max speed
            'RETRY_TIMES': 2,
            'DOWNLOAD_TIMEOUT': 15,
            'DEFAULT_REQUEST_HEADERS': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'es-MX,es;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        })

        # Set start URLs based on country
        if self.country == "MX":
            self.start_urls = ["https://www.occ.com.mx/empleos"]
        elif self.country == "CO":
            self.start_urls = ["https://co.occ.com.mx/empleos"]
        elif self.country == "AR":
            self.start_urls = ["https://ar.occ.com.mx/empleos"]
        else:
            self.start_urls = ["https://www.occ.com.mx/empleos"]

        logger.info(f"🚀 Optimized OCC initialized for {self.country}")


    def start_requests(self):
        """Start requests - Pure Scrapy approach."""
        if not self._is_orchestrator_execution():
            raise RuntimeError(
                "This spider 'OCCMundialSpider' can only be executed through the orchestrator.\n"
                "Use: python -m src.orchestrator run-once occmundial --country <COUNTRY>"
            )

        for url in self.start_urls:
            for page in range(1, self.max_pages + 1):
                if page == 1:
                    page_url = url
                else:
                    page_url = f"{url}?page={page}"

                logger.info(f"🔥 Queuing listing page {page}: {page_url}")
                yield scrapy.Request(
                    url=page_url,
                    callback=self.parse_listing,
                    meta={'page': page},
                    dont_filter=True,
                    errback=self.handle_error
                )

    def parse_listing(self, response):
        """Parse listing page and schedule detail requests."""
        page = response.meta.get('page', 1)
        logger.info(f"📄 Parsing listing page {page}: {response.url}")
        logger.info(f"   Status: {response.status}, Size: {len(response.body)} bytes")

        # Extract job IDs from JavaScript/HTML using regex patterns
        js_patterns = [
            r'oi:\s*[\'"](\d{7,9})[\'"]',  # oi:"12345678"
            r'OccLytics\.SendEventOcc.*?(\d{7,9})',  # OccLytics events
            r'/empleo/oferta/(\d{7,9})-',  # URL patterns
            r'jobid[=:](\d{7,9})',  # jobid=12345678
            r'data-id="(\d{7,9})"',  # data-id="12345678"
            r'"OfferId":"(\d{7,9})"',  # JSON OfferId
            r'ID:\s*(\d{7,9})',  # ID: 12345678
        ]

        found_jobids = set()
        page_text = response.text

        for pattern in js_patterns:
            matches = re.findall(pattern, page_text)
            found_jobids.update(matches)

        logger.info(f"   Found {len(found_jobids)} job IDs in JavaScript/HTML")

        # Extract job links from HTML as backup
        job_links = response.xpath('//a[contains(@href, "/empleo/oferta/")]/@href').getall()

        # Process regex-found job IDs
        new_jobs = 0
        for jobid in found_jobids:
            if jobid not in self.scraped_urls:
                self.scraped_urls.add(jobid)

                # Build detail URL
                detail_url = f"https://www.occ.com.mx/empleo/oferta/{jobid}/"

                logger.info(f"   🚀 Queuing detail: {jobid}")
                new_jobs += 1

                yield scrapy.Request(
                    url=detail_url,
                    callback=self.parse_detail,
                    meta={'jobid': jobid},
                    errback=self.handle_error,
                    dont_filter=True,
                    priority=1
                )

        # Process XPath links as backup
        for link in job_links:
            match = re.search(r'/empleo/oferta/(\d{7,9})-', link)
            if match:
                jobid = match.group(1)
                if jobid not in self.scraped_urls:
                    self.scraped_urls.add(jobid)
                    detail_url = urljoin(response.url, link)

                    logger.info(f"   🚀 Queuing detail from XPath: {jobid}")
                    new_jobs += 1

                    yield scrapy.Request(
                        url=detail_url,
                        callback=self.parse_detail,
                        meta={'jobid': jobid},
                        errback=self.handle_error,
                        dont_filter=True,
                        priority=1
                    )

        logger.info(f"✅ Page {page} complete: {new_jobs} new jobs queued")

    def parse_detail(self, response):
        """Parse job detail page."""
        jobid = response.meta.get('jobid', 'unknown')

        logger.info(f"🔍 Parsing detail: {jobid} - {response.url[:80]}")

        if response.status != 200:
            logger.error(f"❌ Got status {response.status} for {response.url}")
            return

        # Extract job data
        item = JobItem()
        item['portal'] = 'occmundial'
        item['country'] = self.country
        item['url'] = response.url

        # Title - simplified XPath
        title = response.xpath('//h1//text()').get() or \
                response.xpath('//title/text()').get() or \
                response.xpath('//meta[@property="og:title"]/@content').get()

        item['title'] = title.strip() if title else f"Empleo {jobid}"

        # Company - more specific selectors
        company = response.xpath('//div[@id="jobCompanyName"]//text()').get() or \
                  response.xpath('//*[@class="company-name"]//text()').get() or \
                  response.xpath('//span[contains(@class, "company")]//text()').get() or \
                  response.xpath('//div[contains(@class, "empresa")]//text()').get() or \
                  response.css('.company::text').get() or \
                  response.xpath('//meta[@property="og:site_name"]/@content').get()

        item['company'] = company.strip() if company else "No especificado"

        # Location - more specific selectors
        location = response.xpath('//div[@id="jobLocation"]//text()').get() or \
                   response.xpath('//*[@class="location"]//text()').get() or \
                   response.xpath('//span[contains(@class, "location")]//text()').get() or \
                   response.xpath('//div[contains(@class, "ubicacion")]//text()').get() or \
                   response.css('.location::text').get()

        item['location'] = location.strip() if location else self.country

        # Description - avoid navigation by being more specific
        desc_parts = response.xpath('//div[@id="jobDescription"]//text()').getall() or \
                     response.xpath('//div[contains(@class, "job-description")]//text()').getall() or \
                     response.xpath('//section[contains(@class, "description")]//text()').getall() or \
                     response.xpath('//div[contains(@class, "descripcion")]//text()').getall() or \
                     response.css('.description::text').getall()

        # Filter out navigation and header text
        if desc_parts:
            cleaned = [d.strip() for d in desc_parts if d.strip() and len(d.strip()) > 10]
            # Remove common navigation keywords
            nav_keywords = ['sueldos', 'blog', 'publicar vacante', 'regístrate', 'inicia sesión', 'nuevo']
            cleaned = [d for d in cleaned if not any(kw in d.lower() for kw in nav_keywords)]
            item['description'] = ' '.join(cleaned[:300]) if cleaned else f"Detalles del trabajo para {item['title']}"
        else:
            item['description'] = f"Detalles del trabajo para {item['title']}"

        # Requirements
        req_parts = response.xpath('//div[contains(@class, "requirement")]//text()').getall() or \
                    response.xpath('//div[contains(@class, "requisito")]//text()').getall() or \
                    response.xpath('//div[contains(@class, "skills")]//text()').getall()

        if req_parts:
            cleaned = [r.strip() for r in req_parts if r.strip() and len(r.strip()) > 3]
            item['requirements'] = ' '.join(cleaned[:150])
        else:
            item['requirements'] = ""

        # Salary
        salary = response.xpath('//*[contains(@class, "salary")]//text()').get() or \
                 response.xpath('//*[contains(@class, "salar")]//text()').get()

        item['salary_raw'] = salary.strip() if salary else ""

        # Default values
        item['contract_type'] = ""
        item['remote_type'] = ""
        item['posted_date'] = datetime.now().date().isoformat()

        # Validate and yield
        if len(item['title']) >= 3:
            logger.info(f"✅ SUCCESS: {item['title'][:60]} | {item['company']}")
            yield item
        else:
            logger.warning(f"⚠️ Validation failed: title too short")

    def handle_error(self, failure):
        """Handle Scrapy request errors."""
        logger.error(f"❌ Scrapy request failed: {failure.request.url}")
        logger.error(f"   Reason: {failure.value}")
