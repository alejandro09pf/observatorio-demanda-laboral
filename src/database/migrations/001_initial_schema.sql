-- Initial database schema for Labor Market Observatory
-- This script creates all necessary tables and indexes

-- Create database (PostgreSQL 15 doesn't support IF NOT EXISTS for CREATE DATABASE)
-- The database is already created by docker-compose environment variables

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Note: pgvector extension will be added later when we upgrade to a compatible image
-- CREATE EXTENSION IF NOT EXISTS "pgvector";

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

CREATE TABLE IF NOT EXISTS extracted_skills (
    skill_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    skill_name TEXT NOT NULL,
    skill_type VARCHAR(50) NOT NULL, -- 'explicit', 'implicit', 'ner'
    confidence_score FLOAT DEFAULT 1.0,
    extraction_method VARCHAR(50) NOT NULL, -- 'regex', 'ner', 'esco'
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_skill_type CHECK (skill_type IN ('explicit', 'implicit', 'ner')),
    CONSTRAINT chk_extraction_method CHECK (extraction_method IN ('regex', 'ner', 'esco'))
);

CREATE TABLE IF NOT EXISTS enhanced_skills (
    enhanced_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    original_skill_id UUID REFERENCES extracted_skills(skill_id),
    skill_name TEXT NOT NULL,
    normalized_name TEXT,
    esco_code VARCHAR(20),
    esco_level INTEGER,
    confidence_score FLOAT DEFAULT 1.0,
    enhancement_method VARCHAR(50) NOT NULL, -- 'llm', 'esco', 'manual'
    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_enhancement_method CHECK (enhancement_method IN ('llm', 'esco', 'manual'))
);

CREATE TABLE IF NOT EXISTS skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_name TEXT NOT NULL,
    embedding_vector REAL[], -- Will be replaced with pgvector when available
    model_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analysis_results (
    result_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type VARCHAR(50) NOT NULL, -- 'clustering', 'trends', 'demand'
    country CHAR(2),
    portal VARCHAR(50),
    result_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT chk_analysis_country CHECK (country IN ('CO', 'MX', 'AR')),
    CONSTRAINT chk_analysis_portal CHECK (portal IN ('computrabajo', 'bumeran', 'elempleo'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_raw_jobs_country ON raw_jobs(country);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_portal ON raw_jobs(portal);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_scraped_at ON raw_jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_content_hash ON raw_jobs(content_hash);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_is_processed ON raw_jobs(is_processed);

CREATE INDEX IF NOT EXISTS idx_extracted_skills_job_id ON extracted_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_extracted_skills_skill_type ON extracted_skills(skill_type);
CREATE INDEX IF NOT EXISTS idx_extracted_skills_extraction_method ON extracted_skills(extraction_method);

CREATE INDEX IF NOT EXISTS idx_enhanced_skills_job_id ON enhanced_skills(job_id);
CREATE INDEX IF NOT EXISTS idx_enhanced_skills_esco_code ON enhanced_skills(esco_code);

CREATE INDEX IF NOT EXISTS idx_skill_embeddings_skill_name ON skill_embeddings(skill_name);
CREATE INDEX IF NOT EXISTS idx_skill_embeddings_model_name ON skill_embeddings(model_name);

CREATE INDEX IF NOT EXISTS idx_analysis_results_type_country ON analysis_results(analysis_type, country);
CREATE INDEX IF NOT EXISTS idx_analysis_results_created_at ON analysis_results(created_at);

-- Create views for common queries
CREATE OR REPLACE VIEW skill_frequency AS
SELECT 
    es.skill_name,
    COUNT(*) as frequency,
    COUNT(DISTINCT es.job_id) as job_count,
    COUNT(DISTINCT rj.country) as country_count
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
GROUP BY es.skill_name
ORDER BY frequency DESC;

CREATE OR REPLACE VIEW country_skill_distribution AS
SELECT 
    rj.country,
    es.skill_name,
    COUNT(*) as frequency
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
GROUP BY rj.country, es.skill_name
ORDER BY rj.country, frequency DESC;

-- Insert sample data for testing
INSERT INTO raw_jobs (portal, country, url, title, company, location, description, requirements, content_hash)
VALUES 
    ('computrabajo', 'CO', 'https://example.com/job1', 'Desarrollador Python', 'TechCorp', 'Bogotá', 'Desarrollo de aplicaciones web con Python', 'Python, Django, PostgreSQL', 'hash1'),
    ('computrabajo', 'CO', 'https://example.com/job2', 'Ingeniero de Datos', 'DataCorp', 'Medellín', 'Análisis y procesamiento de datos', 'Python, SQL, Pandas', 'hash2')
ON CONFLICT (content_hash) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO labor_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO labor_user;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO labor_user; 