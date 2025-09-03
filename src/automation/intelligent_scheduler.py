#!/usr/bin/env python3
"""
Intelligent Scheduler - Coordinates Scraping and Pipeline Processing

This scheduler intelligently manages:
1. Scraping jobs based on schedule.yaml
2. Pipeline processing coordination
3. Resource management and load balancing
4. Error recovery and retry logic
5. Health monitoring and alerting
"""

import yaml
import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import subprocess
import signal
import os
import psutil
from pathlib import Path

# Add src to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from config.logging_config import setup_logging
from automation.pipeline_automator import PipelineAutomator

logger = logging.getLogger(__name__)

@dataclass
class ScheduledJob:
    """Represents a scheduled scraping job."""
    id: str
    spider: str
    country: str
    trigger_type: str
    trigger_config: Dict[str, Any]
    max_pages: int
    limit: int
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    status: str  # 'pending', 'running', 'completed', 'failed'
    attempts: int
    max_attempts: int

@dataclass
class SystemHealth:
    """System health metrics."""
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    database_connections: int
    active_processes: int
    overall_status: str  # 'healthy', 'degraded', 'critical'

class IntelligentScheduler:
    """Intelligent scheduler for scraping and pipeline coordination."""
    
    def __init__(self, config_file: str = "config/schedule.yaml"):
        self.settings = get_settings()
        self.config_file = config_file
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize components
        self.pipeline_automator = PipelineAutomator()
        
        # Job management
        self.scheduled_jobs: Dict[str, ScheduledJob] = {}
        self.running_jobs: Dict[str, subprocess.Popen] = {}
        self.job_history: List[Dict[str, Any]] = []
        
        # Scheduler state
        self.is_running = False
        self.stop_event = threading.Event()
        self.scheduler_thread = None
        
        # Resource monitoring
        self.max_concurrent_jobs = self.config.get('settings', {}).get('max_concurrent_jobs', 3)
        self.job_timeout = self.config.get('settings', {}).get('job_timeout', 3600)
        self.retry_failed_jobs = self.config.get('settings', {}).get('retry_failed_jobs', True)
        self.max_retries = self.config.get('settings', {}).get('max_retries', 3)
        
        # Health monitoring
        self.health_check_interval = 300  # 5 minutes
        self.last_health_check = datetime.now()
        self.system_health = SystemHealth(0, 0, 0, 0, 0, 'unknown')
        
        # Initialize scheduled jobs
        self._initialize_scheduled_jobs()
        
        logger.info("Intelligent Scheduler initialized successfully")
    
    def _load_config(self) -> dict:
        """Load schedule configuration from YAML file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded schedule configuration from {self.config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load schedule configuration: {e}")
            raise
    
    def _initialize_scheduled_jobs(self):
        """Initialize scheduled jobs from configuration."""
        jobs = self.config.get('jobs', [])
        
        for job_config in jobs:
            job_id = f"{job_config['spider']}_{job_config['country']}_{job_config['trigger']}"
            
            # Calculate next run time
            next_run = self._calculate_next_run(job_config)
            
            job = ScheduledJob(
                id=job_id,
                spider=job_config['spider'],
                country=job_config['country'],
                trigger_type=job_config['trigger'],
                trigger_config=job_config,
                max_pages=job_config.get('max_pages', 10),
                limit=job_config.get('limit', 100),
                last_run=None,
                next_run=next_run,
                status='pending',
                attempts=0,
                max_attempts=self.max_retries
            )
            
            self.scheduled_jobs[job_id] = job
            logger.info(f"Initialized job: {job_id} - Next run: {next_run}")
    
    def _calculate_next_run(self, job_config: Dict[str, Any]) -> datetime:
        """Calculate next run time for a job."""
        now = datetime.now()
        
        if job_config['trigger'] == 'cron':
            # Parse cron expression and calculate next run
            cron_expr = job_config['cron']
            return self._parse_cron_next_run(cron_expr, now)
        
        elif job_config['trigger'] == 'interval':
            if 'every_minutes' in job_config:
                return now + timedelta(minutes=job_config['every_minutes'])
            elif 'every_hours' in job_config:
                return now + timedelta(hours=job_config['every_hours'])
        
        # Default: run in 1 hour
        return now + timedelta(hours=1)
    
    def _parse_cron_next_run(self, cron_expr: str, now: datetime) -> datetime:
        """Parse cron expression and calculate next run time."""
        # Simplified cron parsing - in production, use a proper cron library
        try:
            parts = cron_expr.split()
            if len(parts) == 5:
                minute, hour, day, month, weekday = parts
                
                # For now, assume daily at specified hour:minute
                if minute != '*' and hour != '*':
                    next_run = now.replace(
                        minute=int(minute),
                        hour=int(hour),
                        second=0,
                        microsecond=0
                    )
                    
                    # If time has passed today, schedule for tomorrow
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    
                    return next_run
        except:
            pass
        
        # Fallback: run in 1 hour
        return now + timedelta(hours=1)
    
    def start(self):
        """Start the intelligent scheduler."""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        logger.info("🚀 Starting Intelligent Scheduler...")
        self.is_running = True
        self.stop_event.clear()
        
        # Start pipeline automator
        self.pipeline_automator.start()
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        # Start health monitoring thread
        self.health_thread = threading.Thread(target=self._health_monitoring_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
        
        logger.info("✅ Intelligent Scheduler started successfully")
    
    def stop(self):
        """Stop the intelligent scheduler."""
        if not self.is_running:
            logger.warning("Scheduler is not running")
            return
        
        logger.info("🛑 Stopping Intelligent Scheduler...")
        self.is_running = False
        self.stop_event.set()
        
        # Stop pipeline automator
        self.pipeline_automator.stop()
        
        # Stop all running jobs
        self._stop_all_jobs()
        
        # Wait for threads to finish
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            self.scheduler_thread.join(timeout=10)
        
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=10)
        
        logger.info("✅ Intelligent Scheduler stopped successfully")
    
    def _scheduler_loop(self):
        """Main scheduler loop."""
        logger.info("🔄 Starting scheduler loop...")
        
        while not self.stop_event.is_set():
            try:
                now = datetime.now()
                
                # Check for jobs that need to run
                self._check_scheduled_jobs(now)
                
                # Clean up completed/failed jobs
                self._cleanup_jobs()
                
                # Update job statuses
                self._update_job_statuses()
                
                # Wait before next check
                self.stop_event.wait(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                self.stop_event.wait(300)  # Wait 5 minutes on error
    
    def _check_scheduled_jobs(self, now: datetime):
        """Check which jobs need to run."""
        for job_id, job in self.scheduled_jobs.items():
            if (job.status == 'pending' and 
                job.next_run and 
                job.next_run <= now and
                len(self.running_jobs) < self.max_concurrent_jobs):
                
                # Start the job
                self._start_job(job)
    
    def _start_job(self, job: ScheduledJob):
        """Start a scheduled job."""
        try:
            logger.info(f"🚀 Starting job: {job.id}")
            
            # Update job status
            job.status = 'running'
            job.attempts += 1
            job.last_run = datetime.now()
            
            # Build scrapy command
            cmd = [
                sys.executable, "-m", "scrapy", "crawl", job.spider,
                "-a", f"country={job.country}",
                "-a", f"max_pages={job.max_pages}",
                "-a", f"limit={job.limit}",
                "-L", "INFO"
            ]
            
            # Change to project directory
            project_dir = Path(__file__).parent.parent.parent
            os.chdir(project_dir)
            
            # Set orchestrator execution flags
            env = os.environ.copy()
            env["ORCHESTRATOR_EXECUTION"] = "1"
            env["SCRAPY_ORCHESTRATOR_RUN"] = "1"
            env["ORCHESTRATOR_MODE"] = "1"
            
            # Start subprocess
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            # Store running job
            self.running_jobs[job.id] = process
            
            # Schedule next run
            job.next_run = self._calculate_next_run(job.trigger_config)
            
            logger.info(f"✅ Job {job.id} started successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to start job {job.id}: {e}")
            job.status = 'failed'
            self._record_job_failure(job, str(e))
    
    def _stop_all_jobs(self):
        """Stop all running jobs."""
        for job_id, process in self.running_jobs.items():
            try:
                logger.info(f"🛑 Stopping job: {job_id}")
                process.terminate()
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning(f"Force killing job: {job_id}")
                process.kill()
            except Exception as e:
                logger.error(f"Error stopping job {job_id}: {e}")
        
        self.running_jobs.clear()
    
    def _cleanup_jobs(self):
        """Clean up completed and failed jobs."""
        completed_jobs = []
        
        for job_id, process in self.running_jobs.items():
            if process.poll() is not None:  # Process finished
                completed_jobs.append(job_id)
                
                # Get job result
                return_code = process.returncode
                stdout, stderr = process.communicate()
                
                # Update job status
                job = self.scheduled_jobs.get(job_id)
                if job:
                    if return_code == 0:
                        job.status = 'completed'
                        logger.info(f"✅ Job {job_id} completed successfully")
                        self._record_job_success(job, stdout)
                    else:
                        job.status = 'failed'
                        logger.error(f"❌ Job {job_id} failed with return code {return_code}")
                        self._record_job_failure(job, stderr)
                        
                        # Retry if possible
                        if self.retry_failed_jobs and job.attempts < job.max_attempts:
                            job.status = 'pending'
                            job.next_run = datetime.now() + timedelta(minutes=5)
                            logger.info(f"🔄 Job {job_id} scheduled for retry")
        
        # Remove completed jobs from running list
        for job_id in completed_jobs:
            del self.running_jobs[job_id]
    
    def _update_job_statuses(self):
        """Update status of all jobs."""
        for job in self.scheduled_jobs.values():
            if job.status == 'running':
                # Check if process is still alive
                if job.id in self.running_jobs:
                    process = self.running_jobs[job.id]
                    if process.poll() is not None:
                        # Process finished but not cleaned up yet
                        continue
                else:
                    # Job marked as running but no process found
                    job.status = 'failed'
                    logger.warning(f"Job {job.id} marked as running but no process found")
    
    def _record_job_success(self, job: ScheduledJob, output: str):
        """Record successful job execution."""
        record = {
            'job_id': job.id,
            'spider': job.spider,
            'country': job.country,
            'status': 'success',
            'started_at': job.last_run,
            'completed_at': datetime.now(),
            'attempts': job.attempts,
            'output': output[:1000]  # Truncate long output
        }
        self.job_history.append(record)
    
    def _record_job_failure(self, job: ScheduledJob, error: str):
        """Record failed job execution."""
        record = {
            'job_id': job.id,
            'spider': job.spider,
            'country': job.country,
            'status': 'failed',
            'started_at': job.last_run,
            'failed_at': datetime.now(),
            'attempts': job.attempts,
            'error': error[:1000]  # Truncate long error
        }
        self.job_history.append(record)
    
    def _health_monitoring_loop(self):
        """Monitor system health."""
        logger.info("💚 Starting health monitoring loop...")
        
        while not self.stop_event.is_set():
            try:
                self._check_system_health()
                self.stop_event.wait(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                self.stop_event.wait(60)  # Wait 1 minute on error
    
    def _check_system_health(self):
        """Check system health metrics."""
        try:
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Database connections (simplified)
            database_connections = len(self.running_jobs)
            
            # Active processes
            active_processes = len(psutil.pids())
            
            # Determine overall status
            if (cpu_usage < 80 and memory_usage < 80 and 
                disk_usage < 90 and database_connections < self.max_concurrent_jobs):
                overall_status = 'healthy'
            elif (cpu_usage < 90 and memory_usage < 90 and 
                  disk_usage < 95 and database_connections < self.max_concurrent_jobs * 2):
                overall_status = 'degraded'
            else:
                overall_status = 'critical'
            
            self.system_health = SystemHealth(
                cpu_usage=cpu_usage,
                memory_usage=memory_usage,
                disk_usage=disk_usage,
                database_connections=database_connections,
                active_processes=active_processes,
                overall_status=overall_status
            )
            
            self.last_health_check = datetime.now()
            
            # Log critical status
            if overall_status == 'critical':
                logger.warning(f"🚨 System health critical: CPU={cpu_usage}%, Memory={memory_usage}%, Disk={disk_usage}%")
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive scheduler status."""
        return {
            'scheduler': {
                'is_running': self.is_running,
                'total_jobs': len(self.scheduled_jobs),
                'running_jobs': len(self.running_jobs),
                'max_concurrent_jobs': self.max_concurrent_jobs
            },
            'pipeline': self.pipeline_automator.get_status(),
            'system_health': {
                'cpu_usage': self.system_health.cpu_usage,
                'memory_usage': self.system_health.memory_usage,
                'disk_usage': self.system_health.disk_usage,
                'database_connections': self.system_health.database_connections,
                'active_processes': self.system_health.active_processes,
                'overall_status': self.system_health.overall_status,
                'last_check': self.last_health_check.isoformat()
            },
            'jobs': {
                'scheduled': [self._job_to_dict(job) for job in self.scheduled_jobs.values()],
                'running': list(self.running_jobs.keys()),
                'recent_history': self.job_history[-10:]  # Last 10 jobs
            }
        }
    
    def _job_to_dict(self, job: ScheduledJob) -> Dict[str, Any]:
        """Convert job to dictionary for serialization."""
        return {
            'id': job.id,
            'spider': job.spider,
            'country': job.country,
            'trigger_type': job.trigger_type,
            'max_pages': job.max_pages,
            'limit': job.limit,
            'last_run': job.last_run.isoformat() if job.last_run else None,
            'next_run': job.next_run.isoformat() if job.next_run else None,
            'status': job.status,
            'attempts': job.attempts,
            'max_attempts': job.max_attempts
        }
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job."""
        job = self.scheduled_jobs.get(job_id)
        if job:
            return self._job_to_dict(job)
        return None
    
    def force_run_job(self, job_id: str) -> bool:
        """Force run a specific job immediately."""
        job = self.scheduled_jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if len(self.running_jobs) >= self.max_concurrent_jobs:
            logger.warning(f"Cannot start job {job_id}: maximum concurrent jobs reached")
            return False
        
        logger.info(f"🔄 Force running job: {job_id}")
        self._start_job(job)
        return True
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        job = self.scheduled_jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job.status == 'running':
            # Stop the running job
            if job_id in self.running_jobs:
                process = self.running_jobs[job_id]
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except:
                    process.kill()
                del self.running_jobs[job_id]
        
        job.status = 'paused'
        logger.info(f"⏸️ Job {job_id} paused")
        return True
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        job = self.scheduled_jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return False
        
        if job.status == 'paused':
            job.status = 'pending'
            job.next_run = datetime.now()
            logger.info(f"▶️ Job {job_id} resumed")
            return True
        
        return False
