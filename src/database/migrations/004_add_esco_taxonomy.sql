-- Migration 004: Add ESCO Taxonomy Database Structure
-- This script creates tables for local ESCO skill mapping

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ESCO Skills table
CREATE TABLE IF NOT EXISTS esco_skills (
    skill_uri TEXT PRIMARY KEY,
    skill_id VARCHAR(50),
    preferred_label_es TEXT,
    preferred_label_en TEXT,
    description_es TEXT,
    description_en TEXT,
    skill_type VARCHAR(50),
    skill_group VARCHAR(100),
    skill_family VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ESCO Skill Labels (multilingual)
CREATE TABLE IF NOT EXISTS esco_skill_labels (
    label_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    language_code VARCHAR(5) NOT NULL,
    label TEXT NOT NULL,
    label_type VARCHAR(20) DEFAULT 'alternative', -- preferred, alternative, hidden
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(skill_uri, language_code, label)
);

-- ESCO Skill Relations
CREATE TABLE IF NOT EXISTS esco_skill_relations (
    relation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    target_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL, -- broader, narrower, related, essential, optional
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_skill_uri, target_skill_uri, relation_type)
);

-- Custom Skill Mappings (for skills not in ESCO)
CREATE TABLE IF NOT EXISTS custom_skill_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT NOT NULL,
    esco_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.0,
    mapping_reason TEXT,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ESCO Skill Groups
CREATE TABLE IF NOT EXISTS esco_skill_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name_es TEXT,
    group_name_en TEXT,
    description_es TEXT,
    description_en TEXT,
    parent_group_id VARCHAR(50) REFERENCES esco_skill_groups(group_id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ESCO Skill Families
CREATE TABLE IF NOT EXISTS esco_skill_families (
    family_id VARCHAR(50) PRIMARY KEY,
    family_name_es TEXT,
    family_name_en TEXT,
    description_es TEXT,
    description_en TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for fast searching
CREATE INDEX IF NOT EXISTS idx_esco_skills_label_es ON esco_skills USING gin(to_tsvector('spanish', preferred_label_es));
CREATE INDEX IF NOT EXISTS idx_esco_skills_label_en ON esco_skills USING gin(to_tsvector('english', preferred_label_en));
CREATE INDEX IF NOT EXISTS idx_esco_skills_group ON esco_skills(skill_group);
CREATE INDEX IF NOT EXISTS idx_esco_skills_family ON esco_skills(skill_family);
CREATE INDEX IF NOT EXISTS idx_esco_skills_type ON esco_skills(skill_type);

CREATE INDEX IF NOT EXISTS idx_esco_labels_skill_uri ON esco_skill_labels(skill_uri);
CREATE INDEX IF NOT EXISTS idx_esco_labels_language ON esco_skill_labels(language_code);
CREATE INDEX IF NOT EXISTS idx_esco_labels_text ON esco_skill_labels USING gin(to_tsvector('spanish', label));

CREATE INDEX IF NOT EXISTS idx_esco_relations_source ON esco_skill_relations(source_skill_uri);
CREATE INDEX IF NOT EXISTS idx_esco_relations_target ON esco_skill_relations(target_skill_uri);
CREATE INDEX IF NOT EXISTS idx_esco_relations_type ON esco_skill_relations(relation_type);

CREATE INDEX IF NOT EXISTS idx_custom_mappings_skill_text ON custom_skill_mappings USING gin(to_tsvector('spanish', skill_text));
CREATE INDEX IF NOT EXISTS idx_custom_mappings_esco_uri ON custom_skill_mappings(esco_skill_uri);

-- Create views for easy querying
CREATE OR REPLACE VIEW esco_skills_search AS
SELECT 
    es.skill_uri,
    es.skill_id,
    es.preferred_label_es,
    es.preferred_label_en,
    es.description_es,
    es.description_en,
    es.skill_type,
    es.skill_group,
    es.skill_family,
    es.is_active,
    -- Combine all labels for search
    string_agg(DISTINCT esl.label, ' ' ORDER BY esl.label) as all_labels_es,
    -- Count alternative labels
    COUNT(DISTINCT esl.label) as label_count
FROM esco_skills es
LEFT JOIN esco_skill_labels esl ON es.skill_uri = esl.skill_uri AND esl.language_code = 'es'
WHERE es.is_active = TRUE
GROUP BY es.skill_uri, es.skill_id, es.preferred_label_es, es.preferred_label_en, 
         es.description_es, es.description_en, es.skill_type, es.skill_group, es.skill_family, es.is_active;

-- View for skill relations
CREATE OR REPLACE VIEW esco_skill_relations_view AS
SELECT 
    esr.relation_id,
    esr.source_skill_uri,
    source.preferred_label_es as source_skill_name,
    esr.target_skill_uri,
    target.preferred_label_es as target_skill_name,
    esr.relation_type
FROM esco_skill_relations esr
JOIN esco_skills source ON esr.source_skill_uri = source.skill_uri
JOIN esco_skills target ON esr.target_skill_uri = target.skill_uri;

-- Function to search skills by text
CREATE OR REPLACE FUNCTION search_esco_skills(
    search_text TEXT,
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
            CASE WHEN LOWER(es.preferred_label_es) = LOWER(search_text) THEN 1.0
                 WHEN LOWER(es.preferred_label_en) = LOWER(search_text) THEN 1.0
                 ELSE 0.0
            END,
            -- Contains match
            CASE WHEN LOWER(es.preferred_label_es) LIKE '%' || LOWER(search_text) || '%' THEN 0.8
                 WHEN LOWER(es.preferred_label_en) LIKE '%' || LOWER(search_text) || '%' THEN 0.8
                 ELSE 0.0
            END,
            -- Similarity score
            similarity(LOWER(es.preferred_label_es), LOWER(search_text))
        ) as confidence_score
    FROM esco_skills es
    WHERE es.is_active = TRUE
      AND (
          LOWER(es.preferred_label_es) LIKE '%' || LOWER(search_text) || '%'
          OR LOWER(es.preferred_label_en) LIKE '%' || LOWER(search_text) || '%'
          OR similarity(LOWER(es.preferred_label_es), LOWER(search_text)) > 0.3
      )
    ORDER BY confidence_score DESC;
END;
$$ LANGUAGE plpgsql;

-- Function to get related skills
CREATE OR REPLACE FUNCTION get_related_esco_skills(
    skill_uri TEXT,
    relation_type VARCHAR(50) DEFAULT 'related'
) RETURNS TABLE(
    related_skill_uri TEXT,
    related_skill_name TEXT,
    relation_type VARCHAR(50)
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        esr.target_skill_uri,
        es.preferred_label_es,
        esr.relation_type
    FROM esco_skill_relations esr
    JOIN esco_skills es ON esr.target_skill_uri = es.skill_uri
    WHERE esr.source_skill_uri = skill_uri
      AND (relation_type = 'all' OR esr.relation_type = relation_type)
      AND es.is_active = TRUE
    ORDER BY es.preferred_label_es;
END;
$$ LANGUAGE plpgsql;

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO labor_user;
GRANT EXECUTE ON FUNCTION search_esco_skills(TEXT, VARCHAR, FLOAT) TO labor_user;
GRANT EXECUTE ON FUNCTION get_related_esco_skills(TEXT, VARCHAR) TO labor_user;
