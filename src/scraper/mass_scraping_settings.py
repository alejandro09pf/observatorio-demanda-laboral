"""
Scrapy settings for Mass Scraping - Labor Market Observatory
Optimized for collecting 200k+ job ads efficiently
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from config.settings import get_settings
    # Get application settings
    settings = get_settings()
except ImportError:
    # Fallback settings if config module is not available
    class FallbackSettings:
        scraper_concurrent_requests = 16
        scraper_download_delay = 0.5
        scraper_retry_times = 3
        scraper_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    settings = FallbackSettings()

# Scrapy project settings
BOT_NAME = 'labor_observatory_mass'

SPIDER_MODULES = ['src.scraper.spiders']
NEWSPIDER_MODULE = 'src.scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure concurrent requests for mass scraping
CONCURRENT_REQUESTS = 64  # Increased for mass scraping
CONCURRENT_REQUESTS_PER_DOMAIN = 32  # Increased per domain
CONCURRENT_REQUESTS_PER_IP = 32

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = 0.1  # Minimal delay for faster scraping
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_DELAY_RANGE = (0.05, 0.3)

# Download timeout
DOWNLOAD_TIMEOUT = 10  # Reduced timeout for faster failures

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scraper.middlewares.UserAgentRotationMiddleware': 400,
    # Disable proxy middleware for mass scraping to avoid 403 errors
    'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': None,
    'scraper.middlewares.ProxyRotationMiddleware': None,
    'scraper.middlewares.RetryWithBackoffMiddleware': 770,
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': True,
    'scrapy.spidermiddlewares.dupefilter.DupeFilterMiddleware': None,  # Disable built-in duplicate filter
}

# Disable duplicate filtering completely
DUPEFILTER_ENABLED = False

# Enable or disable extensions here
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Feed export settings - save items to JSON files
FEEDS = {
    'outputs/%(name)s_mass.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'overwrite': True,
        'indent': 2,
    }
}

# Configure item pipelines for mass scraping
ITEM_PIPELINES = {
    'scraper.mass_scraping_pipeline.MassScrapingPostgresPipeline': 300,
}

# Disable the default pipeline
ITEM_PIPELINES_DISABLED = [
    'scraper.pipelines.JobPostgresPipeline',
]

# Retry configuration
RETRY_ENABLED = True
RETRY_TIMES = 1  # Minimal retries for faster scraping
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# User agent
USER_AGENT = settings.scraper_user_agent

# Disable HTTP caching to prevent replaying 429 errors
# IMPORTANT: hiring.cafe returns 429 rate limits which get cached and replayed forever
HTTPCACHE_ENABLED = False
HTTPCACHE_EXPIRATION_SECS = 1800  # Not used when caching is disabled
HTTPCACHE_DIR = 'httpcache'
HTTPCACHE_IGNORE_HTTP_CODES = []
HTTPCACHE_STORAGE = 'scrapy.extensions.httpcache.FilesystemCacheStorage'

# Logging
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/mass_scraping.log'

# AutoThrottle extension - disabled for mass scraping
AUTOTHROTTLE_ENABLED = False

# Additional speed optimizations
SCHEDULER_ORDER = 'BFO'  # Breadth-first order for faster processing
SCHEDULER_DISK_QUEUE = 'scrapy.squeues.PickleFifoDiskQueue'
SCHEDULER_MEMORY_QUEUE = 'scrapy.squeues.FifoMemoryQueue'

# Database connection parameters for pipeline
DB_PARAMS = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5433)),
    'database': os.getenv('DB_NAME', 'labor_observatory'),
    'user': os.getenv('DB_USER', 'labor_user'),
    'password': os.getenv('DB_PASSWORD', '123456'),
}