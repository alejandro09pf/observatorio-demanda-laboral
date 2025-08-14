import scrapy
from .base_spider import BaseSpider
from ..items import JobItem
from urllib.parse import urljoin
from datetime import datetime
import re


class ElempleoSpider(BaseSpider):
    name = "elempleo"
    allowed_domains = ["elempleo.com"]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.portal = "elempleo"
        
        # Set start URLs based on country
        country_urls = {
            'CO': ['https://www.elempleo.com/co/ofertas-empleo'],
            'MX': ['https://www.elempleo.com/mx/ofertas-empleo'],
            'AR': ['https://www.elempleo.com/ar/ofertas-empleo']
        }
        self.start_urls = country_urls.get(self.country, country_urls['CO'])

    def parse_search_results(self, response):
        """Parse search results page."""
        job_cards = response.css("div.job-card, article.job-offer")
        
        for job_card in job_cards:
            job_url = job_card.css("a.job-link::attr(href), a[href*='/oferta/']::attr(href)").get()
            if job_url:
                absolute_url = self.build_absolute_url(job_url, response.url)
                yield scrapy.Request(
                    url=absolute_url,
                    callback=self.parse_job,
                    meta={'job_card': job_card}
                )
        
        # Handle pagination
        next_page = response.css("a.next-page::attr(href), a[rel='next']::attr(href)").get()
        if next_page and self.current_page < self.max_pages:
            self.current_page += 1
            next_url = self.build_absolute_url(next_page, response.url)
            yield scrapy.Request(
                url=next_url,
                callback=self.parse_search_results,
                meta={'page': self.current_page}
            )

    def parse_job(self, response):
        """Parse individual job posting."""
        item = JobItem()
        
        # Basic job information
        item["portal"] = self.portal
        item["country"] = self.country
        item["url"] = response.url
        item["title"] = self.extract_text(response.css("h1.job-title::text, h1::text"))
        item["company"] = self.extract_text(response.css("span.company-name::text, .company::text"))
        item["location"] = self.extract_text(response.css("span.location::text, .location::text"))
        
        # Description and requirements
        description_elements = response.css("div.job-description *::text, .description *::text").getall()
        item["description"] = self.clean_text(" ".join(description_elements))
        
        requirements_elements = response.css("div.job-requirements *::text, .requirements *::text").getall()
        item["requirements"] = self.clean_text(" ".join(requirements_elements))
        
        # Salary information
        salary_element = response.css("span.salary::text, .salary::text").get()
        item["salary_raw"] = self.clean_text(salary_element) if salary_element else None
        
        # Contract and remote type
        contract_element = response.css("span.contract-type::text, .contract::text").get()
        item["contract_type"] = self.clean_text(contract_element) if contract_element else None
        
        remote_element = response.css("span.remote-type::text, .remote::text").get()
        item["remote_type"] = self.clean_text(remote_element) if remote_element else None
        
        # Posted date
        date_element = response.css("span.posted-date::text, .date::text").get()
        item["posted_date"] = self.parse_date(date_element) if date_element else datetime.today().date().isoformat()
        
        # Validate and yield item
        if self.validate_job_item(item):
            yield item
        else:
            self.logger.warning(f"Invalid job item for URL: {response.url}")
