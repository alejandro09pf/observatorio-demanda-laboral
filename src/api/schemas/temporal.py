"""
Pydantic schemas for temporal analysis endpoints.
"""
from pydantic import BaseModel
from typing import List, Dict, Optional, Any


class QuarterData(BaseModel):
    """Quarterly skill data."""
    quarter: str  # e.g., "2024-Q1"
    top_skills: List[Dict[str, Any]]  # [{"skill": "Python", "count": 123}, ...]


class TemporalAnalysisResponse(BaseModel):
    """Temporal analysis response."""
    country: Optional[str] = None
    year: Optional[int] = None
    quarters: List[QuarterData]
    heatmap_data: List[Dict[str, Any]]  # For frontend heatmap visualization
