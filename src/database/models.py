from sqlalchemy import Column, String, Text, Boolean, Float, Integer, DateTime, Date, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid

Base = declarative_base()

class RawJob(Base):
    __tablename__ = 'raw_jobs'
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    portal = Column(String(50), nullable=False)
    country = Column(String(2), nullable=False)
    url = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    company = Column(Text)
    location = Column(Text)
    description = Column(Text, nullable=False)
    requirements = Column(Text)
    salary_raw = Column(Text)
    contract_type = Column(String(50))
    remote_type = Column(String(50))
    posted_date = Column(Date)
    scraped_at = Column(DateTime, server_default=func.now())
    content_hash = Column(String(64), unique=True)
    raw_html = Column(Text)
    is_processed = Column(Boolean, default=False)
    
    # Relationships
    extracted_skills = relationship("ExtractedSkill", back_populates="job")
    enhanced_skills = relationship("EnhancedSkill", back_populates="job")

class ExtractedSkill(Base):
    __tablename__ = 'extracted_skills'
    
    extraction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('raw_jobs.job_id'))
    skill_text = Column(Text, nullable=False)
    skill_type = Column(String(50))
    extraction_method = Column(String(50))
    confidence_score = Column(Float)
    source_section = Column(String(50))
    span_start = Column(Integer)
    span_end = Column(Integer)
    esco_uri = Column(Text)
    extracted_at = Column(DateTime, server_default=func.now())
    
    # Relationships
    job = relationship("RawJob", back_populates="extracted_skills")

class EnhancedSkill(Base):
    __tablename__ = 'enhanced_skills'
    
    enhancement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('raw_jobs.job_id'))
    original_skill_text = Column(Text)
    normalized_skill = Column(Text, nullable=False)
    skill_type = Column(String(50))
    esco_concept_uri = Column(Text)
    esco_preferred_label = Column(Text)
    llm_confidence = Column(Float)
    llm_reasoning = Column(Text)
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(UUID(as_uuid=True))
    enhanced_at = Column(DateTime, server_default=func.now())
    llm_model = Column(String(100))
    
    # Relationships
    job = relationship("RawJob", back_populates="enhanced_skills")

class SkillEmbedding(Base):
    __tablename__ = 'skill_embeddings'
    
    embedding_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    skill_text = Column(Text, unique=True, nullable=False)
    embedding = Column(Vector(768), nullable=False)
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50))
    created_at = Column(DateTime, server_default=func.now())

class AnalysisResult(Base):
    __tablename__ = 'analysis_results'
    
    analysis_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    analysis_type = Column(String(50))
    country = Column(String(2))
    date_range_start = Column(Date)
    date_range_end = Column(Date)
    parameters = Column(JSONB)
    results = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now()) 