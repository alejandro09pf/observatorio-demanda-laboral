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
AVAILABLE_SPIDERS = ['infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo', 'zonajobs', 'magneto', 'occmundial', 'clarin', 'hiring_cafe']
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
    max_pages: int = typer.Option(10, "--max-pages", "-p", help="Maximum pages to scrape per spider")
):
    """Run multiple spiders with specified parameters."""
    spider_list = [s.strip() for s in spiders.split(",")]
    spider_list = validate_spiders(spider_list)
    country = validate_country(country)
    
    logger.info(f"Starting scraping run for spiders: {spider_list} in {country}")
    
    results = {}
    for spider in spider_list:
        try:
            result = run_single_spider(spider, country, limit, max_pages)
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
    max_pages: int = typer.Option(5, "--max-pages", "-p", help="Maximum pages to scrape")
):
    """Run a single spider once."""
    validate_spiders([spider])
    country = validate_country(country)
    
    logger.info(f"Running single spider: {spider} for {country}")
    
    try:
        result = run_single_spider(spider, country, limit, max_pages)
        typer.echo(f" {spider} completed: {result.get('items_scraped', 0)} items scraped")
        return result
        
    except Exception as e:
        logger.error(f"Error running spider {spider}: {e}")
        typer.echo(f" {spider} failed: {e}")
        raise typer.Exit(1)


def run_single_spider(spider: str, country: str, limit: int, max_pages: int) -> dict:
    """Run a single spider and return results."""
    try:
        # Build scrapy command
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "-a", f"country={country}",
            "-a", f"limit={limit}",
            "-a", f"max_pages={max_pages}",
            "-L", "INFO"
        ]
        
        # Change to project root directory where scrapy.cfg is located
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Set PYTHONPATH to include src/
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_dir / "src")

        # Run scrapy command and capture output
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600,
            env=env,
            cwd=project_dir
        )

        
        if result.returncode != 0:
            logger.error(f"Scrapy command failed: {result.stderr}")
            raise Exception(f"Scrapy command failed: {result.stderr}")
        
        # Parse output to get item count from Scrapy stats and logs
        items_scraped = 0
        
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
        if items_scraped == 0:
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
        if items_scraped == 0:
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
        typer.echo(f"Database: ✅ Connected successfully")
        
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
        
        typer.echo("🚀 Starting Labor Market Observatory Automation System...")
        
        # Initialize master controller
        controller = MasterController()
        
        # Start the system
        if controller.start_system():
            typer.echo("✅ Automation system started successfully!")
            typer.echo("\nComponents running:")
            typer.echo("  - Intelligent Scheduler: ✅")
            typer.echo("  - Pipeline Automator: ✅")
            typer.echo("  - Health Monitoring: ✅")
            
            # Keep the process running
            typer.echo("\n🔄 System is now running automatically...")
            typer.echo("Press Ctrl+C to stop")
            
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                typer.echo("\n🛑 Stopping automation system...")
                controller.stop_system()
                typer.echo("✅ Automation system stopped")
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
        typer.echo(f"❌ Automation system not available: {e}")
    except Exception as e:
        typer.echo(f"❌ Error getting automation status: {e}")


@app.command()
def process_jobs(
    batch_size: int = typer.Option(10, "--batch-size", "-b", help="Number of jobs to process")
):
    """Manually process pending jobs through the pipeline."""
    try:
        from automation.master_controller import MasterController
        
        typer.echo(f"🔄 Processing {batch_size} jobs manually...")
        
        controller = MasterController()
        results = controller.process_jobs_manually(batch_size)
        
        if 'error' not in results:
            typer.echo(f"✅ Manual processing completed:")
            typer.echo(f"  Processed: {results.get('processed', 0)}")
            typer.echo(f"  Success: {results.get('success', 0)}")
            typer.echo(f"  Errors: {results.get('errors', 0)}")
            typer.echo(f"  Total Skills: {results.get('total_skills', 0)}")
            typer.echo(f"  ESCO Matches: {results.get('esco_matches', 0)}")
        else:
            typer.echo(f"❌ Manual processing failed: {results['error']}")
            
    except ImportError as e:
        typer.echo(f"❌ Automation system not available: {e}")
    except Exception as e:
        typer.echo(f"❌ Error processing jobs: {e}")


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
        typer.echo(f"\n📋 Scheduled Jobs ({len(jobs_info['scheduled_jobs'])}):")
        for job in jobs_info['scheduled_jobs']:
            status_emoji = "🟢" if job['status'] == 'pending' else "🟡" if job['status'] == 'running' else "🔴"
            typer.echo(f"  {status_emoji} {job['spider']} ({job['country']}) - {job['status']}")
            typer.echo(f"     Next Run: {job['next_run']}")
            typer.echo(f"     Last Run: {job['last_run'] or 'Never'}")
        
        # Running jobs
        if jobs_info['running_jobs']:
            typer.echo(f"\n🔄 Currently Running ({len(jobs_info['running_jobs'])}):")
            for job_id in jobs_info['running_jobs']:
                typer.echo(f"  🟡 {job_id}")
        
        # Recent history
        if jobs_info['recent_history']:
            typer.echo(f"\n📊 Recent Job History:")
            for job in jobs_info['recent_history'][-5:]:  # Last 5
                status_emoji = "✅" if job['status'] == 'success' else "❌"
                typer.echo(f"  {status_emoji} {job['spider']} ({job['country']}) - {job['status']}")
                
    except ImportError as e:
        typer.echo(f"❌ Automation system not available: {e}")
    except Exception as e:
        typer.echo(f"❌ Error listing jobs: {e}")


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
            typer.echo(f"✅ Job {job_id} started successfully")
        else:
            typer.echo(f"❌ Failed to start job {job_id}")
            
    except ImportError as e:
        typer.echo(f"❌ Automation system not available: {e}")
    except Exception as e:
        typer.echo(f"❌ Error force running job: {e}")


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
        typer.echo(f"\n📋 Scheduler Status:")
        typer.echo(f"  Running: {scheduler_status.get('scheduler', {}).get('is_running', False)}")
        typer.echo(f"  Total Jobs: {scheduler_status.get('scheduler', {}).get('total_jobs', 0)}")
        typer.echo(f"  Running Jobs: {scheduler_status.get('scheduler', {}).get('running_jobs', 0)}")
        typer.echo(f"  Max Concurrent: {scheduler_status.get('scheduler', {}).get('max_concurrent_jobs', 0)}")
        
        # Pipeline status
        pipeline_status = health_info['pipeline_status']
        typer.echo(f"\n🔄 Pipeline Status:")
        typer.echo(f"  Running: {pipeline_status.get('is_running', False)}")
        typer.echo(f"  Jobs Processed: {pipeline_status.get('jobs_processed', 0)}")
        typer.echo(f"  Jobs Failed: {pipeline_status.get('jobs_failed', 0)}")
        typer.echo(f"  Extraction Queue: {pipeline_status.get('queue_sizes', {}).get('extraction', 0)}")
        
    except ImportError as e:
        typer.echo(f"❌ Automation system not available: {e}")
    except Exception as e:
        typer.echo(f"❌ Error getting health metrics: {e}")


if __name__ == "__main__":
    app()
