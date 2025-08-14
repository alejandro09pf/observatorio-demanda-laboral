"""
Test middleware functionality.
"""

import pytest
import os
from unittest.mock import patch, MagicMock, mock_open
from src.scraper.middlewares import (
    UserAgentRotationMiddleware,
    ProxyRotationMiddleware,
    RetryWithBackoffMiddleware
)


class TestUserAgentRotationMiddleware:
    """Test user agent rotation middleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return UserAgentRotationMiddleware()
    
    def test_default_user_agents(self, middleware):
        """Test that default user agents are loaded."""
        assert len(middleware.user_agents) > 0
        assert all(isinstance(ua, str) for ua in middleware.user_agents)
    
    @patch('builtins.open', new_callable=mock_open, read_data="UA1\nUA2\nUA3")
    @patch('os.path.exists', return_value=True)
    def test_load_user_agents_from_file(self, mock_exists, mock_file, middleware):
        """Test loading user agents from file."""
        # Recreate middleware to trigger file loading
        middleware = UserAgentRotationMiddleware()
        
        assert middleware.user_agents == ["UA1", "UA2", "UA3"]
    
    @patch('os.path.exists', return_value=False)
    def test_fallback_to_default_agents(self, mock_exists, middleware):
        """Test fallback to default agents when file doesn't exist."""
        # Recreate middleware to trigger fallback
        middleware = UserAgentRotationMiddleware()
        
        assert len(middleware.user_agents) > 0
        assert all("Mozilla" in ua for ua in middleware.user_agents)
    
    def test_round_robin_rotation(self, middleware):
        """Test round-robin user agent rotation."""
        middleware.rotation_strategy = 'round_robin'
        middleware.current_index = 0
        
        # Create mock request
        request = MagicMock()
        request.headers = {}
        
        # Process request
        middleware.process_request(request, MagicMock())
        
        # Verify user agent was set
        assert 'User-Agent' in request.headers
        assert request.headers['User-Agent'] == middleware.user_agents[0]
        
        # Process another request
        middleware.process_request(request, MagicMock())
        
        # Verify next user agent was used
        assert request.headers['User-Agent'] == middleware.user_agents[1]
    
    def test_random_rotation(self, middleware):
        """Test random user agent rotation."""
        middleware.rotation_strategy = 'random'
        
        # Create mock request
        request = MagicMock()
        request.headers = {}
        
        # Process request
        middleware.process_request(request, MagicMock())
        
        # Verify user agent was set
        assert 'User-Agent' in request.headers
        assert request.headers['User-Agent'] in middleware.user_agents


class TestProxyRotationMiddleware:
    """Test proxy rotation middleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        return ProxyRotationMiddleware()
    
    def test_no_proxies_configured(self, middleware):
        """Test behavior when no proxies are configured."""
        middleware.proxies = []
        
        # Create mock request
        request = MagicMock()
        request.meta = {}
        
        # Process request
        result = middleware.process_request(request, MagicMock())
        
        # Verify no proxy was set
        assert 'proxy' not in request.meta
        assert result is None
    
    def test_proxy_rotation(self, middleware):
        """Test proxy rotation."""
        middleware.proxies = ['http://proxy1:8080', 'http://proxy2:8080']
        middleware.rotation_strategy = 'round_robin'
        middleware.current_index = 0
        
        # Create mock request
        request = MagicMock()
        request.meta = {}
        
        # Process request
        middleware.process_request(request, MagicMock())
        
        # Verify proxy was set
        assert 'proxy' in request.meta
        assert request.meta['proxy'] == 'http://proxy1:8080'
        
        # Process another request
        middleware.process_request(request, MagicMock())
        
        # Verify next proxy was used
        assert request.meta['proxy'] == 'http://proxy2:8080'
    
    def test_proxy_loading_from_env(self, middleware):
        """Test loading proxies from environment variable."""
        proxy_pool = "http://proxy1:8080,http://proxy2:8080"
        
        with patch.dict(os.environ, {'PROXY_POOL': proxy_pool}):
            # Recreate middleware to trigger env loading
            middleware = ProxyRotationMiddleware()
            
            assert middleware.proxies == ['http://proxy1:8080', 'http://proxy2:8080']
    
    def test_proxy_authentication(self, middleware):
        """Test proxy with authentication."""
        middleware.proxies = ['http://user:pass@proxy1:8080']
        middleware.rotation_strategy = 'round_robin'
        middleware.current_index = 0
        
        # Create mock request
        request = MagicMock()
        request.meta = {}
        
        # Process request
        middleware.process_request(request, MagicMock())
        
        # Verify proxy with auth was set
        assert request.meta['proxy'] == 'http://user:pass@proxy1:8080'


class TestRetryWithBackoffMiddleware:
    """Test retry with backoff middleware."""
    
    @pytest.fixture
    def middleware(self):
        """Create middleware instance."""
        settings = MagicMock()
        settings.getint.return_value = 3
        settings.getlist.return_value = [500, 502, 503, 504, 408, 429]
        return RetryWithBackoffMiddleware(settings)
    
    def test_retry_http_codes(self, middleware):
        """Test that retry is triggered for specific HTTP codes."""
        # Create mock response with retryable status
        response = MagicMock()
        response.status = 429
        
        # Create mock request
        request = MagicMock()
        request.meta = {}
        
        # Process response
        result = middleware.process_response(request, response, MagicMock())
        
        # Verify retry was triggered
        assert result is not None
        assert hasattr(result, 'meta')
        assert result.meta.get('retry_times', 0) == 1
    
    def test_no_retry_for_success_status(self, middleware):
        """Test that retry is not triggered for successful status codes."""
        # Create mock response with success status
        response = MagicMock()
        response.status = 200
        
        # Create mock request
        request = MagicMock()
        request.meta = {}
        
        # Process response
        result = middleware.process_response(request, response, MagicMock())
        
        # Verify no retry was triggered
        assert result == response
    
    def test_max_retries_exceeded(self, middleware):
        """Test that retry stops after max attempts."""
        # Create mock response with retryable status
        response = MagicMock()
        response.status = 429
        
        # Create mock request with max retries already reached
        request = MagicMock()
        request.meta = {'retry_times': 3}
        
        # Process response
        result = middleware.process_response(request, response, MagicMock())
        
        # Verify no retry was triggered (max reached)
        assert result == response
    
    def test_exponential_backoff(self, middleware):
        """Test exponential backoff calculation."""
        # Create mock response with retryable status
        response = MagicMock()
        response.status = 429
        
        # Create mock request
        request = MagicMock()
        request.meta = {'retry_times': 1}
        
        # Process response
        result = middleware.process_response(request, response, MagicMock())
        
        # Verify retry was triggered with increased retry count
        assert result is not None
        assert result.meta.get('retry_times') == 2
