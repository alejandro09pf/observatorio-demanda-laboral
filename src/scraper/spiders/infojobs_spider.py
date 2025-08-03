import scrapy
from ..items import JobItem

class InfoJobsSpider(scrapy.Spider):
    name = "infojobs"
    allowed_domains = ["infojobs.net"]
    start_urls = ["https://www.infojobs.net/jobsearch/search-results/list.xhtml"]

    def parse(self, response):
        jobs = response.css("article")  # selector específico del portal
        for job in jobs:
            item = JobItem()
            item["title"] = job.css("h2 a::text").get()
            item["url"] = job.css("h2 a::attr(href)").get()
            item["location"] = job.css(".location::text").get()
            item["company"] = job.css(".company::text").get()
            item["description"] = job.css(".description::text").get()
            yield item

        # paginación
        next_page = response.css("a[rel=next]::attr(href)").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)
