#!/usr/bin/env python3
"""
Scheduled scraping runner using APScheduler.
"""

import argparse
import yaml
import logging
import sys
from pathlib import Path
from datetime import datetime
import subprocess
import signal
import time
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from config.settings import get_settings
from config.logging_config import setup_logging

# Setup logging
settings = get_settings()
setup_logging(settings.log_level, settings.log_file)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def load_schedule_config(config_file: str) -> dict:
    """Load schedule configuration from YAML file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        logger.info(f"Loaded schedule configuration from {config_file}")
        return config
    except Exception as e:
        logger.error(f"Failed to load schedule configuration: {e}")
        raise


def run_spider_job(spider: str, country: str, **kwargs):
    """Run a single spider job."""
    logger.info(f"Running scheduled job: {spider} for {country}")
    
    try:
        # Build scrapy command
        cmd = [
            sys.executable, "-m", "scrapy", "crawl", spider,
            "-a", f"country={country}",
            "-L", "INFO"
        ]
        
        # Add optional parameters
        for key, value in kwargs.items():
            if value is not None:
                cmd.extend(["-a", f"{key}={value}"])
        
        # Change to project directory
        project_dir = Path(__file__).parent.parent
        os.chdir(project_dir)
        
        # Run scrapy command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            logger.info(f"✅ Scheduled job {spider} completed successfully")
        else:
            logger.error(f"❌ Scheduled job {spider} failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.error(f"❌ Scheduled job {spider} timed out after 1 hour")
    except Exception as e:
        logger.error(f"❌ Error running scheduled job {spider}: {e}")


def setup_scheduler(config: dict):
    """Setup APScheduler with jobs from configuration."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger
        from apscheduler.triggers.interval import IntervalTrigger
        
        global scheduler
        scheduler = BackgroundScheduler()
        
        jobs = config.get('jobs', [])
        
        for job_config in jobs:
            spider = job_config['spider']
            country = job_config['country']
            trigger_type = job_config['trigger']
            
            # Create job function with parameters
            job_func = lambda s=spider, c=country, **kwargs: run_spider_job(s, c, **kwargs)
            
            if trigger_type == 'cron':
                cron_expr = job_config['cron']
                trigger = CronTrigger.from_crontab(cron_expr)
                scheduler.add_job(
                    job_func,
                    trigger=trigger,
                    id=f"{spider}_{country}_cron",
                    name=f"{spider} {country} (cron: {cron_expr})"
                )
                logger.info(f"Added cron job: {spider} {country} - {cron_expr}")
                
            elif trigger_type == 'interval':
                if 'every_minutes' in job_config:
                    trigger = IntervalTrigger(minutes=job_config['every_minutes'])
                    logger.info(f"Added interval job: {spider} {country} - every {job_config['every_minutes']} minutes")
                elif 'every_hours' in job_config:
                    trigger = IntervalTrigger(hours=job_config['every_hours'])
                    logger.info(f"Added interval job: {spider} {country} - every {job_config['every_hours']} hours")
                else:
                    logger.warning(f"Invalid interval configuration for {spider}")
                    continue
                
                scheduler.add_job(
                    job_func,
                    trigger=trigger,
                    id=f"{spider}_{country}_interval",
                    name=f"{spider} {country} (interval)"
                )
        
        return scheduler
        
    except ImportError:
        logger.error("APScheduler not installed. Please install it with: pip install apscheduler")
        raise
    except Exception as e:
        logger.error(f"Failed to setup scheduler: {e}")
        raise


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info("Received shutdown signal, stopping scheduler...")
    if scheduler:
        scheduler.shutdown()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Run scheduled scraping jobs")
    parser.add_argument("--config", "-c", default="config/schedule.yaml", 
                       help="Schedule configuration file")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Show what jobs would be scheduled without running them")
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_schedule_config(args.config)
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    if args.dry_run:
        logger.info("DRY RUN - Would schedule the following jobs:")
        jobs = config.get('jobs', [])
        for job in jobs:
            logger.info(f"  - {job['spider']} {job['country']} ({job['trigger']})")
        return
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Setup scheduler
    try:
        scheduler = setup_scheduler(config)
        scheduler.start()
        logger.info("Scheduler started successfully")
        
        # Keep the script running
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down...")
            scheduler.shutdown()
            
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
