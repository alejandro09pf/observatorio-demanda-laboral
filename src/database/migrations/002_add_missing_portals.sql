-- Migration to add missing portals to constraints
-- This adds support for all the spiders we have implemented

-- Drop the old portal constraint
ALTER TABLE raw_jobs DROP CONSTRAINT IF EXISTS chk_portal;

-- Add the new portal constraint with all supported portals
ALTER TABLE raw_jobs ADD CONSTRAINT chk_portal CHECK (
    portal IN (
        'computrabajo', 'bumeran', 'elempleo', 'infojobs', 'zonajobs', 
        'magneto', 'occmundial', 'clarin', 'hiring_cafe', 'lego'
    )
);

-- Note: analysis_results table doesn't have a portal column, so we skip that constraint

-- Add missing columns that might be needed for the extraction pipeline
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_status VARCHAR(20) DEFAULT 'pending';
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_attempts INTEGER DEFAULT 0;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_completed_at TIMESTAMP;
ALTER TABLE raw_jobs ADD COLUMN IF NOT EXISTS extraction_error TEXT;

-- Create index for extraction status
CREATE INDEX IF NOT EXISTS idx_raw_jobs_extraction_status ON raw_jobs(extraction_status);
