"""
Skills Router - Skill analysis and aggregations.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct, text
from typing import Optional
import logging

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.dependencies import get_db
from api.schemas.skill import SkillCount, TopSkillsResponse
from database.models import ExtractedSkill, RawJob

logger = logging.getLogger(__name__)

# Import EnhancedSkill dynamically to avoid circular imports
try:
    from database.models import EnhancedSkill
except ImportError:
    EnhancedSkill = None

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
        # Manual uses gold_standard_annotations table
        if extraction_method == "manual":
            # Query gold_standard_annotations table
            query_str = """
                SELECT
                    skill_text,
                    skill_type,
                    esco_concept_uri as esco_uri,
                    COUNT(*) as count
                FROM gold_standard_annotations gsa
            """

            conditions = []
            params = {}

            # Join with jobs if filtering by country
            if country:
                query_str += " JOIN raw_jobs rj ON gsa.job_id = rj.job_id"
                conditions.append("rj.country = :country")
                params["country"] = country.upper()

            # Filter by skill type
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                conditions.append("gsa.skill_type = :skill_type")
                params["skill_type"] = skill_type.lower()

            # Filter by mapping status
            if mapping_status:
                if mapping_status == "esco_mapped":
                    conditions.append("gsa.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    conditions.append("gsa.esco_concept_uri IS NULL")

            # Add WHERE clause if there are conditions
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

            query_str += """
                GROUP BY skill_text, skill_type, esco_concept_uri
                ORDER BY count DESC
                LIMIT :limit
            """
            params["limit"] = limit

            results = db.execute(text(query_str), params).fetchall()

            # Get total unique skills from gold_standard_annotations
            total_unique_query = "SELECT COUNT(DISTINCT skill_text) FROM gold_standard_annotations"
            total_unique = db.execute(text(total_unique_query)).scalar() or 0

        # Pipeline B uses enhanced_skills table
        elif extraction_method == "pipeline_b":
            # Query enhanced_skills table
            query_str = """
                SELECT
                    normalized_skill as skill_text,
                    skill_type,
                    esco_concept_uri as esco_uri,
                    COUNT(*) as count
                FROM enhanced_skills es
            """

            conditions = []
            params = {}

            # Join with jobs if filtering by country
            if country:
                query_str += " JOIN raw_jobs rj ON es.job_id = rj.job_id"
                conditions.append("rj.country = :country")
                params["country"] = country.upper()

            # Filter by skill type
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                conditions.append("es.skill_type = :skill_type")
                params["skill_type"] = skill_type.lower()

            # Filter by mapping status
            if mapping_status:
                if mapping_status == "esco_mapped":
                    conditions.append("es.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    conditions.append("es.esco_concept_uri IS NULL")

            # Add WHERE clause if there are conditions
            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)

            query_str += """
                GROUP BY normalized_skill, skill_type, esco_concept_uri
                ORDER BY count DESC
                LIMIT :limit
            """
            params["limit"] = limit

            results = db.execute(text(query_str), params).fetchall()

            # Get total unique skills from enhanced_skills
            total_unique_query = "SELECT COUNT(DISTINCT normalized_skill) FROM enhanced_skills"
            total_unique = db.execute(text(total_unique_query)).scalar() or 0

        else:
            # Original logic for extracted_skills (Pipeline A, NER, Regex)
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


@router.get("/skills/search", response_model=TopSkillsResponse)
def search_skills(
    query: str = Query("", description="Search query for skill names (empty for all)"),
    country: Optional[str] = Query(None, description="Filter by country code"),
    skill_type: Optional[str] = Query(None, description="Filter by skill type (hard, soft)"),
    extraction_method: Optional[str] = Query(None, description="Filter by extraction method (ner, regex, pipeline_a, pipeline_b, manual)"),
    mapping_status: Optional[str] = Query(None, description="Filter by mapping status (esco_mapped, unmapped)"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=100, description="Results per page"),
    db: Session = Depends(get_db)
):
    """
    Search for skills by text with pagination and filters.

    Args:
        query: Search text (empty for all skills)
        country: Filter by country (CO, MX, AR, etc.)
        skill_type: Filter by skill type (hard, soft)
        extraction_method: Filter by extraction method (ner, regex, pipeline_a, pipeline_b, manual)
        mapping_status: Filter by ESCO mapping status (esco_mapped, unmapped)
        page: Page number (1-indexed)
        page_size: Results per page (1-100)

    Returns:
        TopSkillsResponse with matching skills and pagination info
    """
    try:
        search_pattern = f"%{query}%" if query else "%"
        offset = (page - 1) * page_size

        # Manual uses gold_standard_annotations table
        if extraction_method == "manual":
            query_str = """
                SELECT
                    skill_text,
                    skill_type,
                    esco_concept_uri as esco_uri,
                    COUNT(*) as count
                FROM gold_standard_annotations gsa
            """

            conditions = []
            if query:  # Only add LIKE condition if there's a search query
                conditions.append("LOWER(skill_text) LIKE LOWER(:search_pattern)")
            params = {"search_pattern": search_pattern, "limit": page_size, "offset": offset}

            # Join with jobs if filtering by country
            if country:
                query_str += " JOIN raw_jobs rj ON gsa.job_id = rj.job_id"
                conditions.append("rj.country = :country")
                params["country"] = country.upper()

            # Filter by skill type
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                conditions.append("gsa.skill_type = :skill_type")
                params["skill_type"] = skill_type.lower()

            # Filter by mapping status
            if mapping_status:
                if mapping_status == "esco_mapped":
                    conditions.append("gsa.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    conditions.append("gsa.esco_concept_uri IS NULL")

            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)
            query_str += """
                GROUP BY skill_text, skill_type, esco_concept_uri
                ORDER BY count DESC
                LIMIT :limit OFFSET :offset
            """

            results = db.execute(text(query_str), params).fetchall()

            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(DISTINCT skill_text)
                FROM gold_standard_annotations gsa
                {' JOIN raw_jobs rj ON gsa.job_id = rj.job_id' if country else ''}
                {' WHERE ' + ' AND '.join(conditions) if conditions else ''}
            """
            total_unique = db.execute(text(count_query), params).scalar() or 0

        # Pipeline B uses enhanced_skills table
        elif extraction_method == "pipeline_b":
            query_str = """
                SELECT
                    normalized_skill as skill_text,
                    skill_type,
                    esco_concept_uri as esco_uri,
                    COUNT(*) as count
                FROM enhanced_skills es
            """

            conditions = []
            if query:  # Only add LIKE condition if there's a search query
                conditions.append("LOWER(normalized_skill) LIKE LOWER(:search_pattern)")
            params = {"search_pattern": search_pattern, "limit": page_size, "offset": offset}

            # Join with jobs if filtering by country
            if country:
                query_str += " JOIN raw_jobs rj ON es.job_id = rj.job_id"
                conditions.append("rj.country = :country")
                params["country"] = country.upper()

            # Filter by skill type
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                conditions.append("es.skill_type = :skill_type")
                params["skill_type"] = skill_type.lower()

            # Filter by mapping status
            if mapping_status:
                if mapping_status == "esco_mapped":
                    conditions.append("es.esco_concept_uri IS NOT NULL")
                elif mapping_status == "unmapped":
                    conditions.append("es.esco_concept_uri IS NULL")

            if conditions:
                query_str += " WHERE " + " AND ".join(conditions)
            query_str += """
                GROUP BY normalized_skill, skill_type, esco_concept_uri
                ORDER BY count DESC
                LIMIT :limit OFFSET :offset
            """

            results = db.execute(text(query_str), params).fetchall()

            # Get total count for pagination
            count_query = f"""
                SELECT COUNT(DISTINCT normalized_skill)
                FROM enhanced_skills es
                {' JOIN raw_jobs rj ON es.job_id = rj.job_id' if country else ''}
                {' WHERE ' + ' AND '.join(conditions) if conditions else ''}
            """
            total_unique = db.execute(text(count_query), params).scalar() or 0

        else:
            # Original logic for extracted_skills (Pipeline A, NER, Regex)
            base_query = db.query(
                ExtractedSkill.skill_text,
                ExtractedSkill.skill_type,
                ExtractedSkill.esco_uri,
                func.count(ExtractedSkill.skill_text).label('count')
            )

            # Only filter by search pattern if query is provided
            if query:
                base_query = base_query.filter(ExtractedSkill.skill_text.ilike(search_pattern))

            # Join with jobs if filtering by country
            if country:
                base_query = base_query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
                base_query = base_query.filter(RawJob.country == country.upper())

            # Filter by skill type
            if skill_type and skill_type.lower() in ['hard', 'soft']:
                base_query = base_query.filter(ExtractedSkill.skill_type == skill_type.lower())

            # Filter by extraction method
            if extraction_method:
                if extraction_method == "ner":
                    base_query = base_query.filter(ExtractedSkill.extraction_method == 'ner')
                elif extraction_method == "regex":
                    base_query = base_query.filter(ExtractedSkill.extraction_method == 'regex')
                elif extraction_method == "pipeline_a":
                    base_query = base_query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

            # Filter by mapping status
            if mapping_status:
                if mapping_status == "esco_mapped":
                    base_query = base_query.filter(ExtractedSkill.esco_uri.isnot(None))
                elif mapping_status == "unmapped":
                    base_query = base_query.filter(ExtractedSkill.esco_uri.is_(None))

            # Group by skill and order by count
            query_with_group = base_query.group_by(
                ExtractedSkill.skill_text,
                ExtractedSkill.skill_type,
                ExtractedSkill.esco_uri
            ).order_by(func.count(ExtractedSkill.skill_text).desc())

            # Get results with pagination
            results = query_with_group.limit(page_size).offset(offset).all()

            # Calculate total unique skills matching search
            count_query = db.query(func.count(distinct(ExtractedSkill.skill_text)))
            if query:
                count_query = count_query.filter(ExtractedSkill.skill_text.ilike(search_pattern))
            total_unique = count_query.scalar() or 0

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
            skills=skills,
            page=page,
            page_size=page_size,
            total_pages=(total_unique + page_size - 1) // page_size if total_unique > 0 else 0
        )

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


@router.get("/skills/detail")
def get_skill_detail(
    skill_text: str = Query(..., description="Exact skill text to get details for"),
    extraction_method: Optional[str] = Query(None, description="Filter by extraction method (ner, regex, pipeline_a, pipeline_b, manual)"),
    country: Optional[str] = Query(None, description="Filter by country code"),
    limit_jobs: int = Query(20, ge=1, le=100, description="Number of jobs to return"),
    limit_cooccurring: int = Query(10, ge=1, le=50, description="Number of co-occurring skills to return"),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific skill.

    Returns:
    - Skill metadata (type, total count, ESCO URI)
    - Co-occurring skills (skills that appear in the same jobs)
    - Jobs that contain this skill
    - Country distribution

    Args:
        skill_text: Exact skill text to search for
        extraction_method: Optional filter (ner, regex, pipeline_a, pipeline_b, manual)
        country: Optional country filter
        limit_jobs: Number of jobs to return
        limit_cooccurring: Number of co-occurring skills to return
    """
    try:
        # Determine which table(s) to query based on extraction_method
        skill_info = None
        job_ids = []

        # Manual uses gold_standard_annotations
        if extraction_method == "manual":
            query_str = """
                SELECT skill_text, skill_type, esco_concept_uri as esco_uri, COUNT(*) as count,
                       ARRAY_AGG(DISTINCT job_id) as job_ids
                FROM gold_standard_annotations
                WHERE LOWER(skill_text) = LOWER(:skill_text)
            """
            params = {"skill_text": skill_text}

            if country:
                query_str = """
                    SELECT gsa.skill_text, gsa.skill_type, gsa.esco_concept_uri as esco_uri,
                           COUNT(*) as count, ARRAY_AGG(DISTINCT gsa.job_id) as job_ids
                    FROM gold_standard_annotations gsa
                    JOIN raw_jobs rj ON gsa.job_id = rj.job_id
                    WHERE LOWER(gsa.skill_text) = LOWER(:skill_text) AND rj.country = :country
                """
                params["country"] = country.upper()

            query_str += " GROUP BY skill_text, skill_type, esco_concept_uri"
            result = db.execute(text(query_str), params).fetchone()

        # Pipeline B uses enhanced_skills
        elif extraction_method == "pipeline_b":
            query_str = """
                SELECT normalized_skill as skill_text, skill_type, esco_concept_uri as esco_uri,
                       COUNT(*) as count, ARRAY_AGG(DISTINCT job_id) as job_ids
                FROM enhanced_skills
                WHERE LOWER(normalized_skill) = LOWER(:skill_text)
            """
            params = {"skill_text": skill_text}

            if country:
                query_str = """
                    SELECT es.normalized_skill as skill_text, es.skill_type,
                           es.esco_concept_uri as esco_uri, COUNT(*) as count,
                           ARRAY_AGG(DISTINCT es.job_id) as job_ids
                    FROM enhanced_skills es
                    JOIN raw_jobs rj ON es.job_id = rj.job_id
                    WHERE LOWER(es.normalized_skill) = LOWER(:skill_text) AND rj.country = :country
                """
                params["country"] = country.upper()

            query_str += " GROUP BY normalized_skill, skill_type, esco_concept_uri"
            result = db.execute(text(query_str), params).fetchone()

        # Pipeline A / NER / Regex use extracted_skills
        else:
            query = db.query(
                ExtractedSkill.skill_text,
                ExtractedSkill.skill_type,
                ExtractedSkill.esco_uri,
                func.count(ExtractedSkill.extraction_id).label('count'),
                func.array_agg(distinct(ExtractedSkill.job_id)).label('job_ids')
            ).filter(func.lower(ExtractedSkill.skill_text) == skill_text.lower())

            if extraction_method:
                if extraction_method == "ner":
                    query = query.filter(ExtractedSkill.extraction_method == 'ner')
                elif extraction_method == "regex":
                    query = query.filter(ExtractedSkill.extraction_method == 'regex')
                elif extraction_method == "pipeline_a":
                    query = query.filter(ExtractedSkill.extraction_method.in_(['ner', 'regex']))

            if country:
                query = query.join(RawJob, ExtractedSkill.job_id == RawJob.job_id)
                query = query.filter(RawJob.country == country.upper())

            query = query.group_by(
                ExtractedSkill.skill_text,
                ExtractedSkill.skill_type,
                ExtractedSkill.esco_uri
            )

            result = query.first()

        if not result:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_text}' not found")

        skill_info = {
            "skill_text": result.skill_text,
            "skill_type": result.skill_type,
            "esco_uri": result.esco_uri,
            "total_count": result.count,
            "extraction_method": extraction_method or "all"
        }

        job_ids = result.job_ids if result.job_ids else []

        # Get co-occurring skills (skills that appear in the same jobs)
        if job_ids:
            # Query all skills from the same jobs, grouped by skill_text
            if extraction_method == "manual":
                cooccur_query = text("""
                    SELECT skill_text, skill_type, COUNT(*) as count
                    FROM gold_standard_annotations
                    WHERE job_id = ANY(:job_ids) AND LOWER(skill_text) != LOWER(:skill_text)
                    GROUP BY skill_text, skill_type
                    ORDER BY count DESC
                    LIMIT :limit
                """)
                cooccur_results = db.execute(cooccur_query, {
                    "job_ids": job_ids,
                    "skill_text": skill_text,
                    "limit": limit_cooccurring
                }).fetchall()

            elif extraction_method == "pipeline_b":
                cooccur_query = text("""
                    SELECT normalized_skill as skill_text, skill_type, COUNT(*) as count
                    FROM enhanced_skills
                    WHERE job_id = ANY(:job_ids) AND LOWER(normalized_skill) != LOWER(:skill_text)
                    GROUP BY normalized_skill, skill_type
                    ORDER BY count DESC
                    LIMIT :limit
                """)
                cooccur_results = db.execute(cooccur_query, {
                    "job_ids": job_ids,
                    "skill_text": skill_text,
                    "limit": limit_cooccurring
                }).fetchall()

            else:
                cooccur_results = db.query(
                    ExtractedSkill.skill_text,
                    ExtractedSkill.skill_type,
                    func.count(ExtractedSkill.extraction_id).label('count')
                ).filter(
                    ExtractedSkill.job_id.in_(job_ids),
                    func.lower(ExtractedSkill.skill_text) != skill_text.lower()
                ).group_by(
                    ExtractedSkill.skill_text,
                    ExtractedSkill.skill_type
                ).order_by(
                    func.count(ExtractedSkill.extraction_id).desc()
                ).limit(limit_cooccurring).all()

            cooccurring_skills = [
                {
                    "skill_text": r.skill_text,
                    "skill_type": r.skill_type,
                    "cooccurrence_count": r.count
                }
                for r in cooccur_results
            ]
        else:
            cooccurring_skills = []

        # Get jobs that contain this skill (with full job details)
        from api.schemas.job import JobBase

        jobs_with_skill = db.query(RawJob).filter(
            RawJob.job_id.in_(job_ids[:limit_jobs])
        ).order_by(RawJob.scraped_at.desc()).all()

        jobs_list = [JobBase.model_validate(job) for job in jobs_with_skill]

        # Get country distribution for this skill
        if extraction_method == "manual":
            country_query = text("""
                SELECT rj.country, COUNT(DISTINCT gsa.job_id) as count
                FROM gold_standard_annotations gsa
                JOIN raw_jobs rj ON gsa.job_id = rj.job_id
                WHERE LOWER(gsa.skill_text) = LOWER(:skill_text)
                GROUP BY rj.country
                ORDER BY count DESC
            """)
            country_results = db.execute(country_query, {"skill_text": skill_text}).fetchall()

        elif extraction_method == "pipeline_b":
            country_query = text("""
                SELECT rj.country, COUNT(DISTINCT es.job_id) as count
                FROM enhanced_skills es
                JOIN raw_jobs rj ON es.job_id = rj.job_id
                WHERE LOWER(es.normalized_skill) = LOWER(:skill_text)
                GROUP BY rj.country
                ORDER BY count DESC
            """)
            country_results = db.execute(country_query, {"skill_text": skill_text}).fetchall()

        else:
            country_results = db.query(
                RawJob.country,
                func.count(distinct(ExtractedSkill.job_id)).label('count')
            ).join(
                ExtractedSkill, RawJob.job_id == ExtractedSkill.job_id
            ).filter(
                func.lower(ExtractedSkill.skill_text) == skill_text.lower()
            ).group_by(RawJob.country).order_by(
                func.count(distinct(ExtractedSkill.job_id)).desc()
            ).all()

        country_distribution = [
            {"country": r.country, "count": r.count}
            for r in country_results
        ]

        return {
            "skill": skill_info,
            "cooccurring_skills": cooccurring_skills,
            "jobs": jobs_list,
            "total_jobs": len(job_ids),
            "country_distribution": country_distribution
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting skill detail: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving skill details: {str(e)}")
