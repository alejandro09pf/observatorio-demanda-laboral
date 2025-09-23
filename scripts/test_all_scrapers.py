#!/usr/bin/env python3
"""
Test all scrapers to verify they work correctly and save data to PostgreSQL.
"""

import subprocess
import psycopg2
import json
import time
from datetime import datetime
from pathlib import Path

class ScraperTester:
    def __init__(self):
        self.results = {}
        self.initial_job_count = 0
        self.conn = None
        
    def connect_to_database(self):
        """Connect to PostgreSQL database."""
        try:
            self.conn = psycopg2.connect(
                host="localhost",
                port=5433,
                database="labor_observatory",
                user="labor_user",
                password="your_password"
            )
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            return False
    
    def get_job_count(self):
        """Get current job count in database."""
        if not self.conn:
            return 0
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM raw_jobs;")
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            print(f"❌ Error getting job count: {e}")
            return 0
    
    def get_jobs_by_portal(self, portal):
        """Get job count for specific portal."""
        if not self.conn:
            return 0
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM raw_jobs WHERE portal = %s;", (portal,))
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            print(f"❌ Error getting job count for {portal}: {e}")
            return 0
    
    def test_scraper(self, scraper_name, country="CO", limit=2):
        """Test a single scraper."""
        print(f"\n{'='*60}")
        print(f"🧪 Testing {scraper_name} scraper")
        print(f"{'='*60}")
        
        # Get initial job count
        initial_count = self.get_job_count()
        initial_portal_count = self.get_jobs_by_portal(scraper_name)
        
        print(f"📊 Initial job count: {initial_count}")
        print(f"📊 Initial {scraper_name} jobs: {initial_portal_count}")
        
        # Set environment variables
        env = {
            'DATABASE_URL': 'postgresql://labor_user:your_password@localhost:5433/labor_observatory',
            'SCRAPER_USER_AGENT': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'LLM_MODEL_PATH': './models/llama-2-7b-chat.gguf'
        }
        
        # Run scraper
        cmd = [
            'python', '-m', 'src.orchestrator', 'run-once', scraper_name,
            '--country', country, '--limit', str(limit), '--max-pages', '1', '--verbose'
        ]
        
        print(f"🚀 Running command: {' '.join(cmd)}")
        start_time = time.time()
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                env={**subprocess.os.environ, **env}
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"⏱️  Execution time: {duration:.2f} seconds")
            print(f"📤 Return code: {result.returncode}")
            
            # Check if scraper produced output
            output_file = f"outputs/{scraper_name}_real.json"
            output_exists = Path(output_file).exists()
            
            if output_exists:
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content and content.startswith('['):
                        try:
                            data = json.loads(content)
                            output_count = len(data) if isinstance(data, list) else 1
                        except:
                            output_count = 0
                    else:
                        output_count = 0
            else:
                output_count = 0
            
            print(f"📄 Output file exists: {output_exists}")
            print(f"📄 Output items: {output_count}")
            
            # Check database insertion
            final_count = self.get_job_count()
            final_portal_count = self.get_jobs_by_portal(scraper_name)
            
            jobs_inserted = final_count - initial_count
            portal_jobs_inserted = final_portal_count - initial_portal_count
            
            print(f"📊 Final job count: {final_count}")
            print(f"📊 Final {scraper_name} jobs: {final_portal_count}")
            print(f"📊 Jobs inserted: {jobs_inserted}")
            print(f"📊 {scraper_name} jobs inserted: {portal_jobs_inserted}")
            
            # Analyze logs
            success_indicators = [
                "Connected to PostgreSQL database" in result.stdout,
                "Inserted new job" in result.stdout,
                "item_scraped_count" in result.stdout,
                jobs_inserted > 0
            ]
            
            success_count = sum(success_indicators)
            
            # Determine status
            if success_count >= 3 and jobs_inserted > 0:
                status = "✅ FUNCTIONAL"
            elif success_count >= 2:
                status = "⚠️  PARTIAL"
            else:
                status = "❌ FAILING"
            
            print(f"🎯 Status: {status}")
            
            # Store results
            self.results[scraper_name] = {
                "status": status,
                "return_code": result.returncode,
                "duration": duration,
                "output_file_exists": output_exists,
                "output_items": output_count,
                "jobs_inserted": jobs_inserted,
                "portal_jobs_inserted": portal_jobs_inserted,
                "success_indicators": success_count,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "timestamp": datetime.now().isoformat()
            }
            
            return status == "✅ FUNCTIONAL"
            
        except subprocess.TimeoutExpired:
            print(f"⏰ Scraper timed out after 10 minutes")
            self.results[scraper_name] = {
                "status": "❌ TIMEOUT",
                "return_code": -1,
                "duration": 600,
                "output_file_exists": False,
                "output_items": 0,
                "jobs_inserted": 0,
                "portal_jobs_inserted": 0,
                "success_indicators": 0,
                "stdout": "",
                "stderr": "Timeout after 10 minutes",
                "timestamp": datetime.now().isoformat()
            }
            return False
            
        except Exception as e:
            print(f"❌ Error running scraper: {e}")
            self.results[scraper_name] = {
                "status": "❌ ERROR",
                "return_code": -1,
                "duration": 0,
                "output_file_exists": False,
                "output_items": 0,
                "jobs_inserted": 0,
                "portal_jobs_inserted": 0,
                "success_indicators": 0,
                "stdout": "",
                "stderr": str(e),
                "timestamp": datetime.now().isoformat()
            }
            return False
    
    def run_all_tests(self):
        """Run tests for all scrapers."""
        print("🚀 Starting comprehensive scraper testing...")
        
        if not self.connect_to_database():
            print("❌ Cannot connect to database. Aborting tests.")
            return
        
        self.initial_job_count = self.get_job_count()
        print(f"📊 Initial total job count: {self.initial_job_count}")
        
        # Define scrapers to test with their preferred countries
        scrapers_to_test = [
            ("computrabajo", "CO"),
            ("elempleo", "CO"), 
            ("bumeran", "MX"),
            ("occmundial", "MX"),
            ("magneto", "CO"),
            ("indeed", "MX"),
            ("zonajobs", "CO"),
            ("hiring_cafe", "CO")
        ]
        
        functional_count = 0
        total_count = len(scrapers_to_test)
        
        for scraper_name, country in scrapers_to_test:
            try:
                if self.test_scraper(scraper_name, country):
                    functional_count += 1
            except KeyboardInterrupt:
                print("\n⚠️  Testing interrupted by user")
                break
            except Exception as e:
                print(f"❌ Unexpected error testing {scraper_name}: {e}")
        
        # Generate summary
        print(f"\n{'='*60}")
        print(f"📊 TESTING SUMMARY")
        print(f"{'='*60}")
        print(f"✅ Functional scrapers: {functional_count}/{total_count}")
        print(f"❌ Failing scrapers: {total_count - functional_count}/{total_count}")
        
        # Save detailed results
        with open("scraper_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"📄 Detailed results saved to: scraper_test_results.json")
        
        # Close database connection
        if self.conn:
            self.conn.close()
        
        return functional_count, total_count

if __name__ == "__main__":
    tester = ScraperTester()
    functional, total = tester.run_all_tests()
    
    if functional == total:
        print(f"\n🎉 All {total} scrapers are functional!")
    else:
        print(f"\n⚠️  {total - functional} scrapers need attention.")
