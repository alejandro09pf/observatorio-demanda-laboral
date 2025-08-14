"""
Scrapy middlewares for Labor Market Observatory
"""

import random
import time
import os
from scrapy import signals
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware
from scrapy.downloadermiddlewares.retry import RetryMiddleware
from scrapy.utils.response import response_status_message
from scrapy.exceptions import IgnoreRequest
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class UserAgentRotationMiddleware(UserAgentMiddleware):
    """Rotate user agents to avoid detection."""
    
    def __init__(self, user_agent=''):
        super().__init__(user_agent)
        self.user_agents = self._load_user_agents()
        self.current_index = 0
        self.rotation_strategy = os.getenv('USER_AGENT_ROTATION_STRATEGY', 'round_robin')
    
    def _load_user_agents(self):
        """Load user agents from file or use defaults."""
        user_agent_file = os.getenv('USER_AGENT_LIST_PATH', './config/user_agents.txt')
        
        if os.path.exists(user_agent_file):
            try:
                with open(user_agent_file, 'r', encoding='utf-8') as f:
                    return [line.strip() for line in f if line.strip()]
            except Exception as e:
                logger.warning(f"Could not load user agents from {user_agent_file}: {e}")
        
        # Default user agents if file not found
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0',
        ]
    
    def process_request(self, request, spider):
        """Set a user agent for each request."""
        if self.rotation_strategy == 'round_robin':
            ua = self.user_agents[self.current_index % len(self.user_agents)]
            self.current_index += 1
        else:  # random
            ua = random.choice(self.user_agents)
        
        request.headers['User-Agent'] = ua
        logger.debug(f"Set User-Agent: {ua[:50]}...")
        return None


class ProxyRotationMiddleware:
    """Proxy rotation middleware with authentication support."""
    
    def __init__(self):
        self.proxies = self._load_proxies()
        self.current_index = 0
        self.rotation_strategy = os.getenv('PROXY_ROTATION_STRATEGY', 'round_robin')
    
    def _load_proxies(self):
        """Load proxies from environment variable."""
        proxy_pool = os.getenv('PROXY_POOL', '')
        if proxy_pool:
            return [proxy.strip() for proxy in proxy_pool.split(',') if proxy.strip()]
        return []
    
    def process_request(self, request, spider):
        """Set proxy for request if available."""
        if not self.proxies:
            return None
        
        if self.rotation_strategy == 'round_robin':
            proxy = self.proxies[self.current_index % len(self.proxies)]
            self.current_index += 1
        else:  # random
            proxy = random.choice(self.proxies)
        
        request.meta['proxy'] = proxy
        logger.debug(f"Using proxy: {proxy}")
        return None


class RetryWithBackoffMiddleware(RetryMiddleware):
    """Custom retry middleware with exponential backoff."""
    
    def __init__(self, settings):
        super().__init__(settings)
        self.max_retry_times = settings.getint('RETRY_TIMES', 3)
        self.retry_http_codes = set(settings.getlist('RETRY_HTTP_CODES', [500, 502, 503, 504, 408, 429]))
        self.download_timeout = settings.getint('DOWNLOAD_TIMEOUT', 20)
    
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
            logger.info(f"Retrying {request.url} (attempt {retries}/{self.max_retry_times}) - Reason: {reason}")
            
            # Exponential backoff with jitter
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
