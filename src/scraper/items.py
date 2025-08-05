import scrapy


class JobItem(scrapy.Item):
    portal = scrapy.Field()
    country = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    requirements = scrapy.Field()
    salary_raw = scrapy.Field()
    contract_type = scrapy.Field()
    remote_type = scrapy.Field()
    posted_date = scrapy.Field()
