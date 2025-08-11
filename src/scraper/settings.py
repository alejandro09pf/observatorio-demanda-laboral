"""
Scrapy settings for Labor Market Observatory
"""

from config.settings import get_settings

# Get application settings
settings = get_settings()

# Scrapy project settings
BOT_NAME = 'labor_observatory'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure concurrent requests
CONCURRENT_REQUESTS = settings.scraper_concurrent_requests
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 8

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = settings.scraper_download_delay
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_DELAY_RANGE = (0.5, 2.0)

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scraper.middlewares.RotateUserAgentMiddleware': 400,
    'scraper.middlewares.CustomRetryMiddleware': 550,
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': True,
}

# Configure item pipelines
ITEM_PIPELINES = {
    'scraper.pipelines.ValidationPipeline': 300,
    'scraper.pipelines.NormalizationPipeline': 400,
    'scraper.pipelines.DatabasePipeline': 500,
}

# Retry configuration
RETRY_ENABLED = True
RETRY_TIMES = settings.scraper_retry_times
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# User agent
USER_AGENT = settings.scraper_user_agent

# Enable and configure HTTP caching
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 3600
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scrapy.log'

# AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False

# Enable and configure the AutoThrottle extension
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 60
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0
AUTOTHROTTLE_DEBUG = False
