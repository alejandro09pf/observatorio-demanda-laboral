"""
Admin Router - System administration and scraping control.
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List, Dict, Any
import logging
import subprocess
import psutil
import json
from pathlib import Path
from datetime import datetime
import uuid

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

logger = logging.getLogger(__name__)

router = APIRouter()

# File to track running tasks
TASKS_FILE = Path(__file__).parent.parent.parent.parent / "data" / "active_tasks.json"
TASKS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Available spiders and countries (from orchestrator.py)
AVAILABLE_SPIDERS = [
    'infojobs', 'elempleo', 'bumeran', 'lego', 'computrabajo',
    'zonajobs', 'magneto', 'occmundial', 'clarin', 'hiring_cafe', 'indeed'
]
SUPPORTED_COUNTRIES = ['CO', 'MX', 'AR', 'CL', 'PE', 'EC', 'PA', 'UY']


def load_tasks() -> Dict[str, Any]:
    """Load active tasks from file."""
    if TASKS_FILE.exists():
        try:
            with open(TASKS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tasks: {e}")
    return {}


def save_tasks(tasks: Dict[str, Any]):
    """Save active tasks to file."""
    try:
        with open(TASKS_FILE, 'w') as f:
            json.dump(tasks, f, indent=2, default=str)
    except Exception as e:
        logger.error(f"Error saving tasks: {e}")


def is_process_running(pid: int) -> bool:
    """Check if a process is still running."""
    try:
        process = psutil.Process(pid)
        return process.is_running() and process.status() != psutil.STATUS_ZOMBIE
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


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
def start_scraping(config: ScrapingConfig, background_tasks: BackgroundTasks):
    """
    Start a new scraping task.

    Args:
        config: Scraping configuration (spiders, country, limits)

    Returns:
        Task ID and status
    """
    try:
        # Validate spiders
        invalid_spiders = [s for s in config.spiders if s not in AVAILABLE_SPIDERS]
        if invalid_spiders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid spiders: {invalid_spiders}. Available: {AVAILABLE_SPIDERS}"
            )

        # Validate country
        if config.country not in SUPPORTED_COUNTRIES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid country: {config.country}. Supported: {SUPPORTED_COUNTRIES}"
            )

        # Generate task ID
        task_id = str(uuid.uuid4())[:8]

        # Build command
        project_root = Path(__file__).parent.parent.parent.parent
        spiders_str = ",".join(config.spiders)

        # Create log file
        log_dir = project_root / "logs" / "scraping"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"scraping_{task_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Command to execute
        cmd = [
            "python", "-m", "src.orchestrator",
            "run",
            spiders_str,
            "--country", config.country,
            "--limit", str(config.limit),
            "--max-pages", str(config.max_pages)
        ]

        logger.info(f"Starting scraping task {task_id}: {' '.join(cmd)}")

        # Execute in background
        process = subprocess.Popen(
            cmd,
            cwd=str(project_root),
            stdout=open(log_file, 'w'),
            stderr=subprocess.STDOUT,
            preexec_fn=None if sys.platform == 'win32' else lambda: None
        )

        # Save task info
        tasks = load_tasks()
        tasks[task_id] = {
            "task_id": task_id,
            "config": config.dict(),
            "status": ScrapingStatus.RUNNING.value,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "pid": process.pid,
            "jobs_scraped": 0,
            "errors": 0,
            "log_file": str(log_file)
        }
        save_tasks(tasks)

        return ScrapingStartResponse(
            task_id=task_id,
            status=ScrapingStatus.RUNNING,
            message=f"Scraping started successfully. PID: {process.pid}",
            config=config
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting scraping: {e}")
        raise HTTPException(status_code=500, detail=f"Error starting scraping: {str(e)}")


@router.get("/scraping/status", response_model=ScrapingStatusResponse)
def get_scraping_status():
    """
    Get status of all scraping tasks.

    Returns:
        Active tasks and system status
    """
    try:
        tasks = load_tasks()
        active_tasks = []

        # Check each task
        for task_id, task_data in list(tasks.items()):
            pid = task_data.get('pid')

            # Update status based on process
            if pid and is_process_running(pid):
                task_data['status'] = ScrapingStatus.RUNNING.value
            elif task_data['status'] == ScrapingStatus.RUNNING.value:
                # Was running but now stopped
                task_data['status'] = ScrapingStatus.COMPLETED.value
                task_data['completed_at'] = datetime.now().isoformat()

            # Convert to ScrapingTask
            try:
                active_tasks.append(ScrapingTask(**task_data))
            except Exception as e:
                logger.error(f"Error parsing task {task_id}: {e}")

        # Save updated tasks
        save_tasks({t.task_id: t.dict() for t in active_tasks})

        # Filter only running/pending tasks
        active_only = [t for t in active_tasks if t.status in [ScrapingStatus.RUNNING, ScrapingStatus.PENDING]]

        return ScrapingStatusResponse(
            active_tasks=active_only,
            total_active=len(active_only),
            system_status="operational"
        )

    except Exception as e:
        logger.error(f"Error getting scraping status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scraping/stop/{task_id}")
def stop_scraping(task_id: str):
    """
    Stop a running scraping task.

    Args:
        task_id: Task ID to stop

    Returns:
        Confirmation message
    """
    try:
        tasks = load_tasks()

        if task_id not in tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = tasks[task_id]
        pid = task.get('pid')

        if not pid:
            raise HTTPException(status_code=400, detail="Task has no associated process")

        if not is_process_running(pid):
            task['status'] = ScrapingStatus.STOPPED.value
            save_tasks(tasks)
            return {"message": f"Task {task_id} was already stopped", "status": "stopped"}

        # Kill process
        try:
            process = psutil.Process(pid)
            process.terminate()
            process.wait(timeout=5)

            task['status'] = ScrapingStatus.STOPPED.value
            task['completed_at'] = datetime.now().isoformat()
            save_tasks(tasks)

            return {"message": f"Task {task_id} stopped successfully", "status": "stopped"}

        except psutil.TimeoutExpired:
            process.kill()  # Force kill
            task['status'] = ScrapingStatus.STOPPED.value
            save_tasks(tasks)
            return {"message": f"Task {task_id} force stopped", "status": "stopped"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stopping scraping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scraping/logs/{task_id}")
def get_scraping_logs(task_id: str, tail: int = 100):
    """
    Get logs for a scraping task.

    Args:
        task_id: Task ID
        tail: Number of last lines to return (default 100)

    Returns:
        Log content
    """
    try:
        tasks = load_tasks()

        if task_id not in tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        log_file = tasks[task_id].get('log_file')
        if not log_file or not Path(log_file).exists():
            raise HTTPException(status_code=404, detail="Log file not found")

        # Read last N lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            tail_lines = lines[-tail:] if len(lines) > tail else lines

        return {
            "task_id": task_id,
            "log_file": log_file,
            "lines": len(lines),
            "tail": tail,
            "content": "".join(tail_lines)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/scraping/tasks/{task_id}")
def delete_task(task_id: str):
    """
    Delete a completed task from the list.

    Args:
        task_id: Task ID to delete

    Returns:
        Confirmation message
    """
    try:
        tasks = load_tasks()

        if task_id not in tasks:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

        task = tasks[task_id]
        if task['status'] == ScrapingStatus.RUNNING.value:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete running task. Stop it first."
            )

        del tasks[task_id]
        save_tasks(tasks)

        return {"message": f"Task {task_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting task: {e}")
        raise HTTPException(status_code=500, detail=str(e))
