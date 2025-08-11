"""
Scrapy middlewares for Labor Market Observatory
"""

import random
import time
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from scrapy.exceptions import IgnoreRequest
import logging

logger = logging.getLogger(__name__)

class RotateUserAgentMiddleware(UserAgentMiddleware):
    """Rotate user agents to avoid detection."""
    
    def __init__(self, user_agent=''):
        super().__init__(user_agent)
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.59',
        ]
    
    def process_request(self, request, spider):
        """Set a random user agent for each request."""
        ua = random.choice(self.user_agents)
        request.headers['User-Agent'] = ua
        logger.debug(f"Set User-Agent: {ua}")
        return None

class CustomRetryMiddleware(RetryMiddleware):
    """Custom retry middleware with exponential backoff."""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429]))
    
    def process_response(self, request, response, spider):
        """Process response and retry if needed."""
        if response.status in self.retry_http_codes:
            reason = response_status_message(response.status)
            return self._retry(request, reason, spider) or response
        
        return response
    
    def process_exception(self, request, exception, spider):
        """Process exceptions and retry if needed."""
        if isinstance(exception, self.EXCEPTIONS_TO_RETRY):
            return self._retry(request, exception, spider)
        
        return None
    
    def _retry(self, request, reason, spider):
        """Retry request with exponential backoff."""
        retries = request.meta.get('retry_times', 0) + 1
        
        if retries <= self.max_retry_times:
            logger.info(f"Retrying {request.url} (attempt {retries}/{self.max_retry_times})")
            
            # Exponential backoff
            delay = min(60, (2 ** retries) + random.uniform(0, 1))
            time.sleep(delay)
            
            retry_req = request.copy()
            retry_req.meta['retry_times'] = retries
            retry_req.dont_filter = True
            
            return retry_req
        
        logger.error(f"Gave up retrying {request.url} after {retries} attempts")
        return None

class RandomDelayMiddleware:
    """Add random delays between requests."""
    
    def __init__(self, delay_range=(1, 3)):
        self.delay_range = delay_range
    
    def process_request(self, request, spider):
        """Add random delay before processing request."""
        delay = random.uniform(*self.delay_range)
        time.sleep(delay)
        logger.debug(f"Added delay of {delay:.2f}s")
        return None

class ProxyMiddleware:
    """Proxy rotation middleware (placeholder for future implementation)."""
    
    def __init__(self):
        self.proxies = []  # Add proxy list here if needed
    
    def process_request(self, request, spider):
        """Set proxy for request if available."""
        if self.proxies:
            proxy = random.choice(self.proxies)
            request.meta['proxy'] = proxy
            logger.debug(f"Using proxy: {proxy}")
        return None
