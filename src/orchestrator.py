#!/usr/bin/env python3
"""
Labor Market Observatory - Main Orchestrator

Main command-line interface for controlling the entire data pipeline.
"""

import typer
from typing import Optional, List
import logging
import subprocess
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure .env is loaded from the correct location
def ensure_env_loaded():
    """Ensure .env file is loaded from the project root."""
    project_root = Path(__file__).parent.parent
    env_file = project_root / ".env"
    
    if env_file.exists() and not os.environ.get('DATABASE_URL'):
        # Load .env manually if not already loaded
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key not in os.environ:
                        os.environ[key] = value

# Load environment variables
ensure_env_loaded()

# Now add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import get_settings
from config.logging_config import setup_logging

def _parse_count_from_log(log_path: Path) -> int:
    """Parse item count from Scrapy log file."""
    try:
        if not log_path.exists():
            return 0
        # read last lines first to get the most recent run
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in reversed(lines):
            if "'item_scraped_count':" in line:
                try:
                    part = line.split("'item_scraped_count':", 1)[1]
                    count = part.split(",", 1)[0].strip().strip("}").strip()
                    return int(count)
                except Exception:
                    continue
    except Exception:
        pass
    return 0


def _guess_count_from_outputs(outputs_dir: Path, spider: str, started_at: datetime) -> int:
    """Guess item count from output files modified after the run started."""
    if not outputs_dir.exists():
        return 0

    # Prefer files that look related to the spider, else try any recent JSON
    patterns = [f"{spider}*.json", f"*{spider}*.json", "*.json"]
    candidates = []
    for pat in patterns:
        candidates.extend(outputs_dir.glob(pat))

    # Keep files modified after the run started (with a small slack)
    recent = []
    slack = 5.0  # seconds
    start_ts = started_at.timestamp() - slack
    for p in set(candidates):
        try:
            if p.stat().st_mtime >= start_ts:
                recent.append(p)
        except Exception:
            continue

    # newest first
    recent.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for path in recent:
        try:
            with open(path, "r", encoding="utf-8") as f:
                txt = f.read().strip()
            if not txt:
                continue
            # JSON array
            if txt.startswith("["):
                data = json.loads(txt)
                if isinstance(data, list):
                    return len(data)
            # NDJSON fallback
            return sum(1 for line in txt.splitlines() if line.strip())
        except Exception:
            continue

    return 0

# Initialize Typer app
app = typer.Typer(
    name="labor-observatory",
    help="Labor Market Observatory - Automated job market analysis system",
    add_completion=False
)

# Setup logging
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

# Available spiders
AVAILABLE_SPIDERS = ['infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo', 'zonajobs', 'magneto', 'occmundial', 'clarin', 'hiring_cafe', 'indeed']
SUPPORTED_COUNTRIES = ['CO', 'MX', 'AR', 'CL', 'PE', 'EC', 'PA', 'UY']


def validate_spiders(spiders: List[str]) -> List[str]:
    """Validate spider names."""
    invalid_spiders = [s for s in spiders if s not in AVAILABLE_SPIDERS]
    if invalid_spiders:
        raise typer.BadParameter(f"Invalid spiders: {invalid_spiders}. Available: {AVAILABLE_SPIDERS}")
    return spiders


def validate_country(country: str) -> str:
    """Validate country code."""
    if country not in SUPPORTED_COUNTRIES:
        raise typer.BadParameter(f"Invalid country: {country}. Supported: {SUPPORTED_COUNTRIES}")
    return country


@app.command()
def run(
    spiders: str = typer.Argument(..., help="Comma-separated list of spiders to run"),
    country: str = typer.Option("CO", "--country", "-c", help="Country code (CO, MX, AR, CL, PE, EC, PA, UY)"),
    limit: int = typer.Option(500, "--limit", "-l", help="Maximum number of jobs per spider"),
    max_pages: int = typer.Option(10, "--max-pages", "-p", help="Maximum pages to scrape per spider"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show real-time console output")
):
    """Run multiple spiders with specified parameters."""
    spider_list = [s.strip() for s in spiders.split(",")]
    spider_list = validate_spiders(spider_list)
    country = validate_country(country)
    
    logger.info(f"Starting scraping run for spiders: {spider_list} in {country}")
    
    results = {}
    for spider in spider_list:
        try:
            result = run_single_spider(spider, country, limit, max_pages, verbose)
            results[spider] = result
        except Exception as e:
            logger.error(f"Error running spider {spider}: {e}")
            results[spider] = {"error": str(e)}
    
    # Print summary
    typer.echo("\n" + "="*50)
    typer.echo("SCRAPING RUN SUMMARY")
    typer.echo("="*50)
    for spider, result in results.items():
        if "error" in result:
            typer.echo(f" {spider}: {result['error']}")
        else:
            typer.echo(f" {spider}: {result.get('items_scraped', 0)} items scraped")
    
    return results


@app.command()
def run_once(
    spider: str = typer.Argument(..., help="Spider name to run"),
    country: str = typer.Option("CO", "--country", "-c", help="Country code (CO, MX, AR, CL, PE, EC, PA, UY)"),
    limit: int = typer.Option(100, "--limit", "-l", help="Maximum number of jobs to scrape"),
    max_pages: int = typer.Option(5, "--max-pages", "-p", help="Maximum pages to scrape"),
    multi_city: bool = typer.Option(True, "--multi-city", "-m", help="Scrape multiple cities/locations (enabled by default for maximum coverage)"),
    listing_only: bool = typer.Option(False, "--listing-only", "-lo", help="Fast mode: only scrape listing pages (2x faster)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show real-time console output")
):
    """Run a single spider once."""
    validate_spiders([spider])
    country = validate_country(country)

    logger.info(f"Running single spider: {spider} for {country}")

    try:
        result = run_single_spider(spider, country, limit, max_pages, multi_city, listing_only, verbose)
        typer.echo(f" {spider} completed: {result.get('items_scraped', 0)} items scraped (see outputs/)")
        return result

    except Exception as e:
        logger.error(f"Error running spider {spider}: {e}")
        typer.echo(f" {spider} failed: {e}")
        raise typer.Exit(1)


def run_single_spider(spider: str, country: str, limit: int, max_pages: int, multi_city: bool = False, listing_only: bool = False, verbose: bool = False) -> dict:
    """Run a single spider and return results."""
    started_at = datetime.now()
    project_dir = Path(__file__).parent.parent

    # Special handling for hiring_cafe - use requests-based scraper instead of Scrapy
    if spider == "hiring_cafe":
        logger.info(f"Using requests-based scraper for hiring_cafe (bypasses bot detection)")
        try:
            # Run the requests-based scraper
            scraper_script = project_dir / "scripts" / "scrape_hiring_cafe_requests.py"

            # Use max_pages if provided, otherwise unlimited
            pages_arg = str(max_pages) if max_pages and max_pages > 0 else "unlimited"

            cmd = [sys.executable, str(scraper_script), country, pages_arg]

            if verbose:
                result = subprocess.run(cmd, cwd=project_dir, timeout=7200)  # 2 hour timeout
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_dir, timeout=7200)

            if result.returncode != 0:
                error_msg = result.stderr if hasattr(result, 'stderr') else "Unknown error"
                logger.error(f"hiring_cafe scraper failed: {error_msg}")
                raise Exception(f"hiring_cafe scraper failed: {error_msg}")

            # Parse output for statistics
            items_scraped = 0
            if not verbose and result.stdout:
                for line in result.stdout.split('\n'):
                    if "Jobs inserted:" in line:
                        try:
                            items_scraped = int(line.split("Jobs inserted:")[1].strip().split()[0])
                            break
                        except:
                            pass

            return {
                "spider": spider,
                "country": country,
                "items_scraped": items_scraped,
                "status": "success",
                "started_at": started_at,
                "ended_at": datetime.now()
            }

        except Exception as e:
            logger.error(f"Error running hiring_cafe scraper: {e}")
            raise

    # For all other spiders, use standard Scrapy approach
    try:
        # Build scrapy command with mass scraping settings
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "-a", f"country={country}",
            "-a", f"limit={limit}",
            "-a", f"max_pages={max_pages}",
            "-a", f"multi_city={'true' if multi_city else 'false'}",
            "-a", f"listing_only={'true' if listing_only else 'false'}",
            "-s", "SETTINGS_MODULE=src.scraper.mass_scraping_settings",
            "-L", "INFO"
        ]

        # Change to project root directory where scrapy.cfg is located
        os.chdir(project_dir)
        
        # Set PYTHONPATH to include src/
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_dir / "src")
        
        # Set orchestrator execution flags
        env["ORCHESTRATOR_EXECUTION"] = "1"
        env["SCRAPY_ORCHESTRATOR_RUN"] = "1"
        env["ORCHESTRATOR_MODE"] = "1"
        
        # Use mass scraping settings for better performance
        env["SCRAPY_SETTINGS_MODULE"] = "src.scraper.mass_scraping_settings"

        # Run scrapy command with conditional output capture
        if verbose:
            # Show real-time console output
            result = subprocess.run(
                cmd,
                env=env,
                cwd=project_dir,
                timeout=3600
            )
        else:
            # Capture output for parsing (original behavior)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600,
                env=env,
                cwd=project_dir
            )

        
        if result.returncode != 0:
            if verbose:
                logger.error(f"Scrapy command failed with return code: {result.returncode}")
                raise Exception(f"Scrapy command failed with return code: {result.returncode}")
            else:
                logger.error(f"Scrapy command failed: {result.stderr}")
                raise Exception(f"Scrapy command failed: {result.stderr}")
        
        # Parse output to get item count from Scrapy stats and logs
        items_scraped = 0
        
        if not verbose and result.stderr:
            # Look for Scrapy stats in stderr (Scrapy logs to stderr)
            for line in result.stderr.split('\n'):
                if "'item_scraped_count':" in line:
                    try:
                        # Extract the number from the stats line
                        count_str = line.split("'item_scraped_count':")[1].strip().split(',')[0]
                        items_scraped = int(count_str)
                        logger.info(f"Found item count in stats: {items_scraped}")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to parse item count from line: {line}, error: {e}")
                        pass
        
        # Look for Bumeran-specific indicators (Selenium-based spider)
        if items_scraped == 0 and not verbose and result.stderr:
            for line in result.stderr.split('\n'):
                if any(indicator in line for indicator in [
                    'Found job cards:', 
                    'Found actual job postings:',
                    'Getting job details:',
                    'total_jobs_scraped'
                ]):
                    if 'Found actual job postings:' in line:
                        try:
                            count_str = line.split('Found actual job postings:')[1].strip()
                            items_scraped = int(count_str)
                            logger.info(f"Found job count from Bumeran: {items_scraped}")
                            break
                        except:
                            pass
                    elif 'Getting job details:' in line:
                        items_scraped += 1
                    elif 'total_jobs_scraped' in line:
                        try:
                            count_str = line.split('total_jobs_scraped')[1].strip().split(':')[1].strip()
                            items_scraped = int(count_str)
                            logger.info(f"Found total jobs scraped: {items_scraped}")
                            break
                        except:
                            pass
        
        # Fallback: look for other general indicators
        if items_scraped == 0 and result.stderr:
            for line in result.stderr.split('\n'):
                if any(indicator in line for indicator in [
                    'Inserted new job:', 
                    'Progress:', 
                    'items_scraped'
                ]):
                    # Try to extract number from progress lines
                    if 'Progress:' in line and '/' in line:
                        try:
                            parts = line.split('Progress:')[1].strip().split('/')
                            if len(parts) == 2:
                                items_scraped = max(items_scraped, int(parts[1].split()[0]))
                        except:
                            pass
                    else:
                        items_scraped += 1
        
        # Existing parsing above may set items_scraped for non-verbose runs.
        # If we are verbose (no captured output) OR still at zero, try fallbacks.
        if verbose or items_scraped == 0:
            log_count = _parse_count_from_log(Path("logs") / "scrapy.log")
            if log_count:
                items_scraped = max(items_scraped, log_count)

            if items_scraped == 0:
                feed_count = _guess_count_from_outputs(Path("outputs"), spider, started_at)
                if feed_count:
                    items_scraped = feed_count
        
        return {
            "spider": spider,
            "country": country,
            "items_scraped": items_scraped,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Spider {spider} timed out after 1 hour")
        raise Exception("Spider execution timed out")
    except Exception as e:
        logger.error(f"Error running spider {spider}: {e}")
        raise


@app.command()
def schedule(
    action: str = typer.Argument(..., help="Action: start or stop"),
    config_file: str = typer.Option("config/schedule.yaml", "--config", "-c", help="Schedule configuration file")
):
    """Start or stop scheduled scraping jobs."""
    if action not in ["start", "stop"]:
        raise typer.BadParameter("Action must be 'start' or 'stop'")
    
    if action == "start":
        typer.echo("Starting scheduled scraping jobs...")
        # This would start the APScheduler process
        # For now, just run the schedule script
        try:
            subprocess.run([sys.executable, "scripts/run_schedule.py", "--config", config_file])
        except FileNotFoundError:
            typer.echo("Schedule script not found. Please create scripts/run_schedule.py")
    else:
        typer.echo("Stopping scheduled scraping jobs...")
        # This would stop the APScheduler process


@app.command()
def status():
    """Show system status and statistics."""
    logger.info("Checking system status")
    
    # Check database connection
    try:
        import psycopg2
        
        # Use unified configuration
        db_url = settings.database_url
        if db_url.startswith('postgresql://'):
            db_url = db_url.replace('postgresql://', 'postgres://')
        
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        
        # Get job counts by portal
        cursor.execute("""
            SELECT portal, COUNT(*) as count, 
                   MAX(scraped_at) as last_scraped
            FROM raw_jobs 
            GROUP BY portal
        """)
        
        results = cursor.fetchall()
        
        typer.echo("\n" + "="*50)
        typer.echo("SYSTEM STATUS")
        typer.echo("="*50)
        typer.echo(f"Database:  Connected successfully")
        
        if results:
            typer.echo("\nJob Statistics:")
            for portal, count, last_scraped in results:
                typer.echo(f"  {portal}: {count} jobs (last: {last_scraped})")
        else:
            typer.echo("\nNo jobs found in database")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        typer.echo(f" Database connection failed: {e}")


@app.command()
def list_spiders():
    """List all available spiders."""
    typer.echo("Available spiders:")
    for spider in AVAILABLE_SPIDERS:
        typer.echo(f"  - {spider}")


# ============================================================================
# NEW AUTOMATION COMMANDS - INTEGRATED WITH EXISTING FUNCTIONALITY
# ============================================================================

@app.command()
def start_automation():
    """Start the complete automation system (scheduler + pipeline + monitoring)."""
    try:
        from automation.master_controller import MasterController
        
        typer.echo(" Starting Labor Market Observatory Automation System...")
        
        # Initialize master controller
        controller = MasterController()
        
        # Start the system
        if controller.start_system():
            typer.echo(" Automation system started successfully!")
            typer.echo("\nComponents running:")
            typer.echo("  - Intelligent Scheduler: ")
            typer.echo("  - Pipeline Automator: ")
            typer.echo("  - Health Monitoring: ")
            
            # Keep the process running
            typer.echo("\n System is now running automatically...")
            typer.echo("Press Ctrl+C to stop")
            
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                typer.echo("\n🛑 Stopping automation system...")
                controller.stop_system()
                typer.echo(" Automation system stopped")
        else:
            typer.echo("❌ Failed to start automation system")
            
    except ImportError as e:
        typer.echo(f"❌ Automation system not available: {e}")
        typer.echo("Please ensure all automation components are properly installed")
    except Exception as e:
        typer.echo(f"❌ Error starting automation system: {e}")


@app.command()
def automation_status():
    """Show comprehensive automation system status."""
    try:
        from automation.master_controller import MasterController
        
        controller = MasterController()
        status = controller.get_comprehensive_status()
        
        typer.echo("\n" + "="*60)
        typer.echo("AUTOMATION SYSTEM STATUS")
        typer.echo("="*60)
        
        # System status
        system = status['system']
        typer.echo(f"System Status: {'🟢 Running' if system['is_running'] else '🔴 Stopped'}")
        typer.echo(f"Overall Health: {system['overall_health']}")
        typer.echo(f"Uptime: {system['uptime']}")
        typer.echo(f"Last Health Check: {system['last_health_check']}")
        
        # Component status
        components = status['components']
        typer.echo(f"\nComponent Status:")
        typer.echo(f"  Scheduler: {'🟢' if components['scheduler']['status'] == 'running' else '🔴'} {components['scheduler']['status']}")
        typer.echo(f"  Pipeline: {'🟢' if components['pipeline']['status'] == 'running' else '🔴'} {components['pipeline']['status']}")
        typer.echo(f"  Monitoring: {'🟢' if components['monitoring']['status'] == 'running' else '🔴'} {components['monitoring']['status']}")
        
        # Scheduler details
        scheduler_details = components['scheduler']['details']
        typer.echo(f"\nScheduler Details:")
        typer.echo(f"  Total Jobs: {scheduler_details['scheduler']['total_jobs']}")
        typer.echo(f"  Running Jobs: {scheduler_details['scheduler']['running_jobs']}")
        typer.echo(f"  Max Concurrent: {scheduler_details['scheduler']['max_concurrent_jobs']}")
        
        # Pipeline details
        pipeline_details = components['pipeline']['details']
        typer.echo(f"\nPipeline Details:")
        typer.echo(f"  Jobs Processed: {pipeline_details['jobs_processed']}")
        typer.echo(f"  Jobs Failed: {pipeline_details['jobs_failed']}")
        typer.echo(f"  Extraction Queue: {pipeline_details['queue_sizes']['extraction']}")
        
    except ImportError as e:
        typer.echo(f" Automation system not available: {e}")
    except Exception as e:
        typer.echo(f" Error getting automation status: {e}")


@app.command()
def process_jobs(
    batch_size: int = typer.Option(10, "--batch-size", "-b", help="Number of jobs to process")
):
    """Manually process pending jobs through the pipeline."""
    try:
        from automation.master_controller import MasterController
        
        typer.echo(f" Processing {batch_size} jobs manually...")
        
        controller = MasterController()
        results = controller.process_jobs_manually(batch_size)
        
        if 'error' not in results:
            typer.echo(f" Manual processing completed:")
            typer.echo(f"  Processed: {results.get('processed', 0)}")
            typer.echo(f"  Success: {results.get('success', 0)}")
            typer.echo(f"  Errors: {results.get('errors', 0)}")
            typer.echo(f"  Total Skills: {results.get('total_skills', 0)}")
            typer.echo(f"  ESCO Matches: {results.get('esco_matches', 0)}")
        else:
            typer.echo(f" Manual processing failed: {results['error']}")
            
    except ImportError as e:
        typer.echo(f" Automation system not available: {e}")
    except Exception as e:
        typer.echo(f" Error processing jobs: {e}")


@app.command()
def list_jobs():
    """List all scheduled jobs and their status."""
    try:
        from automation.master_controller import MasterController
        
        controller = MasterController()
        jobs_info = controller.list_all_jobs()
        
        typer.echo("\n" + "="*60)
        typer.echo("SCHEDULED JOBS STATUS")
        typer.echo("="*60)
        
        # Scheduled jobs
        typer.echo(f"\n Scheduled Jobs ({len(jobs_info['scheduled_jobs'])}):")
        for job in jobs_info['scheduled_jobs']:
            status_emoji = "🟢" if job['status'] == 'pending' else "🟡" if job['status'] == 'running' else "🔴"
            typer.echo(f"  {status_emoji} {job['spider']} ({job['country']}) - {job['status']}")
            typer.echo(f"     Next Run: {job['next_run']}")
            typer.echo(f"     Last Run: {job['last_run'] or 'Never'}")
        
        # Running jobs
        if jobs_info['running_jobs']:
            typer.echo(f"\n Currently Running ({len(jobs_info['running_jobs'])}):")
            for job_id in jobs_info['running_jobs']:
                typer.echo(f"   {job_id}")
        
        # Recent history
        if jobs_info['recent_history']:
            typer.echo(f"\n Recent Job History:")
            for job in jobs_info['recent_history'][-5:]:  # Last 5
                status_emoji = "1" if job['status'] == 'success' else "0"
                typer.echo(f"  {status_emoji} {job['spider']} ({job['country']}) - {job['status']}")
                
    except ImportError as e:
        typer.echo(f" Automation system not available: {e}")
    except Exception as e:
        typer.echo(f" Error listing jobs: {e}")


@app.command()
def force_job(
    job_id: str = typer.Argument(..., help="Job ID to force run")
):
    """Force run a specific scheduled job immediately."""
    try:
        from automation.master_controller import MasterController
        
        typer.echo(f"🔄 Force running job: {job_id}")
        
        controller = MasterController()
        if controller.force_run_job(job_id):
            typer.echo(f" Job {job_id} started successfully")
        else:
            typer.echo(f" Failed to start job {job_id}")
            
    except ImportError as e:
        typer.echo(f" Automation system not available: {e}")
    except Exception as e:
        typer.echo(f" Error force running job: {e}")


@app.command()
def health():
    """Show system health metrics."""
    try:
        from automation.master_controller import MasterController
        
        controller = MasterController()
        health_info = controller.get_system_health()
        
        typer.echo("\n" + "="*60)
        typer.echo("SYSTEM HEALTH METRICS")
        typer.echo("="*60)
        
        typer.echo(f"Overall Health: {health_info['overall_health']}")
        typer.echo(f"Last Check: {health_info['last_check']}")
        
        # Scheduler status
        scheduler_status = health_info['scheduler_status']
        typer.echo(f"\n Scheduler Status:")
        typer.echo(f"  Running: {scheduler_status.get('scheduler', {}).get('is_running', False)}")
        typer.echo(f"  Total Jobs: {scheduler_status.get('scheduler', {}).get('total_jobs', 0)}")
        typer.echo(f"  Running Jobs: {scheduler_status.get('scheduler', {}).get('running_jobs', 0)}")
        typer.echo(f"  Max Concurrent: {scheduler_status.get('scheduler', {}).get('max_concurrent_jobs', 0)}")
        
        # Pipeline status
        pipeline_status = health_info['pipeline_status']
        typer.echo(f"\n Pipeline Status:")
        typer.echo(f"  Running: {pipeline_status.get('is_running', False)}")
        typer.echo(f"  Jobs Processed: {pipeline_status.get('jobs_processed', 0)}")
        typer.echo(f"  Jobs Failed: {pipeline_status.get('jobs_failed', 0)}")
        typer.echo(f"  Extraction Queue: {pipeline_status.get('queue_sizes', {}).get('extraction', 0)}")
        
    except ImportError as e:
        typer.echo(f" Automation system not available: {e}")
    except Exception as e:
        typer.echo(f" Error getting health metrics: {e}")


@app.command()
def generate_embeddings(
    test: bool = typer.Option(False, "--test", help="Run in test mode (100 skills only)"),
    limit: int = typer.Option(100, "--limit", help="Number of skills in test mode")
):
    """Generate embeddings for all skills in esco_skills table."""
    import subprocess

    typer.echo("\n" + "="*60)
    typer.echo("PHASE 0 - STEP 0.1: GENERATE SKILL EMBEDDINGS")
    typer.echo("="*60)

    # Build command
    script_path = Path(__file__).parent.parent / "scripts" / "phase0_generate_embeddings.py"
    cmd = [sys.executable, str(script_path)]

    if test:
        cmd.append("--test")
        cmd.append(f"--limit={limit}")
        typer.echo(f" Running in TEST mode (limit={limit})")
    else:
        typer.echo(" Running in PRODUCTION mode (all skills)")

    typer.echo()

    # Run script
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            typer.echo("\n Embeddings generated successfully!")
        else:
            typer.echo(f"\n Failed to generate embeddings (exit code: {result.returncode})")
    except subprocess.CalledProcessError as e:
        typer.echo(f"\n Error generating embeddings: {e}")
        raise typer.Exit(code=1)


@app.command()
def build_faiss_index():
    """Build FAISS index from skill embeddings for fast semantic search."""
    import subprocess

    typer.echo("\n" + "="*60)
    typer.echo("PHASE 0 - STEP 0.2: BUILD FAISS INDEX")
    typer.echo("="*60)
    typer.echo()

    # Build command
    script_path = Path(__file__).parent.parent / "scripts" / "phase0_build_faiss_index.py"
    cmd = [sys.executable, str(script_path)]

    # Run script
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            typer.echo("\n FAISS index built successfully!")
        else:
            typer.echo(f"\n Failed to build FAISS index (exit code: {result.returncode})")
    except subprocess.CalledProcessError as e:
        typer.echo(f"\n Error building FAISS index: {e}")
        raise typer.Exit(code=1)


@app.command()
def test_embeddings(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output")
):
    """Run comprehensive tests on skill embeddings and FAISS index."""
    import subprocess

    typer.echo("\n" + "="*60)
    typer.echo("EMBEDDING QUALITY TESTS")
    typer.echo("="*60)
    typer.echo()

    # Build command
    script_path = Path(__file__).parent.parent / "scripts" / "test_embeddings.py"
    cmd = [sys.executable, str(script_path)]

    if verbose:
        cmd.append("--verbose")

    # Run script
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            typer.echo("\n All embedding tests passed!")
        else:
            typer.echo(f"\n Some tests failed (exit code: {result.returncode})")
    except subprocess.CalledProcessError as e:
        typer.echo(f"\n Error running embedding tests: {e}")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
