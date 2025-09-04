#!/usr/bin/env python3
"""
Proxy Testing Script for Labor Market Observatory
Tests proxy connectivity and finds working proxies
"""

import requests
import time
import concurrent.futures
from typing import List, Dict, Tuple
import json
import os

class ProxyTester:
    def __init__(self):
        self.test_url = "http://httpbin.org/ip"
        self.timeout = 10
        self.working_proxies = []
        self.failed_proxies = []
        
    def test_proxy(self, proxy: str) -> Tuple[str, bool, float, str]:
        """Test a single proxy and return results."""
        start_time = time.time()
        try:
            response = requests.get(
                self.test_url,
                proxies={'http': proxy, 'https': proxy},
                timeout=self.timeout
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                return proxy, True, elapsed, "Success"
            else:
                return proxy, False, elapsed, f"HTTP {response.status_code}"
                
        except requests.exceptions.Timeout:
            elapsed = time.time() - start_time
            return proxy, False, elapsed, "Timeout"
        except requests.exceptions.ProxyError:
            elapsed = time.time() - start_time
            return proxy, False, elapsed, "Proxy Error"
        except Exception as e:
            elapsed = time.time() - start_time
            return proxy, False, elapsed, str(e)
    
    def test_proxy_list(self, proxies: List[str], max_workers: int = 10) -> Dict:
        """Test multiple proxies concurrently."""
        print(f"🔍 Testing {len(proxies)} proxies...")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_proxy = {executor.submit(self.test_proxy, proxy): proxy for proxy in proxies}
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy, success, elapsed, message = future.result()
                
                if success:
                    self.working_proxies.append({
                        'proxy': proxy,
                        'response_time': elapsed,
                        'status': message
                    })
                    print(f"✅ {proxy} - {elapsed:.2f}s")
                else:
                    self.failed_proxies.append({
                        'proxy': proxy,
                        'response_time': elapsed,
                        'error': message
                    })
                    print(f"❌ {proxy} - {message}")
        
        return {
            'working': self.working_proxies,
            'failed': self.failed_proxies,
            'total_tested': len(proxies),
            'working_count': len(self.working_proxies),
            'failed_count': len(self.failed_proxies)
        }
    
    def find_free_proxies(self) -> List[str]:
        """Find free proxies from various sources."""
        proxies = []
        
        # Source 1: Free proxy lists from multiple sources
        proxy_sources = [
            "https://api.proxyscrape.com/v2/?request=get&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt"
        ]
        
        for source in proxy_sources:
            try:
                response = requests.get(source, timeout=10)
                if response.status_code == 200:
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if ':' in line:
                            parts = line.split(':')
                            if len(parts) == 2:
                                ip, port = parts[0], parts[1]
                                if ip.replace('.', '').isdigit() and port.isdigit():
                                    proxies.append(f"http://{ip}:{port}")
            except:
                continue
        
        # Source 2: Known working free proxies (updated list)
        known_working = [
            "http://185.199.229.156:7492",
            "http://185.199.228.220:7492", 
            "http://185.199.231.45:7492",
            "http://185.199.230.102:7492",
            "http://185.199.231.45:7492",
            "http://103.149.162.194:80",
            "http://103.149.162.195:80",
            "http://103.149.162.196:80",
            "http://103.149.162.197:80",
            "http://103.149.162.198:80"
        ]
        
        proxies.extend(known_working)
        return list(set(proxies))  # Remove duplicates
    
    def save_working_proxies(self, filename: str = "working_proxies.json"):
        """Save working proxies to JSON file."""
        if self.working_proxies:
            data = {
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'working_proxies': self.working_proxies,
                'stats': {
                    'total_working': len(self.working_proxies),
                    'total_failed': len(self.failed_proxies)
                }
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"💾 Working proxies saved to {filename}")
    
    def generate_yaml_config(self, filename: str = "working_proxies.yaml"):
        """Generate YAML configuration for working proxies."""
        if not self.working_proxies:
            print("❌ No working proxies to save")
            return
        
        yaml_content = """# Working Proxy Configuration (Auto-generated)
# Generated on: {timestamp}

proxy_pools:
  working:
    description: "Tested and working proxies"
    proxies:
""".format(timestamp=time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Sort by response time (fastest first)
        sorted_proxies = sorted(self.working_proxies, key=lambda x: x['response_time'])
        
        for proxy_info in sorted_proxies:
            yaml_content += f"      - {proxy_info['proxy']}  # {proxy_info['response_time']:.2f}s\n"
        
        yaml_content += """    rotation_strategy: "per_request"
    retry_with_new_proxy: true
    max_failures: 3

portal_config:
  elempleo:
    description: "JS-heavy site, requires working proxies"
    pool: "working"
    rotation_strategy: "per_request"
    retry_with_new_proxy: true
    timeout: 30
    max_retries: 3
  
  bumeran:
    description: "Selenium-based, working proxies sufficient"
    pool: "working"
    rotation_strategy: "per_page"
    retry_with_new_proxy: true
    timeout: 20
    max_retries: 2
  
  computrabajo:
    description: "Standard Scrapy site, working proxies sufficient"
    pool: "working"
    rotation_strategy: "per_request"
    retry_with_new_proxy: true
    timeout: 15
    max_retries: 2

global_settings:
  default_pool: "working"
  default_rotation: "per_request"
  default_timeout: 20
  default_max_retries: 3
  health_check_interval: 300
  proxy_failure_threshold: 5
  automatic_fallback: true
  log_proxy_usage: true
"""
        
        with open(filename, 'w') as f:
            f.write(yaml_content)
        
        print(f"📝 YAML configuration generated: {filename}")

def main():
    """Main function to test proxies."""
    print("🚀 Proxy Testing Script for Labor Market Observatory")
    print("=" * 60)
    
    tester = ProxyTester()
    
    # Find free proxies
    print("🔍 Finding free proxies...")
    proxies = tester.find_free_proxies()
    print(f"📊 Found {len(proxies)} proxies to test")
    
    if not proxies:
        print("❌ No proxies found")
        return
    
    # Test proxies
    results = tester.test_proxy_list(proxies)
    
    # Display results
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"✅ Working: {results['working_count']}")
    print(f"❌ Failed: {results['failed_count']}")
    print(f"📈 Success Rate: {(results['working_count'] / results['total_tested']) * 100:.1f}%")
    
    if results['working_count'] > 0:
        print(f"\n🏆 Fastest Proxy: {min(tester.working_proxies, key=lambda x: x['response_time'])['proxy']}")
        print(f"⏱️  Average Response Time: {sum(p['response_time'] for p in tester.working_proxies) / len(tester.working_proxies):.2f}s")
        
        # Save results
        tester.save_working_proxies()
        tester.generate_yaml_config()
        
        print(f"\n💡 To use these proxies, copy the contents of 'working_proxies.yaml' to 'config/proxies.yaml'")
    else:
        print("\n❌ No working proxies found. Consider:")
        print("   - Using a paid proxy service")
        print("   - Checking your internet connection")
        print("   - Running the script again later")

if __name__ == "__main__":
    main()
