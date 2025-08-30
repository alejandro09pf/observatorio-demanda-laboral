#!/usr/bin/env python3
"""
Pipeline Automator - Automated Job Processing System

This module automatically processes jobs through the entire pipeline:
1. Skill Extraction (NER + Regex)
2. LLM Enhancement (when ready)
3. Embedding Generation (when ready)
4. Analysis & Clustering (when ready)

The system runs continuously and processes jobs as they become available.
"""

import time
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import psycopg2
from psycopg2.extras import RealDictCursor
import json

# Add src to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import get_settings
from config.logging_config import setup_logging
from extractor.pipeline import ExtractionPipeline
from database.operations import DatabaseOperations

logger = logging.getLogger(__name__)

@dataclass
class PipelineStatus:
    """Current status of the pipeline."""
    is_running: bool
    last_check: datetime
    jobs_processed: int
    jobs_failed: int
    current_batch_size: int
    extraction_queue_size: int
    enhancement_queue_size: int
    embedding_queue_size: int
    analysis_queue_size: int
    errors: List[str]

class PipelineAutomator:
    """Automatically processes jobs through the entire pipeline."""
    
    def __init__(self):
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')
        
        # Initialize components
        self.extraction_pipeline = ExtractionPipeline()
        self.db_ops = DatabaseOperations()
        
        # Pipeline status
        self.status = PipelineStatus(
            is_running=False,
            last_check=datetime.now(),
            jobs_processed=0,
            jobs_failed=0,
            current_batch_size=10,
            extraction_queue_size=0,
            enhancement_queue_size=0,
            embedding_queue_size=0,
            analysis_queue_size=0,
            errors=[]
        )
        
        # Configuration
        self.batch_size = 10
        self.check_interval = 60  # seconds
        self.max_retries = 3
        self.retry_delay = 300  # 5 minutes
        
        # Threading
        self.stop_event = threading.Event()
        self.processing_thread = None
        
        logger.info("Pipeline Automator initialized successfully")
    
    def start(self):
        """Start the automated pipeline processing."""
        if self.status.is_running:
            logger.warning("Pipeline is already running")
            return
        
        logger.info("🚀 Starting Pipeline Automator...")
        self.status.is_running = True
        self.stop_event.clear()
        
        # Start processing thread
        self.processing_thread = threading.Thread(target=self._processing_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("✅ Pipeline Automator started successfully")
    
    def stop(self):
        """Stop the automated pipeline processing."""
        if not self.status.is_running:
            logger.warning("Pipeline is not running")
            return
        
        logger.info("🛑 Stopping Pipeline Automator...")
        self.status.is_running = False
        self.stop_event.set()
        
        if self.processing_thread and self.processing_thread.is_alive():
            self.processing_thread.join(timeout=10)
        
        logger.info("✅ Pipeline Automator stopped successfully")
    
    def _processing_loop(self):
        """Main processing loop that runs continuously."""
        logger.info("🔄 Starting processing loop...")
        
        while not self.stop_event.is_set():
            try:
                # Update queue sizes
                self._update_queue_sizes()
                
                # Process extraction queue
                self._process_extraction_queue()
                
                # Process enhancement queue (when LLM is ready)
                # self._process_enhancement_queue()
                
                # Process embedding queue (when embedder is ready)
                # self._process_embedding_queue()
                
                # Process analysis queue (when analyzer is ready)
                # self._process_analysis_queue()
                
                # Update status
                self.status.last_check = datetime.now()
                
                # Wait before next check
                self.stop_event.wait(self.check_interval)
                
            except Exception as e:
                error_msg = f"Error in processing loop: {e}"
                logger.error(error_msg)
                self.status.errors.append(error_msg)
                
                # Wait before retry
                self.stop_event.wait(self.retry_delay)
    
    def _update_queue_sizes(self):
        """Update the size of each processing queue."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Extraction queue (pending extraction)
                cursor.execute("""
                    SELECT COUNT(*) FROM raw_jobs 
                    WHERE extraction_status = 'pending'
                """)
                self.status.extraction_queue_size = cursor.fetchone()[0]
                
                # Enhancement queue (pending enhancement)
                cursor.execute("""
                    SELECT COUNT(*) FROM raw_jobs 
                    WHERE extraction_status = 'completed' 
                    AND enhancement_status = 'pending'
                """)
                self.status.enhancement_queue_size = cursor.fetchone()[0]
                
                # Embedding queue (pending embedding)
                cursor.execute("""
                    SELECT COUNT(*) FROM raw_jobs 
                    WHERE enhancement_status = 'completed' 
                    AND embedding_status = 'pending'
                """)
                self.status.embedding_queue_size = cursor.fetchone()[0]
                
                # Analysis queue (pending analysis)
                cursor.execute("""
                    SELECT COUNT(*) FROM raw_jobs 
                    WHERE embedding_status = 'completed' 
                    AND analysis_status = 'pending'
                """)
                self.status.analysis_queue_size = cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error updating queue sizes: {e}")
    
    def _process_extraction_queue(self):
        """Process jobs in the extraction queue."""
        if self.status.extraction_queue_size == 0:
            return
        
        logger.info(f"📋 Processing extraction queue: {self.status.extraction_queue_size} jobs pending")
        
        try:
            # Process batch
            results = self.extraction_pipeline.process_batch(self.batch_size)
            
            if 'error' not in results:
                self.status.jobs_processed += results.get('success', 0)
                self.status.jobs_failed += results.get('errors', 0)
                
                logger.info(f"✅ Extraction batch completed: {results.get('success', 0)} success, {results.get('errors', 0)} errors")
            else:
                logger.error(f"❌ Extraction batch failed: {results['error']}")
                self.status.errors.append(f"Extraction batch failed: {results['error']}")
                
        except Exception as e:
            error_msg = f"Error processing extraction queue: {e}"
            logger.error(error_msg)
            self.status.errors.append(error_msg)
    
    def _process_enhancement_queue(self):
        """Process jobs in the enhancement queue (LLM processing)."""
        if self.status.enhancement_queue_size == 0:
            return
        
        logger.info(f"🧠 Processing enhancement queue: {self.status.enhancement_queue_size} jobs pending")
        
        # TODO: Implement when LLM processor is ready
        logger.info("LLM enhancement not yet implemented")
    
    def _process_embedding_queue(self):
        """Process jobs in the embedding queue."""
        if self.status.embedding_queue_size == 0:
            return
        
        logger.info(f"🔢 Processing embedding queue: {self.status.embedding_queue_size} jobs pending")
        
        # TODO: Implement when embedder is ready
        logger.info("Embedding generation not yet implemented")
    
    def _process_analysis_queue(self):
        """Process jobs in the analysis queue."""
        if self.status.analysis_queue_size == 0:
            return
        
        logger.info(f"📊 Processing analysis queue: {self.status.analysis_queue_size} jobs pending")
        
        # TODO: Implement when analyzer is ready
        logger.info("Analysis and clustering not yet implemented")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current pipeline status."""
        return {
            'is_running': self.status.is_running,
            'last_check': self.status.last_check.isoformat(),
            'jobs_processed': self.status.jobs_processed,
            'jobs_failed': self.status.jobs_failed,
            'current_batch_size': self.status.current_batch_size,
            'queue_sizes': {
                'extraction': self.status.extraction_queue_size,
                'enhancement': self.status.enhancement_queue_size,
                'embedding': self.status.embedding_queue_size,
                'analysis': self.status.analysis_queue_size
            },
            'errors': self.status.errors[-5:],  # Last 5 errors
            'uptime': self._get_uptime()
        }
    
    def _get_uptime(self) -> str:
        """Get pipeline uptime."""
        if not self.status.is_running:
            return "Stopped"
        
        uptime = datetime.now() - self.status.last_check
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"
    
    def get_pipeline_health(self) -> Dict[str, Any]:
        """Get pipeline health metrics."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()
                
                # Get recent job processing stats
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_jobs,
                        COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END) as extraction_completed,
                        COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END) as extraction_failed,
                        COUNT(CASE WHEN extraction_status = 'pending' THEN 1 END) as extraction_pending,
                        AVG(EXTRACT(EPOCH FROM (extraction_completed_at - scraped_at))) as avg_extraction_time
                    FROM raw_jobs 
                    WHERE scraped_at >= NOW() - INTERVAL '24 hours'
                """)
                
                stats = cursor.fetchone()
                
                if stats and stats[0] > 0:
                    total_jobs, extraction_completed, extraction_failed, extraction_pending, avg_extraction_time = stats
                    
                    return {
                        'health_score': self._calculate_health_score(extraction_completed, extraction_failed, total_jobs),
                        'total_jobs_24h': total_jobs,
                        'extraction_success_rate': (extraction_completed / total_jobs) * 100 if total_jobs > 0 else 0,
                        'extraction_failure_rate': (extraction_failed / total_jobs) * 100 if total_jobs > 0 else 0,
                        'avg_extraction_time_seconds': round(avg_extraction_time, 2) if avg_extraction_time else 0,
                        'queue_backlog': extraction_pending,
                        'status': 'healthy' if extraction_failed == 0 else 'degraded' if extraction_failed < total_jobs * 0.1 else 'unhealthy'
                    }
                else:
                    return {
                        'health_score': 100,
                        'total_jobs_24h': 0,
                        'extraction_success_rate': 100,
                        'extraction_failure_rate': 0,
                        'avg_extraction_time_seconds': 0,
                        'queue_backlog': 0,
                        'status': 'healthy'
                    }
                    
        except Exception as e:
            logger.error(f"Error getting pipeline health: {e}")
            return {
                'health_score': 0,
                'status': 'error',
                'error': str(e)
            }
    
    def _calculate_health_score(self, completed: int, failed: int, total: int) -> int:
        """Calculate pipeline health score (0-100)."""
        if total == 0:
            return 100
        
        success_rate = completed / total
        failure_rate = failed / total
        
        # Penalize failures heavily
        if failure_rate > 0.1:  # More than 10% failure rate
            return max(0, int((success_rate - failure_rate * 2) * 100))
        
        return int(success_rate * 100)
    
    def reset_counters(self):
        """Reset pipeline counters."""
        self.status.jobs_processed = 0
        self.status.jobs_failed = 0
        self.status.errors.clear()
        logger.info("Pipeline counters reset")
    
    def set_batch_size(self, size: int):
        """Set the batch size for processing."""
        if size > 0 and size <= 100:
            self.batch_size = size
            self.status.current_batch_size = size
            logger.info(f"Batch size set to {size}")
        else:
            logger.warning(f"Invalid batch size: {size}. Must be between 1 and 100")
    
    def set_check_interval(self, seconds: int):
        """Set the check interval for the processing loop."""
        if seconds >= 10:
            self.check_interval = seconds
            logger.info(f"Check interval set to {seconds} seconds")
        else:
            logger.warning(f"Invalid check interval: {seconds}. Must be at least 10 seconds")
