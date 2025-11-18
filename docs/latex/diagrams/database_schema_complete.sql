-- ============================================================================
-- COMPLETE DATABASE SCHEMA - Observatorio de Demanda Laboral
-- Version: 2.0 (Actualizado con todas las migraciones hasta 009)
-- Date: 2025-11-17
-- Purpose: Schema completo para importación en Lucidchart
-- ============================================================================

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================================================
-- TABLA 1: raw_jobs (Tabla central - ofertas laborales scrapeadas)
-- ============================================================================
CREATE TABLE raw_jobs (
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

    -- Migration 006: Junk filtering
    is_usable BOOLEAN DEFAULT TRUE,
    unusable_reason TEXT,

    -- Migration 007: Semantic deduplication
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of UUID REFERENCES raw_jobs(job_id) ON DELETE SET NULL,
    duplicate_similarity_score FLOAT,
    duplicate_detection_method VARCHAR(50),

    CONSTRAINT chk_country CHECK (country IN ('CO', 'MX', 'AR'))
);

-- ============================================================================
-- TABLA 2: cleaned_jobs (Migration 006 - Texto limpio para extracción)
-- ============================================================================
CREATE TABLE cleaned_jobs (
    job_id UUID PRIMARY KEY REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    title_cleaned TEXT,
    description_cleaned TEXT,
    requirements_cleaned TEXT,
    combined_text TEXT NOT NULL,
    cleaning_method VARCHAR(50) DEFAULT 'html_strip',
    cleaned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    combined_word_count INTEGER,
    combined_char_count INTEGER
);

-- ============================================================================
-- TABLA 3: esco_skills (Taxonomía ESCO - tabla de referencia)
-- ============================================================================
CREATE TABLE esco_skills (
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

-- ============================================================================
-- TABLA 4: esco_skill_labels (Migration 004 - Etiquetas multilingües)
-- ============================================================================
CREATE TABLE esco_skill_labels (
    label_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    language_code VARCHAR(5) NOT NULL,
    label TEXT NOT NULL,
    label_type VARCHAR(20) DEFAULT 'alternative',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(skill_uri, language_code, label)
);

-- ============================================================================
-- TABLA 5: esco_skill_relations (Migration 004 - Relaciones entre skills)
-- ============================================================================
CREATE TABLE esco_skill_relations (
    relation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    target_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE CASCADE,
    relation_type VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(source_skill_uri, target_skill_uri, relation_type)
);

-- ============================================================================
-- TABLA 6: custom_skill_mappings (Migration 004 - Mapeos manuales)
-- ============================================================================
CREATE TABLE custom_skill_mappings (
    mapping_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT NOT NULL,
    esco_skill_uri TEXT REFERENCES esco_skills(skill_uri) ON DELETE SET NULL,
    confidence_score FLOAT DEFAULT 0.0,
    mapping_reason TEXT,
    created_by VARCHAR(100) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLA 7: esco_skill_groups (Migration 004 - Grupos jerárquicos)
-- ============================================================================
CREATE TABLE esco_skill_groups (
    group_id VARCHAR(50) PRIMARY KEY,
    group_name_es TEXT,
    group_name_en TEXT,
    description_es TEXT,
    description_en TEXT,
    parent_group_id VARCHAR(50) REFERENCES esco_skill_groups(group_id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLA 8: esco_skill_families (Migration 004 - Familias de skills)
-- ============================================================================
CREATE TABLE esco_skill_families (
    family_id VARCHAR(50) PRIMARY KEY,
    family_name_es TEXT,
    family_name_en TEXT,
    description_es TEXT,
    description_en TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================================
-- TABLA 9: extracted_skills (Pipeline A - NER + Regex)
-- ============================================================================
CREATE TABLE extracted_skills (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(50),
    extraction_method VARCHAR(50),
    confidence_score FLOAT,
    source_section VARCHAR(50),
    span_start INTEGER,
    span_end INTEGER,
    esco_uri TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA 10: enhanced_skills (Pipeline B - LLM)
-- ============================================================================
CREATE TABLE enhanced_skills (
    enhancement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID NOT NULL REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    original_skill_text TEXT,
    normalized_skill TEXT NOT NULL,
    skill_type VARCHAR(50),
    esco_concept_uri TEXT,
    esco_preferred_label TEXT,
    llm_confidence FLOAT,
    llm_reasoning TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID,
    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model VARCHAR(100),

    -- Migration 009: Pipeline B metadata
    processing_time_seconds FLOAT,
    tokens_used INTEGER,
    esco_match_method VARCHAR(20)
);

-- ============================================================================
-- TABLA 11: skill_embeddings (Vectores E5 768D)
-- ============================================================================
CREATE TABLE skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT UNIQUE NOT NULL,
    embedding VECTOR(768) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA 12: analysis_results (Clustering, UMAP, tendencias)
-- ============================================================================
CREATE TABLE analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type VARCHAR(50),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    country CHAR(2),
    date_range_start DATE,
    date_range_end DATE,
    parameters JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- TABLA 13: gold_standard_annotations (Migration 008 - Evaluación manual)
-- ============================================================================
CREATE TABLE gold_standard_annotations (
    id SERIAL PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES raw_jobs(job_id) ON DELETE CASCADE,
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(10) NOT NULL,
    annotator VARCHAR(50) DEFAULT 'manual',
    annotation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notes TEXT,

    CONSTRAINT unique_job_skill_type UNIQUE(job_id, skill_text, skill_type),
    CONSTRAINT valid_skill_type CHECK (skill_type IN ('hard', 'soft'))
);

-- ============================================================================
-- INDICES PRINCIPALES
-- ============================================================================

-- raw_jobs indexes
CREATE INDEX idx_raw_jobs_country ON raw_jobs(country);
CREATE INDEX idx_raw_jobs_portal ON raw_jobs(portal);
CREATE INDEX idx_raw_jobs_posted_date ON raw_jobs(posted_date);
CREATE INDEX idx_raw_jobs_is_processed ON raw_jobs(is_processed);
CREATE INDEX idx_raw_jobs_is_usable ON raw_jobs(is_usable) WHERE is_usable = TRUE;
CREATE INDEX idx_raw_jobs_is_duplicate ON raw_jobs(is_duplicate);
CREATE INDEX idx_raw_jobs_duplicate_of ON raw_jobs(duplicate_of);

-- cleaned_jobs indexes
CREATE INDEX idx_cleaned_jobs_cleaned_at ON cleaned_jobs(cleaned_at);
CREATE INDEX idx_cleaned_jobs_word_count ON cleaned_jobs(combined_word_count);
CREATE INDEX idx_cleaned_jobs_combined_text_fts ON cleaned_jobs USING gin(to_tsvector('spanish', combined_text));

-- extracted_skills indexes
CREATE INDEX idx_extracted_skills_job_id ON extracted_skills(job_id);
CREATE INDEX idx_extracted_skills_skill_type ON extracted_skills(skill_type);
CREATE INDEX idx_extracted_skills_extraction_method ON extracted_skills(extraction_method);

-- enhanced_skills indexes
CREATE INDEX idx_enhanced_skills_job_id ON enhanced_skills(job_id);
CREATE INDEX idx_enhanced_skills_skill_type ON enhanced_skills(skill_type);
CREATE INDEX idx_enhanced_skills_processing_time ON enhanced_skills(processing_time_seconds);
CREATE INDEX idx_enhanced_skills_tokens ON enhanced_skills(tokens_used);
CREATE INDEX idx_enhanced_skills_esco_method ON enhanced_skills(esco_match_method);
CREATE INDEX idx_enhanced_skills_llm_model ON enhanced_skills(llm_model);

-- skill_embeddings indexes
CREATE INDEX idx_skill_embeddings_skill_text ON skill_embeddings(skill_text);
CREATE INDEX idx_skill_embeddings_model_name ON skill_embeddings(model_name);

-- analysis_results indexes
CREATE INDEX idx_analysis_results_type ON analysis_results(analysis_type);
CREATE INDEX idx_analysis_results_country ON analysis_results(country);
CREATE INDEX idx_analysis_results_created_at ON analysis_results(created_at);

-- gold_standard_annotations indexes
CREATE INDEX idx_gold_standard_job_id ON gold_standard_annotations(job_id);
CREATE INDEX idx_gold_standard_skill_type ON gold_standard_annotations(skill_type);
CREATE INDEX idx_gold_standard_skill_text ON gold_standard_annotations USING gin(to_tsvector('spanish', skill_text));

-- esco_skills indexes
CREATE INDEX idx_esco_skills_label_es ON esco_skills USING gin(to_tsvector('spanish', preferred_label_es));
CREATE INDEX idx_esco_skills_label_en ON esco_skills USING gin(to_tsvector('english', preferred_label_en));
CREATE INDEX idx_esco_skills_group ON esco_skills(skill_group);
CREATE INDEX idx_esco_skills_family ON esco_skills(skill_family);
CREATE INDEX idx_esco_skills_type ON esco_skills(skill_type);

-- esco_skill_labels indexes
CREATE INDEX idx_esco_labels_skill_uri ON esco_skill_labels(skill_uri);
CREATE INDEX idx_esco_labels_language ON esco_skill_labels(language_code);
CREATE INDEX idx_esco_labels_text ON esco_skill_labels USING gin(to_tsvector('spanish', label));

-- esco_skill_relations indexes
CREATE INDEX idx_esco_relations_source ON esco_skill_relations(source_skill_uri);
CREATE INDEX idx_esco_relations_target ON esco_skill_relations(target_skill_uri);
CREATE INDEX idx_esco_relations_type ON esco_skill_relations(relation_type);

-- custom_skill_mappings indexes
CREATE INDEX idx_custom_mappings_skill_text ON custom_skill_mappings USING gin(to_tsvector('spanish', skill_text));
CREATE INDEX idx_custom_mappings_esco_uri ON custom_skill_mappings(esco_skill_uri);

-- ============================================================================
-- COMENTARIOS PARA DOCUMENTACIÓN
-- ============================================================================

COMMENT ON TABLE raw_jobs IS 'Ofertas laborales scrapeadas sin procesar - tabla central del sistema';
COMMENT ON TABLE cleaned_jobs IS 'Texto limpio y normalizado listo para extracción de skills';
COMMENT ON TABLE extracted_skills IS 'Skills extraídas por Pipeline A (NER + Regex)';
COMMENT ON TABLE enhanced_skills IS 'Skills enriquecidas por Pipeline B (LLM con inferencia implícita)';
COMMENT ON TABLE skill_embeddings IS 'Vectores semánticos E5 768D para similitud y clustering';
COMMENT ON TABLE analysis_results IS 'Resultados de clustering HDBSCAN, proyecciones UMAP, y análisis temporal';
COMMENT ON TABLE gold_standard_annotations IS 'Anotaciones manuales de 300 jobs para evaluación de pipelines';
COMMENT ON TABLE esco_skills IS 'Taxonomía ESCO extendida: 14,174 skills (13,939 ESCO + 152 O*NET + 83 manual)';
COMMENT ON TABLE esco_skill_labels IS 'Etiquetas multilingües y sinónimos de skills ESCO';
COMMENT ON TABLE esco_skill_relations IS 'Relaciones jerárquicas entre skills (broader, narrower, related)';
COMMENT ON TABLE custom_skill_mappings IS 'Mapeos manuales de skills emergentes a taxonomía ESCO';
COMMENT ON TABLE esco_skill_groups IS 'Grupos jerárquicos de skills con auto-referencia (parent_group_id)';
COMMENT ON TABLE esco_skill_families IS 'Familias de alto nivel de clasificación de skills';

-- ============================================================================
-- FIN DEL SCHEMA
-- ============================================================================
