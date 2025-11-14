"""
Celery Tasks for Web Scraping
Worker 1: Scraping tasks using Scrapy spiders
"""
import logging
import psycopg2
import os
from datetime import datetime
from celery import Task
from src.tasks.celery_app import celery_app
from src.orchestrator import run_single_spider
from src.events import publish_event

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def run_spider_task(
    self: Task,
    spider: str,
    country: str,
    limit: int = 100,
    max_pages: int = 5,
    multi_city: bool = False,
    listing_only: bool = False
) -> dict:
    """
    Execute a Scrapy spider for job scraping.

    This is an event-driven task that:
    1. Takes task from Redis queue
    2. Updates progress state
    3. Executes Scrapy spider
    4. Saves results to PostgreSQL
    5. Emits "JobsScraped" event (TODO: implement Pub/Sub)

    Args:
        spider: Spider name (e.g., 'computrabajo', 'linkedin')
        country: Country code (e.g., 'CO', 'MX', 'AR')
        limit: Maximum number of jobs to scrape
        max_pages: Maximum number of pages to crawl
        multi_city: Whether to scrape from multiple cities
        listing_only: Only scrape job listings, not details

    Returns:
        dict: Scraping results with statistics

    Raises:
        Exception: If scraping fails after retries
    """
    try:
        # Update task state: Starting
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Starting {spider} scraping for {country}...',
                'progress': 0,
                'spider': spider,
                'country': country
            }
        )

        logger.info(f"🕷️  Celery Worker: Starting scraping task - {spider} {country}")

        # Update task state: In progress
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Executing Scrapy spider {spider}...',
                'progress': 30,
                'spider': spider,
                'country': country
            }
        )

        # Execute the scraping using existing orchestrator function
        # This reuses all the proven scraping logic
        result = run_single_spider(
            spider=spider,
            country=country,
            limit=limit,
            max_pages=max_pages,
            multi_city=multi_city,
            listing_only=listing_only,
            verbose=False  # Don't print to console in workers
        )

        # Update task state: Completing
        self.update_state(
            state='PROGRESS',
            meta={
                'current': f'Scraping completed, saving results...',
                'progress': 90,
                'spider': spider,
                'country': country,
                'items_scraped': result.get('items_scraped', 0)
            }
        )

        logger.info(
            f"✅ Celery Worker: Scraping completed - "
            f"{result.get('items_scraped', 0)} jobs from {spider} {country}"
        )

        # Get recently scraped job_ids from database
        job_ids = []
        items_scraped = result.get('items_scraped', 0)

        if items_scraped > 0:
            try:
                conn = psycopg2.connect(os.getenv('DATABASE_URL'))
                cursor = conn.cursor()

                # Get most recent jobs that match this scraping session
                cursor.execute("""
                    SELECT job_id FROM raw_jobs
                    WHERE country = %s
                      AND scraped_at >= %s
                    ORDER BY scraped_at DESC
                    LIMIT %s
                """, (country, result.get('started_at'), items_scraped))

                job_ids = [str(row[0]) for row in cursor.fetchall()]

                cursor.close()
                conn.close()

            except Exception as exc:
                logger.error(f"Failed to fetch job_ids for event: {exc}")

        # Emit event to Redis Pub/Sub for auto-triggering extraction
        if job_ids:
            try:
                publish_event('jobs_scraped', {
                    'spider': spider,
                    'country': country,
                    'count': items_scraped,
                    'job_ids': job_ids,
                    'task_id': self.request.id
                })
                logger.info(f"📢 Event published: jobs_scraped with {len(job_ids)} job_ids")
            except Exception as exc:
                logger.error(f"Failed to publish jobs_scraped event: {exc}")

        # Return results
        return {
            'status': 'success',
            'spider': spider,
            'country': country,
            'jobs_scraped': items_scraped,
            'job_ids': job_ids,
            'started_at': result.get('started_at').isoformat() if result.get('started_at') else None,
            'ended_at': result.get('ended_at').isoformat() if result.get('ended_at') else None,
            'task_id': self.request.id,
            'progress': 100
        }

    except Exception as exc:
        # Log the error
        logger.error(f"❌ Celery Worker: Scraping failed - {spider} {country}: {str(exc)}")

        # Update task state: Failed
        self.update_state(
            state='FAILURE',
            meta={
                'current': f'Scraping failed: {str(exc)}',
                'progress': 0,
                'spider': spider,
                'country': country,
                'error': str(exc)
            }
        )

        # Retry the task with exponential backoff
        # Retry 1: after 60 seconds
        # Retry 2: after 120 seconds
        # Retry 3: after 180 seconds
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task
def scrape_multiple_countries(spider: str, countries: list[str], limit: int = 100, max_pages: int = 5) -> dict:
    """
    Scrape multiple countries in parallel using Celery group.

    This demonstrates distributed processing pattern.

    Args:
        spider: Spider name
        countries: List of country codes
        limit: Jobs per country
        max_pages: Pages per country

    Returns:
        dict: Aggregated results from all countries
    """
    from celery import group

    # Create a group of parallel scraping tasks
    job = group(
        run_spider_task.s(spider, country, limit, max_pages)
        for country in countries
    )

    # Execute tasks in parallel
    result = job.apply_async()

    # Wait for all tasks to complete
    results = result.get(timeout=3600)  # 1 hour timeout

    # Aggregate results
    total_jobs = sum(r.get('jobs_scraped', 0) for r in results if r)

    return {
        'status': 'success',
        'spider': spider,
        'countries': countries,
        'total_jobs_scraped': total_jobs,
        'results': results
    }


# Example usage:
# from src.tasks.scraping_tasks import run_spider_task
#
# # Enqueue task
# task = run_spider_task.delay('computrabajo', 'CO', 100, 5)
# print(f"Task ID: {task.id}")
#
# # Check status
# result = celery_app.AsyncResult(task.id)
# print(f"Status: {result.state}")
# print(f"Info: {result.info}")
#
# # Get result (blocking)
# final_result = task.get(timeout=3600)
# print(f"Result: {final_result}")
