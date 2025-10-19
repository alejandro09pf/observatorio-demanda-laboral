-- Migration 006: Add cleaned_jobs table and junk filtering
-- Purpose: Store cleaned/normalized job text separately from raw HTML
-- Author: ETL Pipeline Design
-- Date: 2025-10-19

-- ============================================================================
-- 1. Add junk filtering columns to raw_jobs
-- ============================================================================

ALTER TABLE raw_jobs
ADD COLUMN IF NOT EXISTS is_usable BOOLEAN DEFAULT TRUE,
ADD COLUMN IF NOT EXISTS unusable_reason TEXT;

-- Create index for filtering usable jobs
CREATE INDEX IF NOT EXISTS idx_raw_jobs_usable
ON raw_jobs(is_usable)
WHERE is_usable = TRUE;

COMMENT ON COLUMN raw_jobs.is_usable IS 'FALSE if job is junk/test data and should not be processed';
COMMENT ON COLUMN raw_jobs.unusable_reason IS 'Reason why job was marked as unusable (e.g., "Empty description", "Test job")';

-- ============================================================================
-- 2. Create cleaned_jobs table
-- ============================================================================

CREATE TABLE IF NOT EXISTS cleaned_jobs (
    job_id UUID PRIMARY KEY REFERENCES raw_jobs(job_id) ON DELETE CASCADE,

    -- Cleaned individual fields
    title_cleaned TEXT,
    description_cleaned TEXT,
    requirements_cleaned TEXT,

    -- Combined text for extraction (title + description + requirements)
    combined_text TEXT NOT NULL,

    -- Cleaning metadata
    cleaning_method VARCHAR(50) DEFAULT 'html_strip',
    cleaned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Text statistics (for quality monitoring)
    combined_word_count INTEGER,
    combined_char_count INTEGER,

    CONSTRAINT fk_cleaned_jobs_raw_jobs FOREIGN KEY (job_id)
        REFERENCES raw_jobs(job_id) ON DELETE CASCADE
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_cleaned_jobs_cleaned_at ON cleaned_jobs(cleaned_at);
CREATE INDEX IF NOT EXISTS idx_cleaned_jobs_word_count ON cleaned_jobs(combined_word_count);

-- Full-text search index on combined_text
CREATE INDEX IF NOT EXISTS idx_cleaned_jobs_combined_text_fts
ON cleaned_jobs USING gin(to_tsvector('spanish', combined_text));

COMMENT ON TABLE cleaned_jobs IS 'Cleaned and normalized job postings ready for skill extraction';
COMMENT ON COLUMN cleaned_jobs.combined_text IS 'Concatenated cleaned text: title + description + requirements';
COMMENT ON COLUMN cleaned_jobs.cleaning_method IS 'Method used for cleaning (e.g., html_strip, normalize_unicode)';

-- ============================================================================
-- 3. Create view for extraction-ready jobs
-- ============================================================================

CREATE OR REPLACE VIEW extraction_ready_jobs AS
SELECT
    r.job_id,
    r.portal,
    r.country,
    r.url,
    r.company,
    r.location,
    r.posted_date,
    r.scraped_at,
    r.extraction_status,
    c.title_cleaned,
    c.description_cleaned,
    c.requirements_cleaned,
    c.combined_text,
    c.combined_word_count,
    c.cleaned_at
FROM raw_jobs r
INNER JOIN cleaned_jobs c ON r.job_id = c.job_id
WHERE r.is_usable = TRUE
  AND r.extraction_status = 'pending';

COMMENT ON VIEW extraction_ready_jobs IS 'Jobs ready for skill extraction (usable + cleaned + pending)';

-- ============================================================================
-- 4. Create statistics function
-- ============================================================================

CREATE OR REPLACE FUNCTION get_cleaning_stats()
RETURNS TABLE (
    metric VARCHAR(50),
    value BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 'total_raw_jobs'::VARCHAR(50), COUNT(*)::BIGINT FROM raw_jobs
    UNION ALL
    SELECT 'usable_jobs'::VARCHAR(50), COUNT(*)::BIGINT FROM raw_jobs WHERE is_usable = TRUE
    UNION ALL
    SELECT 'unusable_jobs'::VARCHAR(50), COUNT(*)::BIGINT FROM raw_jobs WHERE is_usable = FALSE
    UNION ALL
    SELECT 'cleaned_jobs'::VARCHAR(50), COUNT(*)::BIGINT FROM cleaned_jobs
    UNION ALL
    SELECT 'extraction_ready'::VARCHAR(50), COUNT(*)::BIGINT FROM extraction_ready_jobs
    UNION ALL
    SELECT 'avg_combined_words'::VARCHAR(50), AVG(combined_word_count)::BIGINT FROM cleaned_jobs;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_cleaning_stats() IS 'Get ETL cleaning pipeline statistics';

-- ============================================================================
-- Migration complete
-- ============================================================================

-- Verify migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 006 completed successfully';
    RAISE NOTICE 'Tables created: cleaned_jobs';
    RAISE NOTICE 'Columns added to raw_jobs: is_usable, unusable_reason';
    RAISE NOTICE 'View created: extraction_ready_jobs';
    RAISE NOTICE 'Function created: get_cleaning_stats()';

    -- Show current stats
    RAISE NOTICE '';
    RAISE NOTICE 'Current statistics:';
    PERFORM * FROM get_cleaning_stats();
END $$;
