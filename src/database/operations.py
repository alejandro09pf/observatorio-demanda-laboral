from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
import os
from .models import Base, RawJob, ExtractedSkill, EnhancedSkill, SkillEmbedding, AnalysisResult
import hashlib
import logging

logger = logging.getLogger(__name__)

class DatabaseOperations:
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        self.engine = create_engine(
            self.database_url,
            pool_size=20,
            max_overflow=0,
            pool_pre_ping=True
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
    
    def insert_job(self, job_data: Dict[str, Any]) -> Optional[str]:
        """Insert a new job posting."""
        session = self.get_session()
        try:
            # Generate content hash
            content = f"{job_data['title']}{job_data['description']}{job_data.get('requirements', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            job = RawJob(
                **job_data,
                content_hash=content_hash
            )
            session.add(job)
            session.commit()
            
            job_id = str(job.job_id)
            logger.info(f"Inserted job {job_id}")
            return job_id
            
        except IntegrityError:
            session.rollback()
            logger.warning(f"Duplicate job detected: {job_data['url']}")
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting job: {e}")
            raise
        finally:
            session.close()
    
    def get_unprocessed_jobs(self, limit: int = 100) -> List[RawJob]:
        """Get unprocessed job postings."""
        session = self.get_session()
        try:
            jobs = session.query(RawJob).filter(
                RawJob.is_processed == False
            ).limit(limit).all()
            return jobs
        finally:
            session.close()
    
    def mark_job_processed(self, job_id: str):
        """Mark a job as processed."""
        session = self.get_session()
        try:
            session.query(RawJob).filter(
                RawJob.job_id == job_id
            ).update({"is_processed": True})
            session.commit()
        finally:
            session.close()
    
    def insert_extracted_skills(self, job_id: str, skills: List[Dict[str, Any]]):
        """Insert extracted skills for a job."""
        session = self.get_session()
        try:
            for skill_data in skills:
                skill = ExtractedSkill(
                    job_id=job_id,
                    **skill_data
                )
                session.add(skill)
            session.commit()
            logger.info(f"Inserted {len(skills)} extracted skills for job {job_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting extracted skills: {e}")
            raise
        finally:
            session.close()
    
    def get_extracted_skills_for_processing(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get jobs with extracted skills that need LLM processing."""
        session = self.get_session()
        try:
            # Get jobs that have extracted skills but no enhanced skills
            subquery = session.query(EnhancedSkill.job_id).distinct()
            
            jobs = session.query(RawJob).join(ExtractedSkill).filter(
                ~RawJob.job_id.in_(subquery)
            ).limit(limit).all()
            
            result = []
            for job in jobs:
                skills = session.query(ExtractedSkill).filter(
                    ExtractedSkill.job_id == job.job_id
                ).all()
                
                result.append({
                    'job_id': str(job.job_id),
                    'job_title': job.title,
                    'job_description': job.description,
                    'job_requirements': job.requirements,
                    'extracted_skills': [
                        {
                            'skill_text': skill.skill_text,
                            'extraction_method': skill.extraction_method,
                            'source_section': skill.source_section,
                            'confidence_score': skill.confidence_score
                        }
                        for skill in skills
                    ]
                })
            
            return result
        finally:
            session.close()
    
    def insert_enhanced_skills(self, job_id: str, skills: List[Dict[str, Any]]):
        """Insert enhanced skills for a job."""
        session = self.get_session()
        try:
            for skill_data in skills:
                skill = EnhancedSkill(
                    job_id=job_id,
                    **skill_data
                )
                session.add(skill)
            session.commit()
            logger.info(f"Inserted {len(skills)} enhanced skills for job {job_id}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting enhanced skills: {e}")
            raise
        finally:
            session.close()
    
    def get_unique_skills_for_embedding(self) -> List[str]:
        """Get unique normalized skills that don't have embeddings yet."""
        session = self.get_session()
        try:
            # Get skills that don't have embeddings
            embedded_skills = session.query(SkillEmbedding.skill_text).distinct()
            
            unique_skills = session.query(
                EnhancedSkill.normalized_skill
            ).filter(
                EnhancedSkill.is_duplicate == False,
                ~EnhancedSkill.normalized_skill.in_(embedded_skills)
            ).distinct().all()
            
            return [skill[0] for skill in unique_skills]
        finally:
            session.close()
    
    def insert_skill_embeddings(self, embeddings: List[Dict[str, Any]]):
        """Insert skill embeddings."""
        session = self.get_session()
        try:
            for emb_data in embeddings:
                embedding = SkillEmbedding(**emb_data)
                session.add(embedding)
            session.commit()
            logger.info(f"Inserted {len(embeddings)} skill embeddings")
        except Exception as e:
            session.rollback()
            logger.error(f"Error inserting embeddings: {e}")
            raise
        finally:
            session.close()
    
    def get_all_embeddings(self) -> List[Dict[str, Any]]:
        """Get all skill embeddings for clustering."""
        session = self.get_session()
        try:
            embeddings = session.query(SkillEmbedding).all()
            return [
                {
                    'skill_text': emb.skill_text,
                    'embedding': emb.embedding,
                    'embedding_id': str(emb.embedding_id)
                }
                for emb in embeddings
            ]
        finally:
            session.close()
    
    def save_analysis_results(self, analysis_type: str, results: Dict[str, Any], 
                            parameters: Dict[str, Any], country: Optional[str] = None):
        """Save analysis results."""
        session = self.get_session()
        try:
            analysis = AnalysisResult(
                analysis_type=analysis_type,
                country=country,
                parameters=parameters,
                results=results
            )
            session.add(analysis)
            session.commit()
            logger.info(f"Saved {analysis_type} analysis results")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving analysis results: {e}")
            raise
        finally:
            session.close()
    
    def get_skill_statistics(self, country: Optional[str] = None) -> Dict[str, Any]:
        """Get skill statistics by country."""
        session = self.get_session()
        try:
            query = session.query(
                EnhancedSkill.normalized_skill,
                func.count(func.distinct(EnhancedSkill.job_id)).label('job_count')
            ).join(RawJob).filter(
                EnhancedSkill.is_duplicate == False
            )
            
            if country:
                query = query.filter(RawJob.country == country)
            
            results = query.group_by(
                EnhancedSkill.normalized_skill
            ).order_by(
                func.count(func.distinct(EnhancedSkill.job_id)).desc()
            ).limit(50).all()
            
            return {
                'top_skills': [
                    {'skill': skill, 'count': count}
                    for skill, count in results
                ],
                'total_unique_skills': session.query(
                    func.count(func.distinct(EnhancedSkill.normalized_skill))
                ).filter(EnhancedSkill.is_duplicate == False).scalar()
            }
        finally:
            session.close() 