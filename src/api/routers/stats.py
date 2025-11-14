"""
Statistics Router - General system statistics and metrics.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct
from typing import Dict, Any
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.dependencies import get_db
from api.schemas.stats import StatsResponse, DateRange, ExtractionMethodsBreakdown
from database.models import RawJob, ExtractedSkill, AnalysisResult, CleanedJob

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats", response_model=StatsResponse)
def get_general_stats(db: Session = Depends(get_db)) -> StatsResponse:
    """
    Get general statistics about the observatory.

    Returns counts of jobs, skills, clusters, countries, etc.
    """
    try:
        # Funnel de datos
        total_raw_jobs = db.query(func.count(RawJob.job_id)).scalar() or 0
        total_cleaned_jobs = db.query(func.count(CleanedJob.job_id)).scalar() or 0
        total_jobs_with_skills = db.query(func.count(distinct(ExtractedSkill.job_id))).scalar() or 0

        # Total skills (all extractions)
        total_skills = db.query(func.count(ExtractedSkill.extraction_id)).scalar() or 0

        # Unique skills
        total_unique_skills = db.query(func.count(distinct(ExtractedSkill.skill_text))).scalar() or 0

        # Extraction methods breakdown - Pipeline A (NER + Regex combined)
        ner_count = db.query(func.count(ExtractedSkill.extraction_id)).filter(
            ExtractedSkill.extraction_method == 'ner'
        ).scalar() or 0

        regex_count = db.query(func.count(ExtractedSkill.extraction_id)).filter(
            ExtractedSkill.extraction_method == 'regex'
        ).scalar() or 0

        pipeline_a_count = ner_count + regex_count

        # Pipeline B (LLM enhanced skills) - using raw SQL since EnhancedSkill model might not be loaded
        from sqlalchemy import text
        enhanced_result = db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(DISTINCT job_id) as unique_jobs,
                COUNT(CASE WHEN llm_model = 'gemma-3-4b-instruct' THEN 1 END) as gemma_count
            FROM enhanced_skills
        """)).fetchone()

        pipeline_b_count = enhanced_result.total if enhanced_result else 0
        pipeline_b_jobs = enhanced_result.unique_jobs if enhanced_result else 0
        gemma_count = enhanced_result.gemma_count if enhanced_result else 0

        extraction_methods = ExtractionMethodsBreakdown(
            ner=ner_count,
            regex=regex_count,
            pipeline_a1=pipeline_a_count,
            pipeline_b_total=pipeline_b_count,
            pipeline_b_gemma=gemma_count,
            pipeline_b_jobs=pipeline_b_jobs
        )

        # Number of clustering analyses
        n_clusters_query = db.query(AnalysisResult).filter(
            AnalysisResult.analysis_type == 'clustering'
        ).first()
        n_clusters = 0
        if n_clusters_query and n_clusters_query.results:
            n_clusters = n_clusters_query.results.get('metrics', {}).get('n_clusters', 0)

        # Countries with jobs
        countries = db.query(distinct(RawJob.country)).filter(
            RawJob.country.isnot(None)
        ).all()
        countries_list = [c[0] for c in countries]
        n_countries = len(countries_list)

        # Portals with jobs
        portals = db.query(distinct(RawJob.portal)).filter(
            RawJob.portal.isnot(None)
        ).all()
        portals_list = [p[0] for p in portals]

        # Date range of jobs
        date_stats = db.query(
            func.min(RawJob.posted_date).label('start'),
            func.max(RawJob.posted_date).label('end')
        ).first()

        date_range = DateRange(
            start=date_stats.start if date_stats else None,
            end=date_stats.end if date_stats else None
        )

        # Last scraping timestamp
        last_scraping = db.query(func.max(RawJob.scraped_at)).scalar()

        return StatsResponse(
            total_raw_jobs=total_raw_jobs,
            total_cleaned_jobs=total_cleaned_jobs,
            total_jobs_with_skills=total_jobs_with_skills,
            total_skills=total_skills,
            total_unique_skills=total_unique_skills,
            extraction_methods=extraction_methods,
            n_clusters=n_clusters,
            n_countries=n_countries,
            countries=sorted(countries_list),
            portals=sorted(portals_list),
            date_range=date_range,
            last_scraping=last_scraping
        )

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")


@router.get("/stats/summary")
def get_stats_summary(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get a quick summary of key metrics (lighter version).
    """
    try:
        total_jobs = db.query(func.count(RawJob.job_id)).scalar() or 0
        total_skills = db.query(func.count(distinct(ExtractedSkill.skill_text))).scalar() or 0

        return {
            "total_jobs": total_jobs,
            "total_unique_skills": total_skills,
            "status": "operational"
        }

    except Exception as e:
        logger.error(f"Error getting summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
