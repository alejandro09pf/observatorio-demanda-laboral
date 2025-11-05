-- Migration 008: Add Gold Standard Annotations Table
-- Purpose: Store manually annotated skills for evaluation of extraction pipelines
-- Date: 2025-11-04

-- Create gold_standard_annotations table
CREATE TABLE IF NOT EXISTS gold_standard_annotations (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL,
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(10) NOT NULL,

    -- Metadata specific to manual annotation
    annotator VARCHAR(50) DEFAULT 'manual',
    annotation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    -- Constraints
    CONSTRAINT fk_gold_standard_job
        FOREIGN KEY (job_id)
        REFERENCES raw_jobs(job_id)
        ON DELETE CASCADE,

    CONSTRAINT unique_job_skill_type
        UNIQUE(job_id, skill_text, skill_type),

    CONSTRAINT valid_skill_type
        CHECK (skill_type IN ('hard', 'soft'))
);

-- Create indexes for performance
CREATE INDEX idx_gold_standard_job_id
    ON gold_standard_annotations(job_id);

CREATE INDEX idx_gold_standard_skill_type
    ON gold_standard_annotations(skill_type);

CREATE INDEX idx_gold_standard_skill_text
    ON gold_standard_annotations USING gin(to_tsvector('spanish', skill_text));

CREATE INDEX idx_gold_standard_annotation_date
    ON gold_standard_annotations(annotation_date);

-- Add comment to table
COMMENT ON TABLE gold_standard_annotations IS
    'Manually annotated skills from gold standard dataset (300 jobs) for pipeline evaluation';

COMMENT ON COLUMN gold_standard_annotations.job_id IS
    'Foreign key to raw_jobs - only jobs with is_gold_standard=true should be here';

COMMENT ON COLUMN gold_standard_annotations.skill_type IS
    'Type of skill: hard (technical) or soft (interpersonal)';

COMMENT ON COLUMN gold_standard_annotations.annotator IS
    'Who performed the annotation (e.g., manual, claude, human_reviewer)';

COMMENT ON COLUMN gold_standard_annotations.notes IS
    'Additional notes or comments about the job ad from manual annotation';
