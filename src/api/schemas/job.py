"""
Pydantic schemas for jobs endpoints.
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from uuid import UUID


class JobBase(BaseModel):
    """Base job model."""
    job_id: UUID
    title: str
    company: Optional[str] = None
    location: Optional[str] = None
    country: str
    portal: str
    posted_date: Optional[date] = None
    scraped_at: datetime
    url: str
    salary_raw: Optional[str] = None
    contract_type: Optional[str] = None
    remote_type: Optional[str] = None

    class Config:
        from_attributes = True


class JobDetail(JobBase):
    """Detailed job model with description and all types of extracted skills."""
    description: str
    requirements: Optional[str] = None
    extracted_skills: List[dict] = []  # Pipeline A (NER + Regex)
    enhanced_skills: List[dict] = []   # Pipeline B (LLM)
    manual_skills: List[dict] = []     # Manual/Golden annotations


class JobListResponse(BaseModel):
    """Paginated job list response."""
    total: int
    limit: int
    offset: int
    jobs: List[JobBase]


class ExtractedSkillSchema(BaseModel):
    """Extracted skill schema."""
    skill_text: str
    skill_type: Optional[str] = None
    extraction_method: Optional[str] = None
    confidence_score: Optional[float] = None
    esco_uri: Optional[str] = None
    llm_model: Optional[str] = None  # For Pipeline B skills

    class Config:
        from_attributes = True
