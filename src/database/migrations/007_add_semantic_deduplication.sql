-- Migration 007: Add semantic deduplication columns
-- This migration adds columns to track near-duplicate job postings
-- that are semantically similar but have different content_hash

-- Add columns to raw_jobs table
ALTER TABLE raw_jobs
ADD COLUMN is_duplicate BOOLEAN DEFAULT FALSE,
ADD COLUMN duplicate_of UUID REFERENCES raw_jobs(job_id) ON DELETE SET NULL,
ADD COLUMN duplicate_similarity_score FLOAT,
ADD COLUMN duplicate_detection_method VARCHAR(50);

-- Create index for efficient duplicate queries
CREATE INDEX idx_raw_jobs_is_duplicate ON raw_jobs(is_duplicate);
CREATE INDEX idx_raw_jobs_duplicate_of ON raw_jobs(duplicate_of);

-- Add comment to document purpose
COMMENT ON COLUMN raw_jobs.is_duplicate IS 'TRUE if this job is a semantic duplicate of another job';
COMMENT ON COLUMN raw_jobs.duplicate_of IS 'References the job_id of the original (best quality) job in the duplicate group';
COMMENT ON COLUMN raw_jobs.duplicate_similarity_score IS 'Similarity score (0-1) that triggered duplicate detection';
COMMENT ON COLUMN raw_jobs.duplicate_detection_method IS 'Method used: exact_match, fuzzy_title, semantic_embedding';
