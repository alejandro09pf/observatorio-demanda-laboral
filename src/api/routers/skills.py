"""
Skills Router - Skill analysis and aggregations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.dependencies import get_db
from api.schemas.skill import SkillCount, TopSkillsResponse
from database.models import ExtractedSkill, RawJob

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/skills/top", response_model=TopSkillsResponse)
def get_top_skills(
    country: Optional[str] = Query(None, description="Filter by country code"),
    skill_type: Optional[str] = Query(None, description="Filter by skill type (hard, soft)"),
    extraction_method: Optional[str] = Query(None, description="Filter by extraction method (ner, regex, pipeline_a, pipeline_b)"),
    mapping_status: Optional[str] = Query(None, description="Filter by mapping status (esco_mapped, unmapped)"),
    limit: int = Query(20, ge=1, le=100, description="Number of top skills to return"),
    db: Session = Depends(get_db)
) -> TopSkillsResponse:
    """
    Get the most demanded skills with frequency counts.

    Args:
        country: Filter by country (CO, MX, AR, etc.)
        skill_type: Filter by skill type (hard, soft, all)
        extraction_method: Filter by extraction method (ner, regex, pipeline_a, pipeline_b)
        mapping_status: Filter by ESCO mapping status (esco_mapped, unmapped)
        limit: Number of top skills to return (1-100)

    Returns:
        TopSkillsResponse with skill frequencies
    """
    try:
        # Build base query
        query = db.query(
            ExtractedSkill.skill_text,
            ExtractedSkill.skill_type,
            ExtractedSkill.esco_uri,
            func.count(ExtractedSkill.skill_text).label('count')
        )

        # Join with jobs if filtering by country
        if country:
            query = query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
            query = query.filter(RawJob.country == country.upper())

        # Filter by skill type
        if skill_type and skill_type.lower() in ['hard', 'soft']:
            query = query.filter(ExtractedSkill.skill_type == skill_type.lower())

        # Filter by extraction method
        if extraction_method:
            if extraction_method == "ner":
                query = query.filter(ExtractedSkill.extraction_method == 'ner')
            elif extraction_method == "regex":
                query = query.filter(ExtractedSkill.extraction_method == 'regex')
            elif extraction_method == "pipeline_a":
                # Pipeline A includes both ner and regex
                query = query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))
            elif extraction_method == "pipeline_b":
                # Pipeline B is LLM-based (from enhanced_skills table, but we check extraction_method patterns)
                query = query.filter(ExtractedSkill.extraction_method.like('pipeline-%'))

        # Filter by mapping status
        if mapping_status:
            if mapping_status == "esco_mapped":
                query = query.filter(ExtractedSkill.esco_uri.isnot(None))
            elif mapping_status == "unmapped":
                query = query.filter(ExtractedSkill.esco_uri.is_(None))

        # Group by skill and order by count
        query = query.group_by(
            ExtractedSkill.skill_text,
            ExtractedSkill.skill_type,
            ExtractedSkill.esco_uri
        ).order_by(func.count(ExtractedSkill.skill_text).desc())

        # Get results
        results = query.limit(limit).all()

        # Calculate total unique skills
        total_unique = db.query(func.count(distinct(ExtractedSkill.skill_text))).scalar() or 0

        # Calculate total count for percentages
        total_count = sum(r.count for r in results) if results else 1

        # Build response
        skills = [
            SkillCount(
                skill_text=r.skill_text,
                count=r.count,
                percentage=round((r.count / total_count) * 100, 2),
                type=r.skill_type,
                esco_uri=r.esco_uri
            )
            for r in results
        ]

        return TopSkillsResponse(
            total_unique=total_unique,
            skills=skills
        )

    except Exception as e:
        logger.error(f"Error getting top skills: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving skills: {str(e)}")


@router.get("/skills/search")
def search_skills(
    query: str = Query(..., min_length=2, description="Search query for skill names"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Search for skills by text.

    Args:
        query: Search text (minimum 2 characters)
        limit: Maximum results to return

    Returns:
        List of matching skills with counts
    """
    try:
        search_pattern = f"%{query}%"

        results = db.query(
            ExtractedSkill.skill_text,
            func.count(ExtractedSkill.skill_text).label('count')
        ).filter(
            ExtractedSkill.skill_text.ilike(search_pattern)
        ).group_by(
            ExtractedSkill.skill_text
        ).order_by(
            func.count(ExtractedSkill.skill_text).desc()
        ).limit(limit).all()

        return {
            "query": query,
            "results": [
                {"skill_text": r.skill_text, "count": r.count}
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error searching skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/by-type")
def get_skills_by_type(
    country: Optional[str] = Query(None, description="Filter by country"),
    db: Session = Depends(get_db)
):
    """
    Get skill distribution by type (hard vs soft).

    Args:
        country: Optional country filter

    Returns:
        Counts by skill type
    """
    try:
        query = db.query(
            ExtractedSkill.skill_type,
            func.count(ExtractedSkill.extraction_id).label('count')
        )

        if country:
            query = query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
            query = query.filter(RawJob.country == country.upper())

        results = query.group_by(ExtractedSkill.skill_type).all()

        total = sum(r.count for r in results)

        return {
            "total": total,
            "by_type": [
                {
                    "type": r.skill_type or "unknown",
                    "count": r.count,
                    "percentage": round((r.count / total) * 100, 2) if total > 0 else 0
                }
                for r in results
            ]
        }

    except Exception as e:
        logger.error(f"Error getting skills by type: {e}")
        raise HTTPException(status_code=500, detail=str(e))
