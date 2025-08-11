-- Create database
CREATE DATABASE IF NOT EXISTS labor_observatory
  WITH ENCODING 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8';

\c labor_observatory;

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";

-- Create tables
CREATE TABLE IF NOT EXISTS raw_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portal VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT NOT NULL,
    requirements TEXT,
    salary_raw TEXT,
    contract_type VARCHAR(50),
    remote_type VARCHAR(50),
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash VARCHAR(64) UNIQUE,
    raw_html TEXT,
    is_processed BOOLEAN DEFAULT FALSE,
    
    CONSTRAINT chk_country CHECK (country IN ('CO', 'MX', 'AR')),
    CONSTRAINT chk_portal CHECK (portal IN ('computrabajo', 'bumeran', 'elempleo'))
);

CREATE INDEX idx_portal_country ON raw_jobs(portal, country);
CREATE INDEX idx_scraped_at ON raw_jobs(scraped_at);
CREATE INDEX idx_processed ON raw_jobs(is_processed);

CREATE TABLE IF NOT EXISTS extracted_skills (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(50),
    extraction_method VARCHAR(50),
    confidence_score FLOAT,
    source_section VARCHAR(50),
    span_start INTEGER,
    span_end INTEGER,
    esco_uri TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_job_skills ON extracted_skills(job_id);
CREATE INDEX idx_skill_text ON extracted_skills(skill_text);

CREATE TABLE IF NOT EXISTS enhanced_skills (
    enhancement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    original_skill_text TEXT,
    normalized_skill TEXT NOT NULL,
    skill_type VARCHAR(50),
    esco_concept_uri TEXT,
    esco_preferred_label TEXT,
    llm_confidence FLOAT,
    llm_reasoning TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID,
    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model VARCHAR(100)
);

CREATE INDEX idx_job_enhanced ON enhanced_skills(job_id);
CREATE INDEX idx_normalized ON enhanced_skills(normalized_skill);

CREATE TABLE IF NOT EXISTS skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT UNIQUE NOT NULL,
    embedding vector(768) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_skill_lookup ON skill_embeddings(skill_text);
CREATE INDEX idx_embedding_similarity ON skill_embeddings 
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);

CREATE TABLE IF NOT EXISTS analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type VARCHAR(50),
    country CHAR(2),
    date_range_start DATE,
    date_range_end DATE,
    parameters JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_analysis_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_date ON analysis_results(created_at);

-- Create views
CREATE VIEW skill_frequency AS
SELECT 
    es.normalized_skill,
    COUNT(DISTINCT es.job_id) as job_count,
    COUNT(*) as total_mentions,
    ARRAY_AGG(DISTINCT rj.country) as countries
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
WHERE es.is_duplicate = FALSE
GROUP BY es.normalized_skill
ORDER BY job_count DESC;

CREATE VIEW country_skill_distribution AS
SELECT 
    rj.country,
    es.normalized_skill,
    COUNT(DISTINCT es.job_id) as job_count
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
WHERE es.is_duplicate = FALSE
GROUP BY rj.country, es.normalized_skill
ORDER BY rj.country, job_count DESC; 