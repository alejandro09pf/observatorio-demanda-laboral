"""
Statistics Router - General system statistics and metrics.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text, exists
from typing import Dict, Any, Optional
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


@router.get("/stats/filtered")
def get_filtered_stats(
    country: Optional[str] = Query(None, description="Filter by country (CO, MX, AR)"),
    job_status: Optional[str] = Query(None, description="Filter by job status (raw, cleaned, golden)"),
    extraction_method: Optional[str] = Query(None, description="Filter skills by extraction method (ner, regex, pipeline_a, pipeline_b)"),
    mapping_status: Optional[str] = Query(None, description="Filter skills by mapping (esco_mapped, unmapped)"),
    skill_type: Optional[str] = Query(None, description="Filter by skill type (hard, soft)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics with comprehensive filters for Dashboard.

    Filters:
    - country: Country code (CO, MX, AR)
    - job_status: Job processing status (raw, cleaned, golden)
    - extraction_method: Skill extraction method (ner, regex, pipeline_a, pipeline_b)
    - mapping_status: ESCO mapping status (esco_mapped, unmapped)
    """
    try:
        # Determine which table to use for skills based on extraction_method and job_status
        use_gold_standard = (job_status == "golden")
        use_enhanced_skills = (extraction_method == "pipeline_b")

        # Build base jobs query
        jobs_query = db.query(RawJob)

        # Apply country filter to jobs
        if country:
            jobs_query = jobs_query.filter(RawJob.country == country.upper())

        # Apply job_status filter
        if job_status == "cleaned":
            jobs_query = jobs_query.filter(exists().where(CleanedJob.job_id == RawJob.job_id))
        elif job_status == "golden":
            gold_job_ids = db.execute(text("SELECT DISTINCT job_id FROM gold_standard_annotations")).fetchall()
            gold_ids = [row[0] for row in gold_job_ids]
            jobs_query = jobs_query.filter(RawJob.job_id.in_(gold_ids))

        # Apply extraction_method filter to jobs (only jobs with skills from that method)
        if extraction_method:
            if extraction_method == "manual":
                job_ids_with_method = db.execute(text("SELECT DISTINCT job_id FROM gold_standard_annotations")).fetchall()
            elif extraction_method == "pipeline_b":
                job_ids_with_method = db.execute(text("SELECT DISTINCT job_id FROM enhanced_skills")).fetchall()
            elif extraction_method == "ner":
                job_ids_with_method = db.query(distinct(ExtractedSkill.job_id)).filter(ExtractedSkill.extraction_method == 'ner').all()
            elif extraction_method == "regex":
                job_ids_with_method = db.query(distinct(ExtractedSkill.job_id)).filter(ExtractedSkill.extraction_method == 'regex').all()
            elif extraction_method == "pipeline_a":
                job_ids_with_method = db.query(distinct(ExtractedSkill.job_id)).filter(ExtractedSkill.extraction_method.in_(['ner', 'regex'])).all()

            method_job_ids = [row[0] for row in job_ids_with_method]
            jobs_query = jobs_query.filter(RawJob.job_id.in_(method_job_ids))

        # Count jobs with all filters applied
        total_jobs = jobs_query.count()

        # Get the filtered job IDs early so we can use them for extraction method counts
        filtered_job_ids = [row.job_id for row in jobs_query.all()]

        # Build skills query based on extraction method and job status
        if use_gold_standard or extraction_method == "manual":
            # Use gold_standard_annotations for golden jobs or manual method
            skills_query = None  # We'll use raw SQL for gold standard
        elif use_enhanced_skills:
            # Use enhanced_skills for pipeline_b
            skills_query = None  # We'll use raw SQL for enhanced skills
        else:
            # Use extracted_skills for pipeline_a, ner, regex
            skills_query = db.query(ExtractedSkill)

        # Calculate skills based on the appropriate table
        if use_gold_standard or extraction_method == "manual":
            # Query gold_standard_annotations
            skill_conditions = []
            skill_params = {}

            if country:
                skill_conditions.append("rj.country = :country")
                skill_params["country"] = country.upper()
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                skill_conditions.append("gsa.skill_type = :skill_type")
                skill_params["skill_type"] = skill_type.lower()
            if mapping_status:
                if mapping_status == "esco_mapped":
                    skill_conditions.append("gsa.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    skill_conditions.append("gsa.esco_concept_uri IS NULL")

            skill_query_str = "SELECT COUNT(*) as total, COUNT(DISTINCT skill_text) as unique_skills, COUNT(DISTINCT gsa.job_id) as unique_jobs FROM gold_standard_annotations gsa"
            if country:
                skill_query_str += " JOIN raw_jobs rj ON gsa.job_id = rj.job_id"
            if skill_conditions:
                skill_query_str += " WHERE " + " AND ".join(skill_conditions)

            skill_result = db.execute(text(skill_query_str), skill_params).fetchone()
            total_skills = skill_result.total if skill_result else 0
            unique_skills = skill_result.unique_skills if skill_result else 0
            unique_jobs_with_skills = skill_result.unique_jobs if skill_result else 0

        elif use_enhanced_skills:
            # Query enhanced_skills
            skill_conditions = []
            skill_params = {}

            if country:
                skill_conditions.append("rj.country = :country")
                skill_params["country"] = country.upper()
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                skill_conditions.append("es.skill_type = :skill_type")
                skill_params["skill_type"] = skill_type.lower()
            if mapping_status:
                if mapping_status == "esco_mapped":
                    skill_conditions.append("es.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    skill_conditions.append("es.esco_concept_uri IS NULL")

            skill_query_str = "SELECT COUNT(*) as total, COUNT(DISTINCT normalized_skill) as unique_skills, COUNT(DISTINCT es.job_id) as unique_jobs FROM enhanced_skills es"
            if country:
                skill_query_str += " JOIN raw_jobs rj ON es.job_id = rj.job_id"
            if skill_conditions:
                skill_query_str += " WHERE " + " AND ".join(skill_conditions)

            skill_result = db.execute(text(skill_query_str), skill_params).fetchone()
            total_skills = skill_result.total if skill_result else 0
            unique_skills = skill_result.unique_skills if skill_result else 0
            unique_jobs_with_skills = skill_result.unique_jobs if skill_result else 0

        else:
            # Use extracted_skills for pipeline_a, ner, regex
            # Join with jobs if needed for country filter
            if country:
                skills_query = skills_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
                skills_query = skills_query.filter(RawJob.country == country.upper())

            # Apply extraction_method filter
            if extraction_method:
                if extraction_method == "ner":
                    skills_query = skills_query.filter(ExtractedSkill.extraction_method == 'ner')
                elif extraction_method == "regex":
                    skills_query = skills_query.filter(ExtractedSkill.extraction_method == 'regex')
                elif extraction_method == "pipeline_a":
                    skills_query = skills_query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

            # Apply mapping_status filter
            if mapping_status:
                if mapping_status == "esco_mapped":
                    skills_query = skills_query.filter(ExtractedSkill.esco_uri.isnot(None))
                elif mapping_status == "unmapped":
                    skills_query = skills_query.filter(ExtractedSkill.esco_uri.is_(None))

            # Apply skill_type filter
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                skills_query = skills_query.filter(ExtractedSkill.skill_type == skill_type.lower())

            # Count skills
            total_skills = skills_query.count()

            # For unique counts with extracted_skills, we need to use the same filtered query
            unique_skills_query = db.query(func.count(distinct(ExtractedSkill.skill_text)))
            unique_jobs_query = db.query(func.count(distinct(ExtractedSkill.job_id)))

            # Apply same filters to unique counts
            if country:
                unique_skills_query = unique_skills_query.select_from(ExtractedSkill).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country.upper())
                unique_jobs_query = unique_jobs_query.select_from(ExtractedSkill).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country.upper())
            else:
                unique_skills_query = unique_skills_query.select_from(ExtractedSkill)
                unique_jobs_query = unique_jobs_query.select_from(ExtractedSkill)

            if extraction_method:
                if extraction_method == "ner":
                    unique_skills_query = unique_skills_query.filter(ExtractedSkill.extraction_method == 'ner')
                    unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.extraction_method == 'ner')
                elif extraction_method == "regex":
                    unique_skills_query = unique_skills_query.filter(ExtractedSkill.extraction_method == 'regex')
                    unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.extraction_method == 'regex')
                elif extraction_method == "pipeline_a":
                    unique_skills_query = unique_skills_query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))
                    unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

            if mapping_status:
                if mapping_status == "esco_mapped":
                    unique_skills_query = unique_skills_query.filter(ExtractedSkill.esco_uri.isnot(None))
                    unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.esco_uri.isnot(None))
                elif mapping_status == "unmapped":
                    unique_skills_query = unique_skills_query.filter(ExtractedSkill.esco_uri.is_(None))
                    unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.esco_uri.is_(None))

            if skill_type and skill_type.lower() in ['hard', 'soft']:
                unique_skills_query = unique_skills_query.filter(ExtractedSkill.skill_type == skill_type.lower())
                unique_jobs_query = unique_jobs_query.filter(ExtractedSkill.skill_type == skill_type.lower())

            unique_skills = unique_skills_query.scalar() or 0
            unique_jobs_with_skills = unique_jobs_query.scalar() or 0

        # Get breakdown by extraction method (always include for transparency)
        ner_count_query = db.query(func.count(ExtractedSkill.extraction_id)).filter(
            ExtractedSkill.extraction_method == 'ner'
        )
        regex_count_query = db.query(func.count(ExtractedSkill.extraction_id)).filter(
            ExtractedSkill.extraction_method == 'regex'
        )

        # Apply country filter to extraction counts if set
        if country:
            ner_count_query = ner_count_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country.upper())
            regex_count_query = regex_count_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country.upper())

        # Apply job_status filter to extraction counts (filter by filtered job IDs)
        if job_status and filtered_job_ids:
            # Join with RawJob if not already joined
            if not country:
                ner_count_query = ner_count_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
                regex_count_query = regex_count_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
            ner_count_query = ner_count_query.filter(RawJob.job_id.in_(filtered_job_ids))
            regex_count_query = regex_count_query.filter(RawJob.job_id.in_(filtered_job_ids))

        # Apply skill_type filter to extraction counts
        if skill_type and skill_type.lower() in ['hard', 'soft']:
            ner_count_query = ner_count_query.filter(ExtractedSkill.skill_type == skill_type.lower())
            regex_count_query = regex_count_query.filter(ExtractedSkill.skill_type == skill_type.lower())

        # Apply mapping_status filter to extraction counts
        if mapping_status:
            if mapping_status == "esco_mapped":
                ner_count_query = ner_count_query.filter(ExtractedSkill.esco_uri.isnot(None))
                regex_count_query = regex_count_query.filter(ExtractedSkill.esco_uri.isnot(None))
            elif mapping_status == "unmapped":
                ner_count_query = ner_count_query.filter(ExtractedSkill.esco_uri.is_(None))
                regex_count_query = regex_count_query.filter(ExtractedSkill.esco_uri.is_(None))

        ner_count = ner_count_query.scalar() or 0
        regex_count = regex_count_query.scalar() or 0

        # Count cleaned jobs with filters
        cleaned_jobs_query = db.query(func.count(CleanedJob.job_id))
        if country:
            cleaned_jobs_query = cleaned_jobs_query.join(RawJob, CleanedJob.job_id == RawJob.job_id).filter(RawJob.country == country.upper())
        total_cleaned_jobs = cleaned_jobs_query.scalar() or 0

        # Pipeline B counts (from enhanced_skills table) with filters
        pipeline_b_conditions = []
        pipeline_b_params = {}

        # Always need to join with raw_jobs for job_status filter
        needs_join = country or job_status

        if country:
            pipeline_b_conditions.append("rj.country = :country")
            pipeline_b_params["country"] = country.upper()

        # Apply job_status filter using filtered_job_ids
        if job_status and filtered_job_ids:
            # Create placeholders for SQL IN clause
            job_id_placeholders = ','.join([f':job_id_{i}' for i in range(len(filtered_job_ids))])
            pipeline_b_conditions.append(f"es.job_id IN ({job_id_placeholders})")
            for i, job_id in enumerate(filtered_job_ids):
                pipeline_b_params[f"job_id_{i}"] = job_id

        if skill_type and skill_type.lower() in ['hard', 'soft']:
            pipeline_b_conditions.append("es.skill_type = :skill_type")
            pipeline_b_params["skill_type"] = skill_type.lower()

        if mapping_status:
            if mapping_status == "esco_mapped":
                pipeline_b_conditions.append("es.esco_concept_uri IS NOT NULL")
            elif mapping_status == "unmapped":
                pipeline_b_conditions.append("es.esco_concept_uri IS NULL")

        pipeline_b_query_str = """
            SELECT COUNT(*) as total, COUNT(DISTINCT es.job_id) as unique_jobs,
                   COUNT(CASE WHEN es.llm_model = 'gemma-3-4b-instruct' THEN 1 END) as gemma_count
            FROM enhanced_skills es
        """
        if needs_join:
            pipeline_b_query_str += " JOIN raw_jobs rj ON es.job_id = rj.job_id"
        if pipeline_b_conditions:
            pipeline_b_query_str += " WHERE " + " AND ".join(pipeline_b_conditions)

        enhanced_result = db.execute(text(pipeline_b_query_str), pipeline_b_params).fetchone()

        pipeline_b_total = enhanced_result.total if enhanced_result else 0
        pipeline_b_jobs = enhanced_result.unique_jobs if enhanced_result else 0
        pipeline_b_gemma = enhanced_result.gemma_count if enhanced_result else 0

        if filtered_job_ids:
            countries_query = db.query(distinct(RawJob.country)).filter(
                RawJob.country.isnot(None),
                RawJob.job_id.in_(filtered_job_ids)
            )
            filtered_countries = [c[0] for c in countries_query.all()]

            portals_query = db.query(distinct(RawJob.portal)).filter(
                RawJob.portal.isnot(None),
                RawJob.job_id.in_(filtered_job_ids)
            )
            filtered_portals = [p[0] for p in portals_query.all()]

            # Date range from filtered jobs
            date_stats_query = db.query(
                func.min(RawJob.posted_date).label('start'),
                func.max(RawJob.posted_date).label('end')
            ).filter(RawJob.job_id.in_(filtered_job_ids))
            date_stats = date_stats_query.first()
        else:
            filtered_countries = []
            filtered_portals = []
            date_stats = None

        return {
            "filters": {
                "country": country,
                "job_status": job_status,
                "extraction_method": extraction_method,
                "mapping_status": mapping_status,
                "skill_type": skill_type
            },
            "jobs": {
                "total": total_jobs,
                "cleaned": total_cleaned_jobs,
                "with_skills": unique_jobs_with_skills
            },
            "skills": {
                "total": total_skills,
                "unique": unique_skills
            },
            "extraction_methods": {
                "ner": ner_count,
                "regex": regex_count,
                "pipeline_a": ner_count + regex_count,
                "pipeline_b_total": pipeline_b_total,
                "pipeline_b_gemma": pipeline_b_gemma,
                "pipeline_b_jobs": pipeline_b_jobs
            },
            "countries": sorted(filtered_countries),
            "portals": sorted(filtered_portals),
            "date_range": {
                "start": date_stats.start if date_stats else None,
                "end": date_stats.end if date_stats else None
            }
        }

    except Exception as e:
        logger.error(f"Error getting filtered stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving filtered statistics: {str(e)}")


@router.get("/stats/by-country")
def get_stats_by_country(
    extraction_method: Optional[str] = Query(None, description="Filter by extraction method"),
    job_status: Optional[str] = Query(None, description="Filter by job status"),
    mapping_status: Optional[str] = Query(None, description="Filter by mapping status"),
    skill_type: Optional[str] = Query(None, description="Filter by skill type (hard, soft)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get statistics broken down by country with optional filters.

    Returns:
        Dictionary with per-country stats
    """
    try:
        countries = ['AR', 'CO', 'MX']
        country_stats = {}

        for country_code in countries:
            # Build jobs query with filters
            jobs_query = db.query(RawJob).filter(RawJob.country == country_code)

            # Apply job_status filter
            if job_status == "cleaned":
                jobs_query = jobs_query.filter(exists().where(CleanedJob.job_id == RawJob.job_id))
            elif job_status == "golden":
                gold_job_ids = db.execute(text("SELECT DISTINCT job_id FROM gold_standard_annotations")).fetchall()
                gold_ids = [row[0] for row in gold_job_ids]
                jobs_query = jobs_query.filter(RawJob.job_id.in_(gold_ids))

            # Apply extraction_method filter to jobs (only jobs with skills from that method)
            if extraction_method:
                if extraction_method == "manual":
                    method_job_ids_query = db.execute(text("SELECT DISTINCT job_id FROM gold_standard_annotations WHERE job_id IN (SELECT job_id FROM raw_jobs WHERE country = :country)"), {"country": country_code})
                    method_job_ids = [row[0] for row in method_job_ids_query.fetchall()]
                    jobs_query = jobs_query.filter(RawJob.job_id.in_(method_job_ids)) if method_job_ids else jobs_query.filter(RawJob.job_id.in_([]))
                elif extraction_method == "pipeline_b":
                    method_job_ids_query = db.execute(text("SELECT DISTINCT job_id FROM enhanced_skills WHERE job_id IN (SELECT job_id FROM raw_jobs WHERE country = :country)"), {"country": country_code})
                    method_job_ids = [row[0] for row in method_job_ids_query.fetchall()]
                    jobs_query = jobs_query.filter(RawJob.job_id.in_(method_job_ids)) if method_job_ids else jobs_query.filter(RawJob.job_id.in_([]))
                elif extraction_method in ["ner", "regex", "pipeline_a"]:
                    if extraction_method == "ner":
                        method_job_ids = db.query(distinct(ExtractedSkill.job_id)).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country_code, ExtractedSkill.extraction_method == 'ner').all()
                    elif extraction_method == "regex":
                        method_job_ids = db.query(distinct(ExtractedSkill.job_id)).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country_code, ExtractedSkill.extraction_method == 'regex').all()
                    elif extraction_method == "pipeline_a":
                        method_job_ids = db.query(distinct(ExtractedSkill.job_id)).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country_code, ExtractedSkill.extraction_method.in_(['ner', 'regex'])).all()
                    method_ids = [row[0] for row in method_job_ids]
                    jobs_query = jobs_query.filter(RawJob.job_id.in_(method_ids)) if method_ids else jobs_query.filter(RawJob.job_id.in_([]))

            total_jobs = jobs_query.count()

            # Query skills from the appropriate table based on extraction_method
            if extraction_method == "manual":
                # Use gold_standard_annotations
                skill_conditions = ["rj.country = :country"]
                skill_params = {"country": country_code}

                if skill_type and skill_type.lower() in ['hard', 'soft']:
                    skill_conditions.append("gsa.skill_type = :skill_type")
                    skill_params["skill_type"] = skill_type.lower()

                if mapping_status:
                    if mapping_status == "esco_mapped":
                        skill_conditions.append("gsa.esco_concept_uri IS NOT NULL")
                    elif mapping_status == "unmapped":
                        skill_conditions.append("gsa.esco_concept_uri IS NULL")

                skill_query_str = f"SELECT COUNT(*) as total, COUNT(DISTINCT skill_text) as unique_skills FROM gold_standard_annotations gsa JOIN raw_jobs rj ON gsa.job_id = rj.job_id WHERE {' AND '.join(skill_conditions)}"
                skill_result = db.execute(text(skill_query_str), skill_params).fetchone()
                total_skills = skill_result.total if skill_result else 0
                unique_skills_count = skill_result.unique_skills if skill_result else 0

            elif extraction_method == "pipeline_b":
                # Use enhanced_skills
                skill_conditions = ["rj.country = :country"]
                skill_params = {"country": country_code}

                if skill_type and skill_type.lower() in ['hard', 'soft']:
                    skill_conditions.append("es.skill_type = :skill_type")
                    skill_params["skill_type"] = skill_type.lower()

                if mapping_status:
                    if mapping_status == "esco_mapped":
                        skill_conditions.append("es.esco_concept_uri IS NOT NULL")
                    elif mapping_status == "unmapped":
                        skill_conditions.append("es.esco_concept_uri IS NULL")

                skill_query_str = f"SELECT COUNT(*) as total, COUNT(DISTINCT normalized_skill) as unique_skills FROM enhanced_skills es JOIN raw_jobs rj ON es.job_id = rj.job_id WHERE {' AND '.join(skill_conditions)}"
                skill_result = db.execute(text(skill_query_str), skill_params).fetchone()
                total_skills = skill_result.total if skill_result else 0
                unique_skills_count = skill_result.unique_skills if skill_result else 0

            else:
                # Use extracted_skills (default for pipeline_a, ner, regex, or no filter)
                skills_query = db.query(ExtractedSkill).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country_code)

                # Apply extraction_method filter
                if extraction_method:
                    if extraction_method == "ner":
                        skills_query = skills_query.filter(ExtractedSkill.extraction_method == 'ner')
                    elif extraction_method == "regex":
                        skills_query = skills_query.filter(ExtractedSkill.extraction_method == 'regex')
                    elif extraction_method == "pipeline_a":
                        skills_query = skills_query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

                # Apply skill_type filter
                if skill_type and skill_type.lower() in ['hard', 'soft']:
                    skills_query = skills_query.filter(ExtractedSkill.skill_type == skill_type.lower())

                # Apply mapping_status filter
                if mapping_status:
                    if mapping_status == "esco_mapped":
                        skills_query = skills_query.filter(ExtractedSkill.esco_uri.isnot(None))
                    elif mapping_status == "unmapped":
                        skills_query = skills_query.filter(ExtractedSkill.esco_uri.is_(None))

                total_skills = skills_query.count()

                # Get unique skills count
                unique_skills = db.query(func.count(distinct(ExtractedSkill.skill_text))).select_from(ExtractedSkill).join(RawJob, ExtractedSkill.job_id == RawJob.job_id).filter(RawJob.country == country_code)

                if extraction_method:
                    if extraction_method == "ner":
                        unique_skills = unique_skills.filter(ExtractedSkill.extraction_method == 'ner')
                    elif extraction_method == "regex":
                        unique_skills = unique_skills.filter(ExtractedSkill.extraction_method == 'regex')
                    elif extraction_method == "pipeline_a":
                        unique_skills = unique_skills.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

                if skill_type and skill_type.lower() in ['hard', 'soft']:
                    unique_skills = unique_skills.filter(ExtractedSkill.skill_type == skill_type.lower())

                if mapping_status:
                    if mapping_status == "esco_mapped":
                        unique_skills = unique_skills.filter(ExtractedSkill.esco_uri.isnot(None))
                    elif mapping_status == "unmapped":
                        unique_skills = unique_skills.filter(ExtractedSkill.esco_uri.is_(None))

                unique_skills_count = unique_skills.scalar() or 0

            country_stats[country_code] = {
                "country": country_code,
                "total_jobs": total_jobs,
                "total_skills": total_skills,
                "unique_skills": unique_skills_count
            }

        return {
            "countries": country_stats,
            "filters": {
                "extraction_method": extraction_method,
                "job_status": job_status,
                "mapping_status": mapping_status,
                "skill_type": skill_type
            }
        }

    except Exception as e:
        logger.error(f"Error getting stats by country: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving country statistics: {str(e)}")
