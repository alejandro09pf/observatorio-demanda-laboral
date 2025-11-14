"""
Pydantic schemas for skills endpoints.
"""
from pydantic import BaseModel
from typing import List, Optional


class SkillCount(BaseModel):
    """Skill with frequency count."""
    skill_text: str
    count: int
    percentage: float
    type: Optional[str] = None
    esco_uri: Optional[str] = None


class TopSkillsResponse(BaseModel):
    """Response for top skills endpoint."""
    total_unique: int
    skills: List[SkillCount]
