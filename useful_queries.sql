-- ================================================================================
-- QUERIES ÚTILES PARA ANÁLISIS DE LA TESIS
-- Observatorio de Demanda Laboral - Análisis de Skills en Ofertas Tecnológicas
-- ================================================================================

-- ================================================================================
-- CONEXIÓN A LA BASE DE DATOS
-- ================================================================================
-- Opción 1: Usando psql desde la línea de comandos
-- PGPASSWORD=123456 psql -h localhost -p 5433 -U labor_user -d labor_observatory

-- Opción 2: Conectar interactivamente
-- psql -h localhost -p 5433 -U labor_user -d labor_observatory
-- (Cuando pida contraseña, ingresa: 123456)

-- Opción 3: Usando una variable de entorno
-- export PGPASSWORD=123456
-- psql -h localhost -p 5433 -U labor_user -d labor_observatory

-- ================================================================================
-- SECCIÓN 0: EXPLORACIÓN DE ESTRUCTURA
-- ================================================================================

-- 0.1 Listar todas las tablas disponibles
\dt

-- 0.2 Ver estructura completa de cada tabla
\d raw_jobs
\d cleaned_jobs
\d gold_standard_annotations
\d extracted_skills
\d enhanced_skills
\d esco_skills
\d skill_embeddings
\d analysis_results
\d custom_skill_mappings

-- 0.3 Listar todas las tablas con sus tamaños
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY size_bytes DESC;

-- 0.4 Contar registros en cada tabla principal
SELECT
    'raw_jobs' as tabla,
    COUNT(*) as registros
FROM raw_jobs
UNION ALL
SELECT 'cleaned_jobs', COUNT(*) FROM cleaned_jobs
UNION ALL
SELECT 'gold_standard_annotations', COUNT(*) FROM gold_standard_annotations
UNION ALL
SELECT 'extracted_skills', COUNT(*) FROM extracted_skills
UNION ALL
SELECT 'enhanced_skills', COUNT(*) FROM enhanced_skills
UNION ALL
SELECT 'esco_skills', COUNT(*) FROM esco_skills
ORDER BY registros DESC;

-- 0.5 Ver todos los métodos de extracción disponibles
SELECT DISTINCT extraction_method, COUNT(*) as count
FROM extracted_skills
GROUP BY extraction_method
ORDER BY count DESC;

-- 0.6 Ver todos los modelos LLM usados
SELECT DISTINCT llm_model, COUNT(*) as count
FROM enhanced_skills
WHERE llm_model IS NOT NULL
GROUP BY llm_model
ORDER BY count DESC;

-- 0.7 Ver índices de una tabla específica
SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'raw_jobs'
ORDER BY indexname;

-- ================================================================================
-- SECCIÓN 1: ESTADÍSTICAS GENERALES DEL DATASET
-- ================================================================================

-- 1. Estadísticas Generales del Dataset
SELECT
    COUNT(*) as total_jobs,
    COUNT(DISTINCT portal) as num_portals,
    MIN(scraped_at) as first_scrape,
    MAX(scraped_at) as last_scrape,
    COUNT(DISTINCT country) as num_countries
FROM raw_jobs;

-- 2. Distribución por Portal
SELECT
    portal,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM raw_jobs
GROUP BY portal
ORDER BY total DESC;

-- 3. Distribución por País
SELECT
    country,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM raw_jobs
WHERE country IS NOT NULL
GROUP BY country
ORDER BY total DESC;

-- 3.1 Distribución combinada Portal x País
SELECT
    portal,
    country,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY country), 2) as pct_in_country
FROM raw_jobs
GROUP BY portal, country
ORDER BY country, total DESC;

-- ================================================================================
-- SECCIÓN 2: GOLD STANDARD (300 OFERTAS ANOTADAS MANUALMENTE)
-- ================================================================================

-- 4. Jobs del Gold Standard (últimas 10 ofertas anotadas)
SELECT
    j.job_id,
    j.title,
    j.portal,
    j.country,
    COUNT(CASE WHEN gs.skill_type = 'hard' THEN 1 END) as num_hard_skills,
    COUNT(CASE WHEN gs.skill_type = 'soft' THEN 1 END) as num_soft_skills,
    MAX(gs.annotation_date) as last_annotation
FROM raw_jobs j
JOIN gold_standard_annotations gs ON j.job_id = gs.job_id
GROUP BY j.job_id, j.title, j.portal, j.country
ORDER BY last_annotation DESC
LIMIT 10;

-- 5. Estadísticas del Gold Standard
SELECT
    COUNT(*) as total_jobs,
    SUM(hard_count) as total_hard_skills,
    SUM(soft_count) as total_soft_skills,
    ROUND(AVG(hard_count), 2) as avg_hard_per_job,
    ROUND(AVG(soft_count), 2) as avg_soft_per_job
FROM (
    SELECT
        job_id,
        COUNT(CASE WHEN skill_type = 'hard' THEN 1 END) as hard_count,
        COUNT(CASE WHEN skill_type = 'soft' THEN 1 END) as soft_count
    FROM gold_standard_annotations
    GROUP BY job_id
) subq;

-- 5.1 Top 20 Hard Skills más frecuentes en Gold Standard
SELECT
    skill_text,
    COUNT(*) as frequency,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM gold_standard_annotations
WHERE skill_type = 'hard'
GROUP BY skill_text
ORDER BY frequency DESC
LIMIT 20;

-- 5.2 Top 20 Soft Skills más frecuentes en Gold Standard
SELECT
    skill_text,
    COUNT(*) as frequency,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM gold_standard_annotations
WHERE skill_type = 'soft'
GROUP BY skill_text
ORDER BY frequency DESC
LIMIT 20;

-- ================================================================================
-- SECCIÓN 3: EXTRACTED SKILLS (NER + REGEX + PIPELINE A.1)
-- ================================================================================

-- 6. Skills Extraídas por NER (Named Entity Recognition)
SELECT
    j.job_id,
    j.title,
    es.skill_text,
    es.skill_type,
    es.confidence_score
FROM raw_jobs j
JOIN extracted_skills es ON j.job_id = es.job_id
WHERE es.extraction_method = 'ner'
LIMIT 20;

-- 7. Top 20 Skills Más Frecuentes (NER)
SELECT
    skill_text,
    COUNT(*) as frequency,
    skill_type
FROM extracted_skills
WHERE extraction_method = 'ner'
GROUP BY skill_text, skill_type
ORDER BY frequency DESC
LIMIT 20;

-- 7.1 Skills Extraídas por Regex
SELECT
    skill_text,
    COUNT(*) as frequency,
    skill_type
FROM extracted_skills
WHERE extraction_method = 'regex'
GROUP BY skill_text, skill_type
ORDER BY frequency DESC
LIMIT 20;

-- 7.2 Skills Extraídas por Pipeline A.1 (TF-IDF + N-grams)
SELECT
    skill_text,
    COUNT(*) as frequency,
    skill_type
FROM extracted_skills
WHERE extraction_method = 'pipeline-a1-tfidf-np'
GROUP BY skill_text, skill_type
ORDER BY frequency DESC
LIMIT 20;

-- 7.3 Comparación de métodos de extracción
SELECT
    extraction_method,
    COUNT(DISTINCT job_id) as jobs_processed,
    COUNT(*) as total_skills,
    ROUND(AVG(confidence_score)::numeric, 3) as avg_confidence,
    COUNT(DISTINCT skill_text) as unique_skills
FROM extracted_skills
GROUP BY extraction_method
ORDER BY jobs_processed DESC;

-- ================================================================================
-- SECCIÓN 4: ENHANCED SKILLS (PIPELINE B - LLM)
-- ================================================================================

-- 8. Skills Extraídas por LLM (Enhanced Skills)
SELECT
    j.job_id,
    j.title,
    es.normalized_skill,
    es.skill_type,
    es.llm_model
FROM raw_jobs j
JOIN enhanced_skills es ON j.job_id = es.job_id
WHERE es.is_duplicate = false
LIMIT 20;

-- 9. Top 20 Skills Más Frecuentes (Enhanced/LLM)
SELECT
    normalized_skill,
    COUNT(*) as frequency,
    skill_type
FROM enhanced_skills
WHERE is_duplicate = false
GROUP BY normalized_skill, skill_type
ORDER BY frequency DESC
LIMIT 20;

-- 9.1 Enhanced Skills - Estadísticas por Modelo LLM
SELECT
    llm_model,
    COUNT(DISTINCT job_id) as jobs_processed,
    COUNT(*) as total_skills,
    ROUND(AVG(llm_confidence)::numeric, 3) as avg_confidence,
    ROUND(AVG(processing_time_seconds)::numeric, 2) as avg_processing_time,
    SUM(tokens_used) as total_tokens
FROM enhanced_skills
WHERE is_duplicate = false
GROUP BY llm_model
ORDER BY jobs_processed DESC;

-- ================================================================================
-- SECCIÓN 5: MAPEO ESCO (TAXONOMÍA EUROPEA DE SKILLS)
-- ================================================================================

-- 10. Skills que Matchearon con ESCO
SELECT
    normalized_skill as original_skill,
    esco_concept_uri,
    esco_preferred_label,
    esco_match_method as match_type,
    llm_confidence as confidence_score
FROM enhanced_skills
WHERE esco_concept_uri IS NOT NULL
    AND is_duplicate = false
ORDER BY llm_confidence DESC
LIMIT 20;

-- 10.1 Estadísticas de Matching con ESCO
SELECT
    esco_match_method,
    COUNT(*) as total_matches,
    COUNT(DISTINCT normalized_skill) as unique_skills,
    ROUND(AVG(llm_confidence)::numeric, 3) as avg_confidence
FROM enhanced_skills
WHERE esco_concept_uri IS NOT NULL
    AND is_duplicate = false
GROUP BY esco_match_method
ORDER BY total_matches DESC;

-- 11. Emergent Skills (NO matchearon con ESCO)
SELECT DISTINCT
    es.normalized_skill,
    COUNT(*) as frequency
FROM enhanced_skills es
WHERE es.esco_concept_uri IS NULL
    AND es.is_duplicate = false
GROUP BY es.normalized_skill
ORDER BY frequency DESC
LIMIT 30;

-- 11.1 Porcentaje de Skills que matchearon vs no matchearon con ESCO
SELECT
    CASE
        WHEN esco_concept_uri IS NOT NULL THEN 'Matched with ESCO'
        ELSE 'Not Matched (Emergent)'
    END as match_status,
    COUNT(*) as total_skills,
    COUNT(DISTINCT normalized_skill) as unique_skills,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM enhanced_skills
WHERE is_duplicate = false
GROUP BY match_status;

-- ================================================================================
-- SECCIÓN 6: ANÁLISIS COMPARATIVO
-- ================================================================================

-- 12. Jobs con Mayor Número de Skills (NER)
SELECT
    j.job_id,
    j.title,
    j.portal,
    COUNT(es.extraction_id) as num_skills
FROM raw_jobs j
JOIN extracted_skills es ON j.job_id = es.job_id
WHERE es.extraction_method = 'ner'
GROUP BY j.job_id, j.title, j.portal
ORDER BY num_skills DESC
LIMIT 10;

-- 13. Jobs con Mayor Número de Skills (Enhanced/LLM)
SELECT
    j.job_id,
    j.title,
    j.portal,
    COUNT(es.enhancement_id) as num_skills
FROM raw_jobs j
JOIN enhanced_skills es ON j.job_id = es.job_id
WHERE es.is_duplicate = false
GROUP BY j.job_id, j.title, j.portal
ORDER BY num_skills DESC
LIMIT 10;

-- 14. Comparación NER vs LLM vs Gold Standard
SELECT
    j.job_id,
    j.title,
    COUNT(DISTINCT gs.id) FILTER (WHERE gs.skill_type = 'hard') as gold_hard,
    COUNT(DISTINCT es1.extraction_id) FILTER (WHERE es1.extraction_method = 'ner') as ner_count,
    COUNT(DISTINCT es2.enhancement_id) as llm_count
FROM raw_jobs j
JOIN gold_standard_annotations gs ON j.job_id = gs.job_id
LEFT JOIN extracted_skills es1 ON j.job_id = es1.job_id
LEFT JOIN enhanced_skills es2 ON j.job_id = es2.job_id AND es2.is_duplicate = false
GROUP BY j.job_id, j.title
ORDER BY gold_hard DESC
LIMIT 10;

-- 14.1 Overlap entre Gold Standard y Enhanced Skills
WITH gs_skills AS (
    SELECT DISTINCT
        job_id,
        LOWER(TRIM(skill_text)) as skill_normalized
    FROM gold_standard_annotations
    WHERE skill_type = 'hard'
),
enhanced AS (
    SELECT DISTINCT
        job_id,
        LOWER(TRIM(normalized_skill)) as skill_normalized
    FROM enhanced_skills
    WHERE is_duplicate = false
        AND skill_type = 'hard'
)
SELECT
    COUNT(DISTINCT gs.job_id) as jobs_in_gold_standard,
    COUNT(DISTINCT CASE WHEN e.skill_normalized IS NOT NULL THEN gs.job_id END) as jobs_with_matches,
    ROUND(
        COUNT(DISTINCT CASE WHEN e.skill_normalized IS NOT NULL THEN gs.job_id END) * 100.0 /
        COUNT(DISTINCT gs.job_id), 2
    ) as match_percentage
FROM gs_skills gs
LEFT JOIN enhanced e ON gs.job_id = e.job_id AND gs.skill_normalized = e.skill_normalized;

-- ================================================================================
-- SECCIÓN 7: ANÁLISIS TEMPORAL Y GEOGRÁFICO
-- ================================================================================

-- 15. Análisis Temporal: Jobs por Mes
SELECT
    DATE_TRUNC('month', scraped_at) as month,
    portal,
    COUNT(*) as jobs_scraped
FROM raw_jobs
WHERE scraped_at >= '2025-09-01'
GROUP BY month, portal
ORDER BY month DESC, jobs_scraped DESC;

-- 16. Jobs por Idioma
SELECT
    language,
    COUNT(*) as total,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM raw_jobs
WHERE language IS NOT NULL
GROUP BY language
ORDER BY total DESC;

-- 17. Top Skills por País (NER) - Mínimo 50 menciones
SELECT
    j.country,
    es.skill_text,
    COUNT(*) as frequency
FROM raw_jobs j
JOIN extracted_skills es ON j.job_id = es.job_id
WHERE j.country IN ('MX', 'CO', 'AR')
    AND es.extraction_method = 'ner'
    AND es.skill_type = 'hard'
GROUP BY j.country, es.skill_text
HAVING COUNT(*) > 50
ORDER BY j.country, frequency DESC
LIMIT 30;

-- 17.1 Top Skills por País (Enhanced/LLM)
SELECT
    j.country,
    es.normalized_skill,
    COUNT(*) as frequency
FROM raw_jobs j
JOIN enhanced_skills es ON j.job_id = es.job_id
WHERE j.country IN ('MX', 'CO', 'AR')
    AND es.is_duplicate = false
    AND es.skill_type = 'hard'
GROUP BY j.country, es.normalized_skill
HAVING COUNT(*) > 10
ORDER BY j.country, frequency DESC
LIMIT 30;

-- ================================================================================
-- SECCIÓN 8: CONTROL DE CALIDAD E INTEGRIDAD
-- ================================================================================

-- 18. Jobs sin Skills Extraídas (ningún método)
SELECT
    j.job_id,
    j.title,
    j.portal,
    j.scraped_at
FROM raw_jobs j
LEFT JOIN extracted_skills es ON j.job_id = es.job_id
WHERE es.extraction_id IS NULL
LIMIT 20;

-- 18.1 Estadísticas de Procesamiento
SELECT
    extraction_status,
    COUNT(*) as jobs,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) as percentage
FROM raw_jobs
GROUP BY extraction_status
ORDER BY jobs DESC;

-- 18.2 Jobs con Errores en Extracción
SELECT
    job_id,
    title,
    portal,
    extraction_error
FROM raw_jobs
WHERE extraction_status = 'failed'
LIMIT 20;

-- 18.3 Duplicados detectados
SELECT
    COUNT(*) as total_duplicates,
    COUNT(DISTINCT duplicate_of) as unique_originals
FROM raw_jobs
WHERE is_duplicate = true;

-- ================================================================================
-- SECCIÓN 9: ANÁLISIS DE TAXONOMÍA ESCO
-- ================================================================================

-- 19. Skills ESCO más usadas en las ofertas
SELECT
    e.esco_preferred_label,
    e.esco_concept_uri,
    COUNT(*) as frequency,
    COUNT(DISTINCT e.job_id) as jobs_count
FROM enhanced_skills e
WHERE e.esco_concept_uri IS NOT NULL
    AND e.is_duplicate = false
GROUP BY e.esco_preferred_label, e.esco_concept_uri
ORDER BY frequency DESC
LIMIT 30;

-- 19.1 Skills ESCO por familia
SELECT
    es.skill_family,
    COUNT(DISTINCT e.normalized_skill) as unique_skills,
    COUNT(*) as total_mentions
FROM enhanced_skills e
JOIN esco_skills es ON e.esco_concept_uri = es.skill_uri
WHERE e.is_duplicate = false
    AND es.skill_family IS NOT NULL
GROUP BY es.skill_family
ORDER BY total_mentions DESC;

-- 19.2 Skills ESCO por tipo
SELECT
    es.skill_type as esco_skill_type,
    COUNT(DISTINCT e.normalized_skill) as unique_skills,
    COUNT(*) as total_mentions
FROM enhanced_skills e
JOIN esco_skills es ON e.esco_concept_uri = es.skill_uri
WHERE e.is_duplicate = false
    AND es.skill_type IS NOT NULL
GROUP BY es.skill_type
ORDER BY total_mentions DESC;

-- ================================================================================
-- SECCIÓN 10: QUERIES AVANZADAS
-- ================================================================================

-- 20. Skills que aparecen en múltiples países
SELECT
    es.normalized_skill,
    COUNT(DISTINCT j.country) as num_countries,
    STRING_AGG(DISTINCT j.country::text, ', ') as countries,
    COUNT(*) as total_frequency
FROM raw_jobs j
JOIN enhanced_skills es ON j.job_id = es.job_id
WHERE es.is_duplicate = false
GROUP BY es.normalized_skill
HAVING COUNT(DISTINCT j.country) > 1
ORDER BY total_frequency DESC
LIMIT 30;

-- 21. Co-ocurrencia de skills (skills que aparecen juntas)
WITH job_skills AS (
    SELECT
        job_id,
        normalized_skill
    FROM enhanced_skills
    WHERE is_duplicate = false
        AND skill_type = 'hard'
)
SELECT
    s1.normalized_skill as skill_1,
    s2.normalized_skill as skill_2,
    COUNT(*) as co_occurrence
FROM job_skills s1
JOIN job_skills s2 ON s1.job_id = s2.job_id AND s1.normalized_skill < s2.normalized_skill
GROUP BY s1.normalized_skill, s2.normalized_skill
HAVING COUNT(*) >= 10
ORDER BY co_occurrence DESC
LIMIT 30;

-- 22. Análisis de longitud de ofertas vs número de skills
SELECT
    cj.combined_word_count / 100 * 100 as word_count_range,
    COUNT(DISTINCT j.job_id) as num_jobs,
    ROUND(AVG(skill_count), 2) as avg_skills
FROM raw_jobs j
JOIN cleaned_jobs cj ON j.job_id = cj.job_id
LEFT JOIN (
    SELECT job_id, COUNT(*) as skill_count
    FROM enhanced_skills
    WHERE is_duplicate = false
    GROUP BY job_id
) es ON j.job_id = es.job_id
WHERE cj.combined_word_count IS NOT NULL
GROUP BY word_count_range
ORDER BY word_count_range;

-- ================================================================================
-- SECCIÓN 11: QUERIES PARA TESIS / REPORTES
-- ================================================================================

-- 23. Resumen ejecutivo completo
SELECT
    'Total Jobs' as metric,
    COUNT(*)::text as value
FROM raw_jobs
UNION ALL
SELECT 'Jobs in Gold Standard', COUNT(DISTINCT job_id)::text
FROM gold_standard_annotations
UNION ALL
SELECT 'Skills in Gold Standard', COUNT(*)::text
FROM gold_standard_annotations
UNION ALL
SELECT 'Jobs Processed (NER)', COUNT(DISTINCT job_id)::text
FROM extracted_skills WHERE extraction_method = 'ner'
UNION ALL
SELECT 'Skills Extracted (NER)', COUNT(*)::text
FROM extracted_skills WHERE extraction_method = 'ner'
UNION ALL
SELECT 'Jobs Processed (LLM)', COUNT(DISTINCT job_id)::text
FROM enhanced_skills WHERE is_duplicate = false
UNION ALL
SELECT 'Skills Enhanced (LLM)', COUNT(*)::text
FROM enhanced_skills WHERE is_duplicate = false
UNION ALL
SELECT 'Skills Matched with ESCO', COUNT(*)::text
FROM enhanced_skills WHERE esco_concept_uri IS NOT NULL AND is_duplicate = false
UNION ALL
SELECT 'Unique ESCO Skills', COUNT(DISTINCT esco_concept_uri)::text
FROM enhanced_skills WHERE esco_concept_uri IS NOT NULL AND is_duplicate = false;

-- ================================================================================
-- NOTAS IMPORTANTES
-- ================================================================================
-- 1. La tabla principal de jobs es 'raw_jobs' (NO 'jobs')
-- 2. El campo de portal es 'portal' (NO 'source')
-- 3. Gold Standard está en 'gold_standard_annotations' (las skills están en filas separadas)
-- 4. No hay tablas 'llm_extracted_skills' separadas - todo está en 'enhanced_skills'
-- 5. Métodos de extracción disponibles: 'ner', 'regex', 'pipeline-a1-tfidf-np'
-- 6. Los campos de skills son: 'skill_text' (extracted_skills) y 'normalized_skill' (enhanced_skills)
-- 7. Para usar ROUND con decimales en confidence scores, hay que castear a ::numeric
-- ================================================================================
