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
AVAILABLE_SPIDERS = ['infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo', 'zonajobs', 'magneto', 'occmundial', 'clarin']
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
    # Build scrapy command
    cmd = [
        sys.executable, "-m", "scrapy", "crawl", spider,
        "-a", f"country={country}",
        "-a", f"max_pages={max_pages}",
        "-s", f"CLOSESPIDER_ITEMCOUNT={limit}",
        "-L", "INFO"
    ]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    
    try:
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
        
        if result.returncode != 0:
            logger.error(f"Scrapy command failed: {result.stderr}")
            raise Exception(f"Scrapy command failed: {result.stderr}")
        
        # Parse output to get item count
        items_scraped = 0
        for line in result.stdout.split('\n'):
            if 'Inserted new job:' in line:
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
        from src.scraper.settings import DB_PARAMS
        
        conn = psycopg2.connect(**DB_PARAMS)
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
        typer.echo(f"Database:  Connected to {DB_PARAMS['database']}")
        
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

if __name__ == "__main__":
    app()
