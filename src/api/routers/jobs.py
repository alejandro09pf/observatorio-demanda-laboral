"""
Jobs Router - CRUD operations for job postings.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import Optional, List
from uuid import UUID
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.dependencies import get_db
from api.schemas.job import JobBase, JobDetail, JobListResponse, ExtractedSkillSchema
from database.models import RawJob, ExtractedSkill

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/jobs", response_model=JobListResponse)
def get_jobs(
    country: Optional[str] = Query(None, description="Filter by country code (e.g., CO, MX, AR)"),
    portal: Optional[str] = Query(None, description="Filter by job portal"),
    limit: int = Query(50, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    search: Optional[str] = Query(None, description="Search in title or description"),
    db: Session = Depends(get_db)
) -> JobListResponse:
    """
    Get a paginated list of job postings with optional filters.

    Filters:
    - country: Country code (CO, MX, AR, etc.)
    - portal: Job portal (computrabajo, bumeran, indeed, etc.)
    - search: Search text in title or description
    - limit: Results per page (1-100, default 50)
    - offset: Pagination offset (default 0)
    """
    try:
        # Build base query
        query = db.query(RawJob)

        # Apply filters
        if country:
            query = query.filter(RawJob.country == country.upper())

        if portal:
            query = query.filter(RawJob.portal == portal.lower())

        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    RawJob.title.ilike(search_pattern),
                    RawJob.description.ilike(search_pattern),
                    RawJob.company.ilike(search_pattern)
                )
            )

        # Get total count
        total = query.count()

        # Apply pagination and ordering
        jobs = query.order_by(RawJob.scraped_at.desc()).offset(offset).limit(limit).all()

        # Convert to response models
        jobs_response = [JobBase.model_validate(job) for job in jobs]

        return JobListResponse(
            total=total,
            limit=limit,
            offset=offset,
            jobs=jobs_response
        )

    except Exception as e:
        logger.error(f"Error getting jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving jobs: {str(e)}")


@router.get("/jobs/{job_id}", response_model=JobDetail)
def get_job_detail(
    job_id: UUID,
    db: Session = Depends(get_db)
) -> JobDetail:
    """
    Get detailed information about a specific job, including extracted skills.

    Args:
        job_id: UUID of the job posting

    Returns:
        JobDetail with full description, requirements, and extracted skills
    """
    try:
        # Query job
        job = db.query(RawJob).filter(RawJob.job_id == job_id).first()

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Query extracted skills for this job
        skills = db.query(ExtractedSkill).filter(
            ExtractedSkill.job_id == job_id
        ).all()

        # Convert to dict
        job_dict = {
            "job_id": job.job_id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "country": job.country,
            "portal": job.portal,
            "posted_date": job.posted_date,
            "scraped_at": job.scraped_at,
            "url": job.url,
            "salary_raw": job.salary_raw,
            "contract_type": job.contract_type,
            "remote_type": job.remote_type,
            "description": job.description,
            "requirements": job.requirements,
            "extracted_skills": [
                {
                    "skill_text": skill.skill_text,
                    "skill_type": skill.skill_type,
                    "extraction_method": skill.extraction_method,
                    "confidence_score": skill.confidence_score,
                    "esco_uri": skill.esco_uri
                }
                for skill in skills
            ]
        }

        return JobDetail(**job_dict)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job detail: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving job: {str(e)}")


@router.get("/jobs/country/{country_code}")
def get_jobs_by_country(
    country_code: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get jobs for a specific country.

    Quick endpoint for country-specific queries.
    """
    try:
        jobs = db.query(RawJob).filter(
            RawJob.country == country_code.upper()
        ).order_by(RawJob.scraped_at.desc()).limit(limit).all()

        return {
            "country": country_code.upper(),
            "count": len(jobs),
            "jobs": [JobBase.model_validate(job) for job in jobs]
        }

    except Exception as e:
        logger.error(f"Error getting jobs by country: {e}")
        raise HTTPException(status_code=500, detail=str(e))
