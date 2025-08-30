#!/usr/bin/env python3
"""
Master Controller - Central Coordination of Automation System

This is the central coordinator that manages all automation components:
1. Intelligent Scheduler (scraping automation)
2. Pipeline Automator (job processing automation)
3. Monitoring System (system health and alerts)

The controller provides a unified interface for the CLI to control the entire system.
"""

import logging
import threading
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time

# Add src to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from config.logging_config import setup_logging
from automation.intelligent_scheduler import IntelligentScheduler
from automation.pipeline_automator import PipelineAutomator

logger = logging.getLogger(__name__)

@dataclass
class SystemStatus:
    """Overall system status."""
    is_running: bool
    start_time: Optional[datetime]
    uptime: str
    scheduler_status: str
    pipeline_status: str
    monitoring_status: str
    overall_health: str

class MasterController:
    """Central controller for the entire automation system."""
    
    def __init__(self):
        self.settings = get_settings()
        
        # Initialize components
        self.intelligent_scheduler = IntelligentScheduler()
        self.pipeline_automator = PipelineAutomator()
        
        # System state
        self.is_running = False
        self.start_time = None
        self.stop_event = threading.Event()
        
        # Component status
        self.scheduler_status = 'stopped'
        self.pipeline_status = 'stopped'
        self.monitoring_status = 'stopped'
        
        # Health monitoring
        self.health_check_interval = 60  # seconds
        self.last_health_check = datetime.now()
        self.overall_health = 'unknown'
        
        # Health monitoring thread
        self.health_thread = None
        
        logger.info("Master Controller initialized successfully")
    
    def start_system(self) -> bool:
        """Start the entire automation system."""
        if self.is_running:
            logger.warning("System is already running")
            return False
        
        try:
            logger.info("🚀 Starting Labor Market Observatory Automation System...")
            
            # Start intelligent scheduler
            logger.info("Starting Intelligent Scheduler...")
            self.intelligent_scheduler.start()
            self.scheduler_status = 'running'
            
            # Start pipeline automator
            logger.info("Starting Pipeline Automator...")
            self.pipeline_automator.start()
            self.pipeline_status = 'running'
            
            # Start health monitoring
            logger.info("Starting Health Monitoring...")
            self._start_health_monitoring()
            self.monitoring_status = 'running'
            
            # Update system state
            self.is_running = True
            self.start_time = datetime.now()
            self.stop_event.clear()
            
            logger.info("✅ Automation System started successfully!")
            logger.info("Components running:")
            logger.info("  - Intelligent Scheduler: ✅")
            logger.info("  - Pipeline Automator: ✅")
            logger.info("  - Health Monitoring: ✅")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start automation system: {e}")
            self._emergency_stop()
            return False
    
    def stop_system(self) -> bool:
        """Stop the entire automation system."""
        if not self.is_running:
            logger.warning("System is not running")
            return False
        
        try:
            logger.info("🛑 Stopping Labor Market Observatory Automation System...")
            
            # Stop all components
            self.stop_event.set()
            
            # Stop intelligent scheduler
            logger.info("Stopping Intelligent Scheduler...")
            self.intelligent_scheduler.stop()
            self.scheduler_status = 'stopped'
            
            # Stop pipeline automator
            logger.info("Stopping Pipeline Automator...")
            self.pipeline_automator.stop()
            self.pipeline_status = 'stopped'
            
            # Stop health monitoring
            logger.info("Stopping Health Monitoring...")
            self._stop_health_monitoring()
            self.monitoring_status = 'stopped'
            
            # Update system state
            self.is_running = False
            
            logger.info("✅ Automation System stopped successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error stopping automation system: {e}")
            return False
    
    def _emergency_stop(self):
        """Emergency stop in case of startup failure."""
        logger.error("🚨 Emergency stop initiated due to startup failure")
        
        try:
            self.intelligent_scheduler.stop()
            self.pipeline_automator.stop()
            self._stop_health_monitoring()
        except:
            pass
        
        self.is_running = False
        self.scheduler_status = 'error'
        self.pipeline_status = 'error'
        self.monitoring_status = 'error'
    
    def _start_health_monitoring(self):
        """Start the health monitoring thread."""
        self.health_thread = threading.Thread(target=self._health_monitoring_loop)
        self.health_thread.daemon = True
        self.health_thread.start()
    
    def _stop_health_monitoring(self):
        """Stop the health monitoring thread."""
        if self.health_thread and self.health_thread.is_alive():
            self.health_thread.join(timeout=5)
    
    def _health_monitoring_loop(self):
        """Continuous health monitoring loop."""
        logger.info("💚 Starting health monitoring loop...")
        
        while not self.stop_event.is_set():
            try:
                self._check_system_health()
                self.stop_event.wait(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")
                self.stop_event.wait(30)  # Wait 30 seconds on error
    
    def _check_system_health(self):
        """Check the health of all components."""
        try:
            # Get component health
            scheduler_status = self.intelligent_scheduler.get_status()
            pipeline_status = self.pipeline_automator.get_status()
            
            # Determine overall health based on component status
            scheduler_running = scheduler_status.get('scheduler', {}).get('is_running', False)
            pipeline_running = pipeline_status.get('is_running', False)
            
            if scheduler_running and pipeline_running:
                self.overall_health = 'healthy'
            elif scheduler_running or pipeline_running:
                self.overall_health = 'degraded'
            else:
                self.overall_health = 'critical'
            
            self.last_health_check = datetime.now()
            
            # Log critical health issues
            if self.overall_health == 'critical':
                logger.warning("🚨 System health critical!")
                logger.warning(f"  Scheduler running: {scheduler_running}")
                logger.warning(f"  Pipeline running: {pipeline_running}")
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            self.overall_health = 'error'
    
    def get_system_status(self) -> SystemStatus:
        """Get comprehensive system status."""
        uptime = self._calculate_uptime()
        
        return SystemStatus(
            is_running=self.is_running,
            start_time=self.start_time,
            uptime=uptime,
            scheduler_status=self.scheduler_status,
            pipeline_status=self.pipeline_status,
            monitoring_status=self.monitoring_status,
            overall_health=self.overall_health
        )
    
    def _calculate_uptime(self) -> str:
        """Calculate system uptime."""
        if not self.start_time:
            return "Not started"
        
        uptime = datetime.now() - self.start_time
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get detailed status of all components."""
        return {
            'system': {
                'is_running': self.is_running,
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'uptime': self._calculate_uptime(),
                'overall_health': self.overall_health,
                'last_health_check': self.last_health_check.isoformat()
            },
            'components': {
                'scheduler': {
                    'status': self.scheduler_status,
                    'details': self.intelligent_scheduler.get_status()
                },
                'pipeline': {
                    'status': self.pipeline_status,
                    'details': self.pipeline_automator.get_status()
                },
                'monitoring': {
                    'status': self.monitoring_status
                }
            }
        }
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get status of the intelligent scheduler."""
        return self.intelligent_scheduler.get_status()
    
    def get_pipeline_status(self) -> Dict[str, Any]:
        """Get status of the pipeline automator."""
        return self.pipeline_automator.get_status()
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get system health metrics."""
        return {
            'overall_health': self.overall_health,
            'scheduler_status': self.intelligent_scheduler.get_status(),
            'pipeline_status': self.pipeline_automator.get_status(),
            'last_check': self.last_health_check.isoformat()
        }
    
    # Control methods for individual components
    
    def force_run_job(self, job_id: str) -> bool:
        """Force run a specific scheduled job."""
        if not self.is_running:
            logger.warning("Cannot force run job: system not running")
            return False
        
        return self.intelligent_scheduler.force_run_job(job_id)
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a scheduled job."""
        if not self.is_running:
            logger.warning("Cannot pause job: system not running")
            return False
        
        return self.intelligent_scheduler.pause_job(job_id)
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job."""
        if not self.is_running:
            logger.warning("Cannot resume job: system not running")
            return False
        
        return self.intelligent_scheduler.resume_job(job_id)
    
    def process_jobs_manually(self, batch_size: int = 10) -> Dict[str, Any]:
        """Manually trigger job processing."""
        if not self.is_running:
            logger.warning("Cannot process jobs: system not running")
            return {'error': 'System not running'}
        
        return self.pipeline_automator.process_batch(batch_size)
    
    def reset_pipeline_counters(self):
        """Reset pipeline counters."""
        if not self.is_running:
            logger.warning("Cannot reset counters: system not running")
            return
        
        self.pipeline_automator.reset_counters()
        logger.info("Pipeline counters reset successfully")
    
    def set_pipeline_batch_size(self, size: int):
        """Set the batch size for pipeline processing."""
        if not self.is_running:
            logger.warning("Cannot set batch size: system not running")
            return
        
        self.pipeline_automator.set_batch_size(size)
    
    def set_pipeline_check_interval(self, seconds: int):
        """Set the check interval for pipeline processing."""
        if not self.is_running:
            logger.warning("Cannot set check interval: system not running")
            return
        
        self.pipeline_automator.set_check_interval(seconds)
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job."""
        return self.intelligent_scheduler.get_job_status(job_id)
    
    def list_all_jobs(self) -> Dict[str, Any]:
        """List all scheduled jobs and their status."""
        return {
            'scheduled_jobs': [self.intelligent_scheduler._job_to_dict(job) 
                              for job in self.intelligent_scheduler.scheduled_jobs.values()],
            'running_jobs': list(self.intelligent_scheduler.running_jobs.keys()),
            'recent_history': self.intelligent_scheduler.job_history[-10:]
        }
    
    def restart_component(self, component: str) -> bool:
        """Restart a specific component."""
        if component == 'scheduler':
            logger.info("Restarting Intelligent Scheduler...")
            self.intelligent_scheduler.stop()
            time.sleep(2)
            self.intelligent_scheduler.start()
            return True
        elif component == 'pipeline':
            logger.info("Restarting Pipeline Automator...")
            self.pipeline_automator.stop()
            time.sleep(2)
            self.pipeline_automator.start()
            return True
        else:
            logger.error(f"Unknown component: {component}")
            return False
