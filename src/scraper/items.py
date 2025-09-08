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
    
    # Additional fields for hiring.cafe and other portals
    job_id = scrapy.Field()
    job_category = scrapy.Field()
    role_activities = scrapy.Field()
    compensation = scrapy.Field()
    geolocation = scrapy.Field()
    source_country = scrapy.Field()
    scraped_at = scrapy.Field()