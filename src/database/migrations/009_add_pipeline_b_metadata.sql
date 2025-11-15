-- Migration 009: Add Pipeline B metadata fields to enhanced_skills
-- Date: 2025-01-05
-- Purpose: Track LLM processing metrics (time, tokens, ESCO method) for thesis analysis

-- Add metadata columns
ALTER TABLE enhanced_skills
ADD COLUMN IF NOT EXISTS processing_time_seconds FLOAT,
ADD COLUMN IF NOT EXISTS tokens_used INTEGER,
ADD COLUMN IF NOT EXISTS esco_match_method VARCHAR(20),
ADD COLUMN IF NOT EXISTS llm_model VARCHAR(100);

-- Add comments for documentation
COMMENT ON COLUMN enhanced_skills.processing_time_seconds IS 'Time taken by LLM to process entire job (seconds). Same value for all skills from same job.';
COMMENT ON COLUMN enhanced_skills.tokens_used IS 'Total LLM tokens consumed for job extraction. Same value for all skills from same job.';
COMMENT ON COLUMN enhanced_skills.esco_match_method IS 'How skill was matched to ESCO: exact, fuzzy, semantic, or emergent (not matched)';
COMMENT ON COLUMN enhanced_skills.llm_model IS 'LLM model used for extraction (e.g., gemma-3-4b-instruct)';

-- Create indexes for analytics queries
CREATE INDEX IF NOT EXISTS idx_enhanced_skills_processing_time ON enhanced_skills(processing_time_seconds);
CREATE INDEX IF NOT EXISTS idx_enhanced_skills_tokens ON enhanced_skills(tokens_used);
CREATE INDEX IF NOT EXISTS idx_enhanced_skills_esco_method ON enhanced_skills(esco_match_method);
CREATE INDEX IF NOT EXISTS idx_enhanced_skills_llm_model ON enhanced_skills(llm_model);

-- Verify columns exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'enhanced_skills'
        AND column_name = 'processing_time_seconds'
    ) THEN
        RAISE EXCEPTION 'Migration 009 failed: processing_time_seconds column not created';
    END IF;

    RAISE NOTICE 'Migration 009 completed successfully';
END $$;
