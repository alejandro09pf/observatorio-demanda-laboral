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
    """Enhanced proxy rotation middleware with portal-specific strategies."""
    
    def __init__(self):
        self.proxies = self._load_proxies()
        self.current_index = 0
        self.rotation_strategy = os.getenv('PROXY_ROTATION_STRATEGY', 'round_robin')
        self.proxy_config = self._load_proxy_config()
        self.proxy_failures = {}  # Track failures per proxy
        self.portal_stats = {}    # Track usage per portal
        
    def _load_proxies(self):
        """Load proxies from environment variable."""
        proxy_pool = os.getenv('PROXY_POOL', '')
        if proxy_pool:
            return [proxy.strip() for proxy in proxy_pool.split(',') if proxy.strip()]
        return []
    
    def _load_proxy_config(self):
        """Load proxy configuration from YAML file."""
        try:
            import yaml
            config_file = os.getenv('PROXY_CONFIG_PATH', './config/proxies.yaml')
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"Could not load proxy config: {e}")
        return {}
    
    def _get_portal_config(self, spider):
        """Get portal-specific proxy configuration."""
        portal = getattr(spider, 'portal', getattr(spider, 'name', 'default'))
        portal_config = self.proxy_config.get('portal_config', {}).get(portal, {})
        
        if not portal_config:
            # Use default configuration
            global_settings = self.proxy_config.get('global_settings', {})
            portal_config = {
                'pool': global_settings.get('default_pool', 'standard'),
                'rotation_strategy': global_settings.get('default_rotation', 'per_request'),
                'timeout': global_settings.get('default_timeout', 20),
                'max_retries': global_settings.get('default_max_retries', 3)
            }
        
        return portal_config
    
    def _get_proxy_pool(self, pool_name):
        """Get proxy pool by name."""
        pools = self.proxy_config.get('proxy_pools', {})
        if pool_name in pools:
            return pools[pool_name]['proxies']
        return self.proxies  # Fallback to environment variable
    
    def _select_proxy(self, spider, request):
        """Select appropriate proxy based on portal configuration."""
        portal_config = self._get_portal_config(spider)
        pool_name = portal_config.get('pool', 'standard')
        rotation_strategy = portal_config.get('rotation_strategy', 'per_request')
        
        # Get available proxies for this pool
        available_proxies = self._get_proxy_pool(pool_name)
        if not available_proxies:
            return None
        
        # Filter out failed proxies
        working_proxies = [p for p in available_proxies if self.proxy_failures.get(p, 0) < 3]
        if not working_proxies:
            working_proxies = available_proxies  # Reset if all failed
        
        # Select proxy based on rotation strategy
        if rotation_strategy == 'per_request':
            # Random selection for each request
            proxy = random.choice(working_proxies)
        elif rotation_strategy == 'per_page':
            # Round-robin per page
            page = request.meta.get('page', 1)
            proxy = working_proxies[page % len(working_proxies)]
        else:
            # Default round-robin
            proxy = working_proxies[self.current_index % len(working_proxies)]
            self.current_index += 1
        
        # Track usage
        self._track_proxy_usage(spider, proxy)
        return proxy
    
    def _track_proxy_usage(self, spider, proxy):
        """Track proxy usage statistics."""
        portal = getattr(spider, 'portal', getattr(spider, 'name', 'unknown'))
        if portal not in self.portal_stats:
            self.portal_stats[portal] = {'total_requests': 0, 'proxy_usage': {}}
        
        self.portal_stats[portal]['total_requests'] += 1
        if proxy not in self.portal_stats[portal]['proxy_usage']:
            self.portal_stats[portal]['proxy_usage'][proxy] = 0
        self.portal_stats[portal]['proxy_usage'][proxy] += 1
    
    def process_request(self, request, spider):
        """Set proxy for request based on portal configuration."""
        if not self.proxies and not self.proxy_config:
            return None
        
        proxy = self._select_proxy(spider, request)
        if proxy:
            request.meta['proxy'] = proxy
            request.meta['proxy_config'] = self._get_portal_config(spider)
            logger.debug(f"Using proxy {proxy} for {spider.name}")
        
        return None
    
    def process_response(self, request, response, spider):
        """Handle proxy failures and retries."""
        proxy = request.meta.get('proxy')
        if proxy and response.status in [403, 407, 429, 500, 502, 503, 504]:
            # Proxy failed, mark it
            self.proxy_failures[proxy] = self.proxy_failures.get(proxy, 0) + 1
            logger.warning(f"Proxy {proxy} failed for {spider.name}, status: {response.status}")
            
            # Check if we should retry with new proxy
            portal_config = self._get_portal_config(spider)
            if portal_config.get('retry_with_new_proxy', True):
                # Create retry request with new proxy
                retry_req = request.copy()
                retry_req.dont_filter = True
                retry_req.meta['proxy'] = self._select_proxy(spider, request)
                if retry_req.meta['proxy']:
                    logger.info(f"Retrying request with new proxy: {retry_req.meta['proxy']}")
                    return retry_req
        
        return response


class RetryWithBackoffMiddleware(RetryMiddleware):
    """Custom retry middleware with exponential backoff."""
    
    # Define exceptions that should trigger retries
    EXCEPTIONS_TO_RETRY = (IOError, OSError, ConnectionError, ConnectionRefusedError, 
                           ConnectionAbortedError, ConnectionResetError, TimeoutError)
    
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
