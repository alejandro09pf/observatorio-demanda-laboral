"""
Pydantic schemas for admin endpoints.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ScrapingStatus(str, Enum):
    """Scraping task status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class ScrapingConfig(BaseModel):
    """Scraping configuration for Celery workers."""
    spiders: List[str] = Field(..., description="List of spider names")
    countries: List[str] = Field(..., description="List of country codes (CO, MX, AR, etc.)")
    max_jobs: int = Field(100, ge=1, le=10000, description="Max jobs per spider")
    max_pages: int = Field(5, ge=1, le=100, description="Max pages per spider")


class ScrapingTask(BaseModel):
    """Scraping task information."""
    task_id: str
    config: ScrapingConfig
    status: ScrapingStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    pid: Optional[int] = None
    jobs_scraped: int = 0
    errors: int = 0
    log_file: Optional[str] = None


class ScrapingStartResponse(BaseModel):
    """Response when starting scraping tasks (Celery version)."""
    task_ids: List[str]
    status: ScrapingStatus
    message: str
    tasks: Optional[List[Dict[str, Any]]] = None


class ScrapingStatusResponse(BaseModel):
    """Response for scraping status."""
    active_tasks: List[ScrapingTask]
    total_active: int
    system_status: str


class AvailableSpidersResponse(BaseModel):
    """Available spiders and countries."""
    spiders: List[str]
    countries: List[str]
