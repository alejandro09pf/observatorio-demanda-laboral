-- Migration: Add ESCO mapping columns to gold_standard_annotations
-- Date: 2025-11-07
-- Purpose: Enable ESCO mapping for manually annotated skills to compare coverage

-- Add ESCO mapping columns (same as enhanced_skills)
ALTER TABLE gold_standard_annotations
ADD COLUMN IF NOT EXISTS esco_concept_uri TEXT,
ADD COLUMN IF NOT EXISTS esco_preferred_label TEXT,
ADD COLUMN IF NOT EXISTS esco_match_method VARCHAR(20),
ADD COLUMN IF NOT EXISTS esco_match_score DOUBLE PRECISION;

-- Create indexes for ESCO queries
CREATE INDEX IF NOT EXISTS idx_gold_standard_esco_uri
ON gold_standard_annotations(esco_concept_uri);

CREATE INDEX IF NOT EXISTS idx_gold_standard_esco_method
ON gold_standard_annotations(esco_match_method);

-- Add comment
COMMENT ON COLUMN gold_standard_annotations.esco_concept_uri IS 'ESCO skill URI if matched';
COMMENT ON COLUMN gold_standard_annotations.esco_preferred_label IS 'ESCO preferred label if matched';
COMMENT ON COLUMN gold_standard_annotations.esco_match_method IS 'Method used for ESCO matching (exact, fuzzy, embedding)';
COMMENT ON COLUMN gold_standard_annotations.esco_match_score IS 'Confidence score of ESCO match (0-1)';
