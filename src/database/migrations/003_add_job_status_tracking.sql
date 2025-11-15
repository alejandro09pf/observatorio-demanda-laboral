-- Migration 003: Add comprehensive job status tracking
-- This script adds status tracking for each pipeline stage

-- Add status tracking columns to raw_jobs
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_completed_at TIMESTAMP;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_attempts INTEGER DEFAULT 0;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_error TEXT;

ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS enhancement_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS enhancement_completed_at TIMESTAMP;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS enhancement_attempts INTEGER DEFAULT 0;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS enhancement_error TEXT;

ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS embedding_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS embedding_completed_at TIMESTAMP;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS embedding_attempts INTEGER DEFAULT 0;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS embedding_error TEXT;

ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS analysis_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS analysis_completed_at TIMESTAMP;

-- Add constraint for valid status values
ALTER TABLE raw_jobs ADD CONSTRAINT chk_extraction_status 
    CHECK (extraction_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

ALTER TABLE raw_jobs ADD CONSTRAINT chk_enhancement_status 
    CHECK (enhancement_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

ALTER TABLE raw_jobs ADD CONSTRAINT chk_embedding_status 
    CHECK (embedding_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

ALTER TABLE raw_jobs ADD CONSTRAINT chk_analysis_status 
    CHECK (analysis_status IN ('pending', 'processing', 'completed', 'failed', 'skipped'));

-- Create indexes for status queries
CREATE INDEX IF NOT EXISTS idx_raw_jobs_extraction_status ON raw_jobs(extraction_status);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_enhancement_status ON raw_jobs(enhancement_status);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_embedding_status ON raw_jobs(embedding_status);
CREATE INDEX IF NOT EXISTS idx_raw_jobs_analysis_status ON raw_jobs(analysis_status);

-- Create a view for pipeline status overview
CREATE OR REPLACE VIEW pipeline_status_overview AS
SELECT 
    country,
    portal,
    COUNT(*) as total_jobs,
    COUNT(CASE WHEN extraction_status = 'completed' THEN 1 END) as extraction_completed,
    COUNT(CASE WHEN extraction_status = 'failed' THEN 1 END) as extraction_failed,
    COUNT(CASE WHEN enhancement_status = 'completed' THEN 1 END) as enhancement_completed,
    COUNT(CASE WHEN enhancement_status = 'failed' THEN 1 END) as enhancement_failed,
    COUNT(CASE WHEN embedding_status = 'completed' THEN 1 END) as embedding_completed,
    COUNT(CASE WHEN embedding_status = 'failed' THEN 1 END) as embedding_failed,
    COUNT(CASE WHEN analysis_status = 'completed' THEN 1 END) as analysis_completed,
    COUNT(CASE WHEN analysis_status = 'failed' THEN 1 END) as analysis_failed
FROM raw_jobs
GROUP BY country, portal
ORDER BY country, portal;

-- Create a view for jobs that need processing
CREATE OR REPLACE VIEW jobs_needing_extraction AS
SELECT job_id, portal, country, title, company, location
FROM raw_jobs
WHERE extraction_status IN ('pending', 'failed')
ORDER BY scraped_at ASC;

CREATE OR REPLACE VIEW jobs_needing_enhancement AS
SELECT rj.job_id, rj.portal, rj.country, rj.title, rj.company, rj.location
FROM raw_jobs rj
JOIN extracted_skills es ON rj.job_id = es.job_id
WHERE rj.enhancement_status IN ('pending', 'failed')
  AND rj.extraction_status = 'completed'
ORDER BY rj.scraped_at ASC;

-- Add status update functions
CREATE OR REPLACE FUNCTION update_job_extraction_status(
    p_job_id UUID,
    p_status VARCHAR(20),
    p_error TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE raw_jobs 
    SET 
        extraction_status = p_status,
        extraction_completed_at = CASE WHEN p_status = 'completed' THEN NOW() ELSE extraction_completed_at END,
        extraction_attempts = CASE WHEN p_status = 'failed' THEN extraction_attempts + 1 ELSE extraction_attempts END,
        extraction_error = p_error
    WHERE job_id = p_job_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_job_enhancement_status(
    p_job_id UUID,
    p_status VARCHAR(20),
    p_error TEXT DEFAULT NULL
) RETURNS VOID AS $$
BEGIN
    UPDATE raw_jobs 
    SET 
        enhancement_status = p_status,
        enhancement_completed_at = CASE WHEN p_status = 'completed' THEN NOW() ELSE enhancement_completed_at END,
        enhancement_attempts = CASE WHEN p_status = 'failed' THEN enhancement_attempts + 1 ELSE enhancement_attempts END,
        enhancement_error = p_error
    WHERE job_id = p_job_id;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION update_job_extraction_status(UUID, VARCHAR, TEXT) TO labor_user;
GRANT EXECUTE ON FUNCTION update_job_enhancement_status(UUID, VARCHAR, TEXT) TO labor_user;
GRANT SELECT ON pipeline_status_overview TO labor_user;
GRANT SELECT ON jobs_needing_extraction TO labor_user;
GRANT SELECT ON jobs_needing_enhancement TO labor_user;

-- Update existing jobs to have proper status
UPDATE raw_jobs SET extraction_status = 'pending' WHERE extraction_status IS NULL;
UPDATE raw_jobs SET enhancement_status = 'pending' WHERE enhancement_status IS NULL;
UPDATE raw_jobs SET embedding_status = 'pending' WHERE embedding_status IS NULL;
UPDATE raw_jobs SET analysis_status = 'pending' WHERE analysis_status IS NULL;
