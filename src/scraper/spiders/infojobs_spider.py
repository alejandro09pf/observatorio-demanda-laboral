import scrapy
from ..items import JobItem
from urllib.parse import urljoin
from datetime import datetime


class InfoJobsSpider(scrapy.Spider):
    name = "infojobs"
    allowed_domains = ["infojobs.net"]
    start_urls = [
        "https://www.infojobs.net/jobsearch/search-results/list.xhtml"
    ]

    custom_settings = {
        "DOWNLOAD_DELAY": 1,
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AcademicResearchBot/1.0"
    }

    def parse(self, response):
        job_cards = response.css("article")

        for job in job_cards:
            item = JobItem()

            item["portal"] = "infojobs"
            item["country"] = "ES"  # Cambia si decides scrapear otro país
            item["title"] = job.css("h2 h2 a::text").get(default="").strip()
            item["url"] = urljoin(response.url, job.css("a::attr(href)").get(default="").strip())
            item["company"] = job.css(".company::text").get(default="").strip()
            item["location"] = job.css(".location::text").get(default="").strip()
            item["description"] = job.css(".description::text").get(default="").strip()

            # Campos extendidos (si aparecen)
            item["requirements"] = None
            item["salary_raw"] = None
            item["contract_type"] = None
            item["remote_type"] = None
            item["posted_date"] = datetime.today().date().isoformat()

            yield item

        # Paginación
        next_page = response.css("a[rel=next]::attr(href)").get()
        if next_page:
            next_url = urljoin(response.url, next_page)
            yield scrapy.Request(url=next_url, callback=self.parse)
