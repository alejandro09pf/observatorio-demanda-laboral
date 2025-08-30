-- Migration 005: Fix broken ESCO function
-- This migration fixes the search_esco_skills function that has invalid SQL

-- Drop the broken function with correct signature
DROP FUNCTION IF EXISTS search_esco_skills(text, character varying, double precision);

-- Create the correct function
CREATE OR REPLACE FUNCTION search_esco_skills(
    search_query TEXT,
    language_code VARCHAR(5) DEFAULT 'es',
    min_confidence FLOAT DEFAULT 0.0
) RETURNS TABLE(
    skill_uri TEXT,
    preferred_label TEXT,
    skill_type VARCHAR(50),
    skill_group VARCHAR(100),
    confidence_score REAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        es.skill_uri,
        CASE 
            WHEN language_code = 'es' THEN es.preferred_label_es
            ELSE es.preferred_label_en
        END as preferred_label,
        es.skill_type,
        es.skill_group,
        GREATEST(
            -- Exact match
            CASE WHEN LOWER(es.preferred_label_es) = LOWER(search_query) THEN 1.0
                 WHEN LOWER(es.preferred_label_en) = LOWER(search_query) THEN 1.0
                 ELSE 0.0
            END,
            -- Contains match
            CASE WHEN LOWER(es.preferred_label_es) LIKE '%' || LOWER(search_query) || '%' THEN 0.8
                 WHEN LOWER(es.preferred_label_en) LIKE '%' || LOWER(search_query) || '%' THEN 0.8
                 ELSE 0.0
            END,
            -- Similarity score
            similarity(LOWER(es.preferred_label_es), LOWER(search_query))
        ) as confidence_score
    FROM esco_skills es
    WHERE es.is_active = TRUE
      AND (
          LOWER(es.preferred_label_es) LIKE '%' || LOWER(search_query) || '%'
          OR LOWER(es.preferred_label_en) LIKE '%' || LOWER(search_query) || '%'
          OR similarity(LOWER(es.preferred_label_es), LOWER(search_query)) > 0.3
      )
    ORDER BY confidence_score DESC;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT EXECUTE ON FUNCTION search_esco_skills(TEXT, VARCHAR, FLOAT) TO labor_user;
