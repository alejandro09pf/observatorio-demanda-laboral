"""
Admin Router - Celery Version
Event-Driven system administration and scraping control using Celery workers.
"""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
import logging
from pathlib import Path
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.schemas.admin import (
    ScrapingConfig,
    ScrapingTask,
    ScrapingStatus,
    ScrapingStartResponse,
    ScrapingStatusResponse,
    AvailableSpidersResponse
)

# Import Celery tasks and app
try:
    from tasks.celery_app import celery_app
    from tasks.scraping_tasks import run_spider_task
    from tasks.extraction_tasks import extract_skills_task, process_pending_extractions
    from tasks.enhancement_tasks import enhance_job_task, process_pending_enhancements
    from tasks.clustering_tasks import run_clustering_task, analyze_cluster_task
    CELERY_AVAILABLE = True
except ImportError as e:
    CELERY_AVAILABLE = False
    logging.warning(f"Celery not available: {e}, some features will be disabled")

logger = logging.getLogger(__name__)

router = APIRouter()

# Available spiders and countries
AVAILABLE_SPIDERS = [
    'infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo',
    'zonajobs', 'magneto', 'occmundial', 'clarin', 'hiring_cafe', 'indeed'
]
SUPPORTED_COUNTRIES = ['CO', 'MX', 'AR', 'CL', 'PE', 'EC', 'PA', 'UY']


@router.get("/available", response_model=AvailableSpidersResponse)
def get_available_spiders():
    """
    Get list of available spiders and supported countries.
    """
    return AvailableSpidersResponse(
        spiders=AVAILABLE_SPIDERS,
        countries=SUPPORTED_COUNTRIES
    )


@router.post("/scraping/start", response_model=ScrapingStartResponse)
def start_scraping_celery(config: ScrapingConfig):
    """
    Start a new scraping task using Celery workers (Event-Driven approach).

    This endpoint:
    1. Validates the scraping configuration
    2. Enqueues tasks to Redis message queue
    3. Returns task IDs immediately (non-blocking)
    4. Workers process tasks asynchronously

    Args:
        config: Scraping configuration with spiders, countries, limits

    Returns:
        Task IDs and initial status

    Example:
        POST /api/admin/scraping/start
        {
            "spiders": ["computrabajo", "linkedin"],
            "countries": ["CO"],
            "max_jobs": 100,
            "max_pages": 5
        }

        Response:
        {
            "task_ids": ["abc123", "def456"],
            "message": "2 scraping tasks enqueued successfully",
            "status": "PENDING"
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available. Please start Celery workers first."
        )

    try:
        # Validate spiders
        invalid_spiders = [s for s in config.spiders if s not in AVAILABLE_SPIDERS]
        if invalid_spiders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid spiders: {invalid_spiders}. Available: {AVAILABLE_SPIDERS}"
            )

        # Validate countries
        invalid_countries = [c for c in config.countries if c not in SUPPORTED_COUNTRIES]
        if invalid_countries:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid countries: {invalid_countries}. Supported: {SUPPORTED_COUNTRIES}"
            )

        # Enqueue tasks to Celery (one task per spider-country combination)
        task_ids = []
        tasks_info = []

        for spider in config.spiders:
            for country in config.countries:
                # Enqueue task asynchronously
                task = run_spider_task.delay(
                    spider=spider,
                    country=country,
                    limit=config.max_jobs,
                    max_pages=config.max_pages
                )

                task_ids.append(task.id)
                tasks_info.append({
                    "task_id": task.id,
                    "spider": spider,
                    "country": country,
                    "status": "PENDING"
                })

                logger.info(f"📮 Enqueued scraping task: {spider} {country} (Task ID: {task.id})")

        return ScrapingStartResponse(
            task_ids=task_ids,
            message=f"{len(task_ids)} scraping task(s) enqueued successfully",
            status=ScrapingStatus.PENDING,
            tasks=tasks_info
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error enqueueing scraping tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enqueue tasks: {str(e)}")


@router.get("/scraping/status", response_model=ScrapingStatusResponse)
def get_scraping_status():
    """
    Get status of all active Celery scraping tasks.

    Returns:
        Summary of active, pending, and completed tasks

    This uses Celery's inspect API to query worker status.
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Inspect Celery workers
        inspect = celery_app.control.inspect()

        # Get active tasks (currently running)
        active_tasks = inspect.active() or {}

        # Get reserved tasks (queued but not started)
        reserved_tasks = inspect.reserved() or {}

        # Get scheduled tasks (scheduled for future)
        scheduled_tasks = inspect.scheduled() or {}

        # Flatten all tasks
        all_active = []
        for worker_name, tasks in active_tasks.items():
            for task in tasks:
                all_active.append({
                    "task_id": task['id'],
                    "name": task['name'],
                    "args": str(task['args']),
                    "worker": worker_name,
                    "status": "RUNNING"
                })

        all_reserved = []
        for worker_name, tasks in reserved_tasks.items():
            for task in tasks:
                all_reserved.append({
                    "task_id": task['id'],
                    "name": task['name'],
                    "args": str(task['args']),
                    "worker": worker_name,
                    "status": "PENDING"
                })

        # Check stats
        stats = inspect.stats() or {}
        total_workers = len(stats)

        return ScrapingStatusResponse(
            active_tasks=all_active,
            reserved_tasks=all_reserved,
            total_active=len(all_active),
            total_pending=len(all_reserved),
            workers_online=total_workers,
            system_status="operational" if total_workers > 0 else "no_workers"
        )

    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/scraping/task/{task_id}")
def get_task_status(task_id: str):
    """
    Get detailed status of a specific Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        Task status, progress, and result
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Get task result from Celery
        task_result = celery_app.AsyncResult(task_id)

        response = {
            "task_id": task_id,
            "status": task_result.state,
            "result": None,
            "error": None,
            "progress": 0
        }

        if task_result.state == 'PENDING':
            response['progress'] = 0
            response['result'] = "Task is waiting in queue"

        elif task_result.state == 'STARTED':
            response['progress'] = 10
            response['result'] = "Task has started"

        elif task_result.state == 'PROGRESS':
            # Task is reporting progress
            info = task_result.info
            response['progress'] = info.get('progress', 50)
            response['result'] = info.get('current', 'Processing...')

        elif task_result.state == 'SUCCESS':
            response['progress'] = 100
            response['result'] = task_result.result

        elif task_result.state == 'FAILURE':
            response['progress'] = 0
            response['error'] = str(task_result.info)
            response['result'] = "Task failed"

        elif task_result.state == 'RETRY':
            response['progress'] = 0
            response['result'] = f"Task is retrying... Attempt {task_result.info.get('retries', 1)}"

        return response

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@router.post("/scraping/stop/{task_id}")
def stop_scraping_task(task_id: str):
    """
    Stop a running Celery task.

    Args:
        task_id: Celery task ID

    Returns:
        Confirmation message

    Note: This sends a revoke signal to Celery. The task will be terminated.
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Revoke the task (terminate if already started)
        celery_app.control.revoke(task_id, terminate=True, signal='SIGKILL')

        logger.info(f"🛑 Revoked Celery task: {task_id}")

        return {
            "message": f"Task {task_id} has been stopped",
            "task_id": task_id
        }

    except Exception as e:
        logger.error(f"Error stopping task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop task: {str(e)}")


@router.get("/workers/stats")
def get_workers_stats():
    """
    Get statistics about Celery workers.

    Returns:
        Worker statistics including active workers, queues, throughput
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        inspect = celery_app.control.inspect()

        # Get stats from all workers
        stats = inspect.stats() or {}
        active_queues = inspect.active_queues() or {}
        registered_tasks = inspect.registered() or {}

        workers_info = []
        for worker_name, worker_stats in stats.items():
            workers_info.append({
                "name": worker_name,
                "pool": worker_stats.get('pool', {}).get('implementation', 'unknown'),
                "max_concurrency": worker_stats.get('pool', {}).get('max-concurrency', 0),
                "total_tasks": worker_stats.get('total', {}).items() if isinstance(worker_stats.get('total'), dict) else [],
                "queues": [q['name'] for q in active_queues.get(worker_name, [])],
                "registered_tasks": len(registered_tasks.get(worker_name, []))
            })

        return {
            "workers": workers_info,
            "total_workers": len(workers_info),
            "system_status": "operational" if len(workers_info) > 0 else "no_workers"
        }

    except Exception as e:
        logger.error(f"Error getting workers stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get workers stats: {str(e)}")


# Health check endpoint
@router.get("/health")
def health_check():
    """Check if Celery workers are responsive."""
    if not CELERY_AVAILABLE:
        return {
            "status": "error",
            "message": "Celery not installed",
            "workers": 0
        }

    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats() or {}

        return {
            "status": "healthy" if len(stats) > 0 else "no_workers",
            "message": f"{len(stats)} worker(s) online",
            "workers": len(stats),
            "celery_available": True
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "workers": 0
        }


@router.get("/schedule")
def get_celery_schedule():
    """
    Get Celery Beat schedule configuration.

    Returns:
        Scheduled tasks with their cron patterns and configurations

    Example:
        GET /api/admin/schedule

        Response:
        {
            "scraping_tasks": [...],
            "extraction_tasks": [...],
            "clustering_tasks": [...],
            "other_tasks": [...]
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery not available"
        )

    try:
        import re
        from datetime import datetime

        # Get beat schedule from Celery config
        schedule = celery_app.conf.beat_schedule if hasattr(celery_app.conf, 'beat_schedule') else {}

        def parse_crontab(crontab_str):
            """Parse crontab string to human readable format."""
            # Extract numbers from crontab string like "<crontab: 0 2 * * * (m/h/dM/MY/d)>"
            match = re.search(r'(\d+)\s+(\d+)\s+(\*|\d+)\s+(\*|\d+)\s+(\*|\d+)', crontab_str)
            if match:
                minute, hour, day, month, dow = match.groups()

                # Convert to human readable
                time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"

                if dow != '*':
                    days = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
                    return f"{days[int(dow)]} {time_str}"
                elif day != '*':
                    return f"Día {day} a las {time_str}"
                else:
                    return f"Diario a las {time_str}"
            return crontab_str

        scraping_tasks = []
        extraction_tasks = []
        clustering_tasks = []
        other_tasks = []

        for task_name, task_config in schedule.items():
            schedule_str = str(task_config.get('schedule', ''))
            parsed_schedule = parse_crontab(schedule_str)
            args = task_config.get('args', [])

            task_info = {
                'name': task_name,
                'schedule': parsed_schedule,
                'raw_schedule': schedule_str,
                'args': args
            }

            # Categorize tasks
            if 'scraping' in task_name:
                if len(args) >= 2:
                    task_info['spider'] = args[0]
                    task_info['country'] = args[1]
                    task_info['max_jobs'] = args[2] if len(args) > 2 else None
                scraping_tasks.append(task_info)
            elif 'extraction' in task_name or 'cleaning' in task_name or 'embeddings' in task_name:
                extraction_tasks.append(task_info)
            elif 'clustering' in task_name:
                if len(args) >= 1:
                    task_info['pipeline'] = args[0]
                    task_info['n_clusters'] = args[1] if len(args) > 1 else None
                clustering_tasks.append(task_info)
            else:
                other_tasks.append(task_info)

        return {
            "scraping_tasks": scraping_tasks,
            "extraction_tasks": extraction_tasks,
            "clustering_tasks": clustering_tasks,
            "other_tasks": other_tasks,
            "total_scheduled_tasks": len(schedule)
        }

    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schedule: {str(e)}")


# ==========================================
# EXTRACTION ENDPOINTS
# ==========================================

@router.post("/extraction/start")
def start_extraction_pending(limit: int = 100, country: str = None):
    """
    Start extraction for all pending jobs.

    This endpoint enqueues extraction tasks for jobs with extraction_status='pending'.

    Args:
        limit: Maximum number of jobs to process (default 100)
        country: Optional country filter (e.g., 'CO', 'MX')

    Returns:
        Task information and number of jobs enqueued

    Example:
        POST /api/admin/extraction/start?limit=50&country=CO

        Response:
        {
            "status": "success",
            "message": "50 extraction tasks enqueued",
            "jobs_enqueued": 50,
            "task_id": "abc123..."
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Enqueue the process_pending_extractions task
        task = process_pending_extractions.delay(limit=limit, country=country)

        logger.info(f"📮 Enqueued process_pending_extractions task: {task.id}")

        return {
            "status": "success",
            "message": f"Extraction task enqueued (limit={limit}, country={country})",
            "task_id": task.id,
            "limit": limit,
            "country": country
        }

    except Exception as e:
        logger.error(f"Error starting extraction: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start extraction: {str(e)}")


@router.post("/extraction/job/{job_id}")
def extract_single_job(job_id: str):
    """
    Extract skills from a single job posting.

    Args:
        job_id: UUID of the job to extract skills from

    Returns:
        Task information

    Example:
        POST /api/admin/extraction/job/123e4567-e89b-12d3-a456-426614174000

        Response:
        {
            "status": "success",
            "task_id": "abc123...",
            "job_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Enqueue extraction task for single job
        task = extract_skills_task.delay(job_id)

        logger.info(f"📮 Enqueued extraction task for job {job_id}: {task.id}")

        return {
            "status": "success",
            "message": f"Extraction task enqueued for job {job_id}",
            "task_id": task.id,
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Error extracting job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to extract job: {str(e)}")


@router.get("/extraction/stats")
def get_extraction_stats():
    """
    Get extraction statistics from database.

    Returns:
        Statistics about extraction status across all jobs

    Example:
        GET /api/admin/extraction/stats

        Response:
        {
            "total_jobs": 1000,
            "pending": 500,
            "completed": 450,
            "failed": 50,
            "total_skills_extracted": 12500
        }
    """
    try:
        import psycopg2
        import os

        # Connect directly to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Get extraction status counts
        cursor.execute("""
            SELECT
                COUNT(*) as total_jobs,
                SUM(CASE WHEN extraction_status = 'pending' THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN extraction_status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN extraction_status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM raw_jobs
        """)

        row = cursor.fetchone()
        total_jobs = row[0] or 0
        pending = row[1] or 0
        completed = row[2] or 0
        failed = row[3] or 0

        # Get total skills extracted
        cursor.execute("SELECT COUNT(*) FROM extracted_skills")
        total_skills = cursor.fetchone()[0] or 0

        cursor.close()
        conn.close()

        return {
            "total_jobs": total_jobs,
            "pending": pending,
            "completed": completed,
            "failed": failed,
            "total_skills_extracted": total_skills,
            "completion_rate": round(completed / total_jobs * 100, 2) if total_jobs > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting extraction stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ==========================================
# ENHANCEMENT ENDPOINTS
# ==========================================

@router.post("/enhancement/start")
def start_enhancement_pending(limit: int = 100):
    """
    Start enhancement for all extracted skills that haven't been enhanced yet.

    This endpoint enqueues enhancement tasks for skills without enhancement.

    Args:
        limit: Maximum number of skills to process (default 100)

    Returns:
        Task information and number of skills enqueued

    Example:
        POST /api/admin/enhancement/start?limit=50

        Response:
        {
            "status": "success",
            "message": "50 enhancement tasks enqueued",
            "task_id": "abc123..."
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Enqueue the process_pending_enhancements task
        task = process_pending_enhancements.delay(limit=limit)

        logger.info(f"📮 Enqueued process_pending_enhancements task: {task.id}")

        return {
            "status": "success",
            "message": f"Enhancement task enqueued (limit={limit})",
            "task_id": task.id,
            "limit": limit
        }

    except Exception as e:
        logger.error(f"Error starting enhancement: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start enhancement: {str(e)}")


@router.post("/enhancement/job/{job_id}")
def enhance_single_job(job_id: str):
    """
    Enhance all extracted skills from a single job.

    Args:
        job_id: UUID of the job to enhance

    Returns:
        Task information

    Example:
        POST /api/admin/enhancement/job/123e4567-e89b-12d3-a456-426614174000

        Response:
        {
            "status": "success",
            "task_id": "abc123...",
            "job_id": "123e4567-e89b-12d3-a456-426614174000"
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Enqueue enhancement task for single job
        task = enhance_job_task.delay(job_id)

        logger.info(f"📮 Enqueued enhancement task for job {job_id}: {task.id}")

        return {
            "status": "success",
            "message": f"Enhancement task enqueued for job {job_id}",
            "task_id": task.id,
            "job_id": job_id
        }

    except Exception as e:
        logger.error(f"Error enhancing job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to enhance job: {str(e)}")


@router.get("/enhancement/stats")
def get_enhancement_stats():
    """
    Get enhancement statistics from database.

    Returns:
        Statistics about enhancement status across all jobs

    Example:
        GET /api/admin/enhancement/stats

        Response:
        {
            "total_jobs_with_skills": 1000,
            "jobs_enhanced": 500,
            "jobs_pending_enhancement": 500,
            "total_enhanced_skills": 5000
        }
    """
    try:
        import psycopg2
        import os

        # Connect directly to database
        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Get total jobs with extracted skills
        cursor.execute("""
            SELECT COUNT(DISTINCT job_id) FROM extracted_skills
        """)
        total_jobs_with_skills = cursor.fetchone()[0] or 0

        # Get jobs with enhancements (jobs with enhanced_skills)
        cursor.execute("""
            SELECT COUNT(DISTINCT job_id) FROM enhanced_skills
        """)
        jobs_enhanced = cursor.fetchone()[0] or 0

        # Get total enhanced skills count
        cursor.execute("SELECT COUNT(*) FROM enhanced_skills")
        total_enhanced_skills = cursor.fetchone()[0] or 0

        # Get embeddings count
        cursor.execute("SELECT COUNT(*) FROM skill_embeddings")
        embeddings = cursor.fetchone()[0] or 0

        jobs_pending = total_jobs_with_skills - jobs_enhanced

        cursor.close()
        conn.close()

        return {
            "total_jobs_with_skills": total_jobs_with_skills,
            "jobs_enhanced": jobs_enhanced,
            "jobs_pending_enhancement": jobs_pending,
            "total_enhanced_skills": total_enhanced_skills,
            "total_embeddings": embeddings,
            "enhancement_rate": round(jobs_enhanced / total_jobs_with_skills * 100, 2) if total_jobs_with_skills > 0 else 0
        }

    except Exception as e:
        logger.error(f"Error getting enhancement stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


# ==========================================
# CLUSTERING ENDPOINTS
# ==========================================

@router.post("/clustering/run")
def run_clustering(
    pipeline_name: str,
    n_clusters: int = 50,
    country: str = None
):
    """
    Run clustering analysis on enhanced skills.

    Args:
        pipeline_name: Name of the clustering pipeline (e.g., 'pipeline_b_300_post')
        n_clusters: Number of clusters to generate (default 50)
        country: Optional country code filter (e.g., 'CO', 'MX')

    Returns:
        Task information

    Example:
        POST /api/admin/clustering/run?pipeline_name=pipeline_b_300_post&n_clusters=50&country=CO

        Response:
        {
            "status": "success",
            "task_id": "abc123...",
            "pipeline": "pipeline_b_300_post"
        }
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Celery workers not available"
        )

    try:
        # Enqueue clustering task
        task = run_clustering_task.delay(
            pipeline_name=pipeline_name,
            n_clusters=n_clusters,
            country_filter=country
        )

        logger.info(
            f"📮 Enqueued clustering task: {task.id} "
            f"(pipeline={pipeline_name}, n_clusters={n_clusters}, country={country})"
        )

        return {
            "status": "success",
            "message": f"Clustering task enqueued: {pipeline_name}",
            "task_id": task.id,
            "pipeline": pipeline_name,
            "n_clusters": n_clusters,
            "country_filter": country
        }

    except Exception as e:
        logger.error(f"Error starting clustering: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start clustering: {str(e)}")


@router.get("/clustering/results")
def get_clustering_results(limit: int = 10):
    """
    Get recent clustering analysis results.

    Args:
        limit: Number of results to return (default 10)

    Returns:
        List of clustering analyses

    Example:
        GET /api/admin/clustering/results?limit=5
    """
    try:
        import psycopg2
        import os

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                analysis_id,
                analysis_type,
                parameters,
                results,
                created_at
            FROM analysis_results
            WHERE analysis_type = 'clustering'
            ORDER BY created_at DESC
            LIMIT %s
        """, (limit,))

        results = []
        for row in cursor.fetchall():
            results.append({
                'analysis_id': str(row[0]),
                'analysis_type': row[1],
                'parameters': json.loads(row[2]) if row[2] else {},
                'results_summary': json.loads(row[3]) if row[3] else {},
                'created_at': row[4].isoformat() if row[4] else None
            })

        cursor.close()
        conn.close()

        return {
            'status': 'success',
            'count': len(results),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error getting clustering results: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")


@router.get("/clustering/stats")
def get_clustering_stats():
    """
    Get clustering statistics.

    Returns:
        Statistics about clustering analyses

    Example:
        GET /api/admin/clustering/stats
    """
    try:
        import psycopg2
        import os

        conn = psycopg2.connect(os.getenv('DATABASE_URL'))
        cursor = conn.cursor()

        # Count total analyses
        cursor.execute("""
            SELECT COUNT(*) FROM analysis_results WHERE analysis_type = 'clustering'
        """)
        total_analyses = cursor.fetchone()[0] or 0

        # Get most recent analysis
        cursor.execute("""
            SELECT created_at, parameters
            FROM analysis_results
            WHERE analysis_type = 'clustering'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        recent = cursor.fetchone()
        last_analysis = recent[0].isoformat() if recent and recent[0] else None
        last_params = json.loads(recent[1]) if recent and recent[1] else None

        cursor.close()
        conn.close()

        return {
            'total_clustering_analyses': total_analyses,
            'last_analysis_at': last_analysis,
            'last_analysis_params': last_params
        }

    except Exception as e:
        logger.error(f"Error getting clustering stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")
