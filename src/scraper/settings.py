"""
Scrapy settings for Labor Market Observatory
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
        scraper_concurrent_requests = 8
        scraper_download_delay = 1.0
        scraper_retry_times = 3
        scraper_user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    settings = FallbackSettings()

# Scrapy project settings
BOT_NAME = 'labor_observatory'

SPIDER_MODULES = ['src.scraper.spiders']
NEWSPIDER_MODULE = 'src.scraper.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure concurrent requests
CONCURRENT_REQUESTS = int(os.getenv('SCRAPY_CONCURRENT_REQUESTS', settings.scraper_concurrent_requests))
CONCURRENT_REQUESTS_PER_DOMAIN = 8
CONCURRENT_REQUESTS_PER_IP = 8

# Configure a delay for requests for the same website
DOWNLOAD_DELAY = float(os.getenv('SCRAPY_DOWNLOAD_DELAY', settings.scraper_download_delay))
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_DELAY_RANGE = (0.5, 2.0)

# Download timeout
DOWNLOAD_TIMEOUT = int(os.getenv('SCRAPY_DOWNLOAD_TIMEOUT', 20))

# Enable or disable downloader middlewares
DOWNLOADER_MIDDLEWARES = {
    'scrapy.downloadermiddlewares.useragent.UserAgentMiddleware': None,
    'scraper.middlewares.UserAgentRotationMiddleware': 400,
    # 'scrapy.downloadermiddlewares.httpproxy.HttpProxyMiddleware': 750,
    # 'scraper.middlewares.ProxyRotationMiddleware': 760,
    'scraper.middlewares.RetryWithBackoffMiddleware': 770,
}

# Enable or disable spider middlewares
SPIDER_MIDDLEWARES = {
    'scrapy.spidermiddlewares.httperror.HttpErrorMiddleware': True,
}

# Enable or disable extensions here
EXTENSIONS = {
    'scrapy.extensions.telnet.TelnetConsole': None,
}

# Feed export settings - save items to JSON files
FEEDS = {
    'outputs/%(name)s_real.json': {
        'format': 'json',
        'encoding': 'utf8',
        'store_empty': False,
        'overwrite': True,
        'indent': 2,
    }
}

# Configure item pipelines
ITEM_PIPELINES = {
    'scraper.pipelines.JobPostgresPipeline': 300,
}

# Retry configuration
RETRY_ENABLED = True
RETRY_TIMES = int(os.getenv('SCRAPY_RETRY_TIMES', settings.scraper_retry_times))
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

# Database connection parameters for pipeline
DB_PARAMS = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 5433)),
    'database': os.getenv('DB_NAME', 'labor_observatory'),
    'user': os.getenv('DB_USER', 'labor_user'),
    'password': os.getenv('DB_PASSWORD', 'your_password'),
}
