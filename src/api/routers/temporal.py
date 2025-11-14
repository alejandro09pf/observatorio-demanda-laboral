"""
Temporal Analysis Router - Skill demand evolution over time.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_
from typing import Optional
from datetime import datetime
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.dependencies import get_db
from api.schemas.temporal import QuarterData, TemporalAnalysisResponse
from database.models import ExtractedSkill, RawJob

logger = logging.getLogger(__name__)

router = APIRouter()


def get_quarter(date):
    """Get quarter from date (Q1, Q2, Q3, Q4)."""
    month = date.month if hasattr(date, 'month') else 1
    quarter = (month - 1) // 3 + 1
    year = date.year if hasattr(date, 'year') else datetime.now().year
    return f"{year}-Q{quarter}"


@router.get("/temporal/skills", response_model=TemporalAnalysisResponse)
def get_temporal_skills(
    country: Optional[str] = Query(None, description="Filter by country"),
    year: Optional[int] = Query(None, description="Filter by year"),
    top_n: int = Query(10, ge=1, le=50, description="Top N skills per quarter"),
    db: Session = Depends(get_db)
) -> TemporalAnalysisResponse:
    """
    Get temporal evolution of skill demand by quarter.

    Args:
        country: Filter by country (e.g., CO, MX, AR)
        year: Filter by specific year (e.g., 2024)
        top_n: Number of top skills per quarter

    Returns:
        Quarterly skill evolution data
    """
    try:
        # Build query
        query = db.query(
            RawJob.posted_date,
            ExtractedSkill.skill_text,
            func.count(ExtractedSkill.skill_text).label('count')
        ).join(
            ExtractedSkill, RawJob.job_id == ExtractedSkill.job_id
        ).filter(
            RawJob.posted_date.isnot(None)
        )

        # Apply filters
        if country:
            query = query.filter(RawJob.country == country.upper())

        if year:
            query = query.filter(extract('year', RawJob.posted_date) == year)

        # Group by date and skill
        results = query.group_by(
            RawJob.posted_date,
            ExtractedSkill.skill_text
        ).all()

        # Process by quarter
        quarterly_data = {}
        skill_totals = {}  # For heatmap

        for row in results:
            quarter = get_quarter(row.posted_date)
            skill = row.skill_text
            count = row.count

            # Group by quarter
            if quarter not in quarterly_data:
                quarterly_data[quarter] = {}

            if skill not in quarterly_data[quarter]:
                quarterly_data[quarter][skill] = 0

            quarterly_data[quarter][skill] += count

            # Track totals for heatmap
            if skill not in skill_totals:
                skill_totals[skill] = {}
            if quarter not in skill_totals[skill]:
                skill_totals[skill][quarter] = 0
            skill_totals[skill][quarter] += count

        # Build response
        quarters = []
        for quarter in sorted(quarterly_data.keys()):
            # Get top N skills for this quarter
            top_skills = sorted(
                quarterly_data[quarter].items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]

            quarters.append(QuarterData(
                quarter=quarter,
                top_skills=[{"skill": s, "count": c} for s, c in top_skills]
            ))

        # Build heatmap data (skill x quarter matrix)
        # Get top skills overall
        overall_top_skills = set()
        for quarter_skills in quarterly_data.values():
            top_in_quarter = sorted(
                quarter_skills.items(),
                key=lambda x: x[1],
                reverse=True
            )[:top_n]
            overall_top_skills.update([s for s, _ in top_in_quarter])

        heatmap_data = []
        for skill in list(overall_top_skills)[:20]:  # Limit to 20 skills for heatmap
            row = {"skill": skill}
            for quarter in sorted(quarterly_data.keys()):
                row[quarter] = quarterly_data[quarter].get(skill, 0)
            heatmap_data.append(row)

        return TemporalAnalysisResponse(
            country=country,
            year=year,
            quarters=quarters,
            heatmap_data=heatmap_data
        )

    except Exception as e:
        logger.error(f"Error in temporal analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing temporal data: {str(e)}")


@router.get("/temporal/trends")
def get_skill_trends(
    skill: str = Query(..., min_length=2, description="Skill name to analyze"),
    country: Optional[str] = Query(None, description="Filter by country"),
    db: Session = Depends(get_db)
):
    """
    Get trend data for a specific skill over time.

    Args:
        skill: Skill name (e.g., "Python", "React")
        country: Optional country filter

    Returns:
        Monthly/quarterly counts for the skill
    """
    try:
        query = db.query(
            RawJob.posted_date,
            func.count(ExtractedSkill.skill_text).label('count')
        ).join(
            ExtractedSkill, RawJob.job_id == ExtractedSkill.job_id
        ).filter(
            ExtractedSkill.skill_text.ilike(f"%{skill}%"),
            RawJob.posted_date.isnot(None)
        )

        if country:
            query = query.filter(RawJob.country == country.upper())

        results = query.group_by(RawJob.posted_date).all()

        # Group by quarter
        quarterly_counts = {}
        for row in results:
            quarter = get_quarter(row.posted_date)
            if quarter not in quarterly_counts:
                quarterly_counts[quarter] = 0
            quarterly_counts[quarter] += row.count

        return {
            "skill": skill,
            "country": country,
            "data": [
                {"period": q, "count": c}
                for q, c in sorted(quarterly_counts.items())
            ]
        }

    except Exception as e:
        logger.error(f"Error getting skill trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))
