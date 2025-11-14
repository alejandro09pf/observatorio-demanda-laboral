"""
Pydantic schemas for statistics endpoints.
"""
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime, date


class DateRange(BaseModel):
    """Date range model."""
    start: Optional[date] = None
    end: Optional[date] = None


class ExtractionMethodsBreakdown(BaseModel):
    """Breakdown of extraction methods."""
    ner: int
    regex: int
    pipeline_a1: int  # Combined NER + Regex for Pipeline A
    pipeline_b_total: int  # Total LLM enhanced skills
    pipeline_b_gemma: int  # Gemma specifically
    pipeline_b_jobs: int  # Jobs with LLM enhancement


class StatsResponse(BaseModel):
    """General statistics response."""
    # Funnel de datos
    total_raw_jobs: int
    total_cleaned_jobs: int
    total_jobs_with_skills: int

    # Skills
    total_skills: int
    total_unique_skills: int
    extraction_methods: ExtractionMethodsBreakdown

    # Clustering
    n_clusters: int

    # Geografía
    n_countries: int
    countries: List[str]
    portals: List[str]

    # Temporal
    date_range: DateRange
    last_scraping: Optional[datetime] = None

    class Config:
        from_attributes = True
