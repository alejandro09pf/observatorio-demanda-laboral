#!/usr/bin/env python3
"""
Qualitative Cluster Analysis Script
Analiza clusters cualitativamente e identifica skills sin mapeo ESCO
"""

import psycopg2
import json
import logging
from collections import defaultdict
from typing import Dict, List, Tuple

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_CONFIG = {
    'host': 'localhost',
    'port': 5433,
    'database': 'labor_observatory',
    'user': 'labor_user',
    'password': '123456'
}

def get_db_connection():
    """Establece conexión a la base de datos"""
    return psycopg2.connect(**DB_CONFIG)

def analyze_clusters_from_db(source: str, table: str, limit_clusters: int = 20) -> Dict:
    """
    Analiza clusters desde la DB para un experimento específico

    Args:
        source: Nombre del experimento (ej: "Manual 300 Pre-ESCO")
        table: Tabla de origen (gold_standard_annotations, extracted_skills)
        limit_clusters: Cuántos clusters analizar en detalle

    Returns:
        Dict con análisis de clusters
    """
    conn = get_db_connection()
    cur = conn.cursor()

    logger.info(f"\n{'='*80}")
    logger.info(f"ANALIZANDO CLUSTERS: {source}")
    logger.info(f"{'='*80}")

    # Query para obtener skills con sus embeddings y clustering
    # Nota: Asumiendo que ya se corrió clustering y los labels están en algún lugar
    # Por ahora vamos a hacer análisis directo de las skills

    if table == "gold_standard_annotations":
        query = """
        SELECT skill_text, COUNT(*) as frequency, COUNT(DISTINCT job_id) as job_count
        FROM gold_standard_annotations
        GROUP BY skill_text
        ORDER BY frequency DESC
        """
    else:
        query = f"""
        SELECT skill_text, COUNT(*) as frequency, COUNT(DISTINCT job_id) as job_count
        FROM extracted_skills
        WHERE source = '{source}'
        GROUP BY skill_text
        ORDER BY frequency DESC
        """

    cur.execute(query)
    skills = cur.fetchall()

    logger.info(f"Total skills: {len(skills)}")
    logger.info(f"Top 20 skills por frecuencia:")
    for i, (skill, freq, jobs) in enumerate(skills[:20], 1):
        logger.info(f"  {i:2d}. {skill:40s} (freq: {freq:3d}, jobs: {jobs:3d})")

    cur.close()
    conn.close()

    return {
        'source': source,
        'total_skills': len(skills),
        'top_skills': [(s[0], s[1], s[2]) for s in skills[:50]]
    }

def analyze_unmapped_esco_skills(source_name: str, query: str) -> List[Tuple]:
    """
    Identifica skills que NO mapearon a ESCO

    Args:
        source_name: Nombre de la fuente (Pipeline A, B, Manual)
        query: SQL query para obtener skills sin mapeo

    Returns:
        Lista de (skill_text, frequency, job_count)
    """
    conn = get_db_connection()
    cur = conn.cursor()

    logger.info(f"\n{'='*80}")
    logger.info(f"SKILLS SIN MAPEO ESCO: {source_name}")
    logger.info(f"{'='*80}")

    cur.execute(query)
    unmapped = cur.fetchall()

    logger.info(f"Total skills sin ESCO: {len(unmapped)}")
    logger.info(f"\nTop 50 skills sin mapeo ESCO:")
    logger.info(f"{'Rank':>4} | {'Skill':50s} | {'Freq':>5} | {'Jobs':>5}")
    logger.info("-" * 80)

    for i, (skill, freq, jobs) in enumerate(unmapped[:50], 1):
        logger.info(f"{i:4d} | {skill:50s} | {freq:5d} | {jobs:5d}")

    cur.close()
    conn.close()

    return unmapped[:50]

def classify_unmapped_skills_interactive(skills: List[Tuple]) -> Dict:
    """
    Ayuda a clasificar manualmente skills sin ESCO

    Categorías:
    1. Skills chilenas válidas
    2. Tecnología emergente
    3. Errores de extracción
    4. Otras
    """
    logger.info("\n" + "="*80)
    logger.info("CLASIFICACIÓN MANUAL DE SKILLS")
    logger.info("="*80)
    logger.info("\nRevisa las top 50 skills sin ESCO arriba.")
    logger.info("\nPara clasificación manual, agrúpalas en:")
    logger.info("  1. Skills chilenas válidas (ej: legislación chilena, AFPs)")
    logger.info("  2. Tecnología emergente (ej: ChatGPT, Kubernetes)")
    logger.info("  3. Errores de extracción (ej: Piano, Europa, Oferta)")
    logger.info("  4. Soft skills válidas")
    logger.info("  5. Otras")

    # Por ahora solo retornamos la lista para clasificación manual externa
    return {
        'total_unmapped': len(skills),
        'top_50': [{'skill': s[0], 'freq': s[1], 'jobs': s[2]} for s in skills],
        'needs_manual_classification': True
    }

def main():
    """Ejecuta análisis completo"""

    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS CUALITATIVO DE CLUSTERING")
    logger.info("="*80)

    # PARTE 1: Análisis de clusters por experimento
    logger.info("\n\n### PARTE 1: ANÁLISIS DE TOP SKILLS POR EXPERIMENTO ###\n")

    # Manual 300 Pre-ESCO
    manual_analysis = analyze_clusters_from_db(
        source="Manual 300 Pre-ESCO",
        table="gold_standard_annotations"
    )

    # Pipeline B Pre-ESCO
    pipeline_b_pre = analyze_clusters_from_db(
        source="Pipeline B (gemma-3-4b-instruct)",
        table="extracted_skills"
    )

    # PARTE 2: Skills sin mapeo ESCO
    logger.info("\n\n### PARTE 2: SKILLS SIN MAPEO A ESCO ###\n")

    # Manual annotations sin ESCO
    manual_unmapped_query = """
    SELECT
        gsa.skill_text,
        COUNT(*) as frequency,
        COUNT(DISTINCT gsa.job_id) as job_count
    FROM gold_standard_annotations gsa
    LEFT JOIN esco_skills es ON LOWER(TRIM(gsa.skill_text)) = LOWER(TRIM(es.preferred_label))
    WHERE es.skill_uri IS NULL
    GROUP BY gsa.skill_text
    ORDER BY frequency DESC
    LIMIT 50
    """

    manual_unmapped = analyze_unmapped_esco_skills(
        "Manual Annotations (Gold Standard)",
        manual_unmapped_query
    )

    # Pipeline B sin ESCO
    pipeline_b_unmapped_query = """
    SELECT
        es.skill_text,
        COUNT(*) as frequency,
        COUNT(DISTINCT es.job_id) as job_count
    FROM extracted_skills es
    WHERE es.source = 'Pipeline B (gemma-3-4b-instruct)'
      AND (es.normalized_skill IS NULL OR es.normalized_skill = '')
    GROUP BY es.skill_text
    ORDER BY frequency DESC
    LIMIT 50
    """

    pipeline_b_unmapped = analyze_unmapped_esco_skills(
        "Pipeline B (LLM Gemma)",
        pipeline_b_unmapped_query
    )

    # Pipeline A sin ESCO
    pipeline_a_unmapped_query = """
    SELECT
        es.skill_text,
        COUNT(*) as frequency,
        COUNT(DISTINCT es.job_id) as job_count
    FROM extracted_skills es
    WHERE es.source = 'Pipeline A (NER+Regex)'
      AND (es.normalized_skill IS NULL OR es.normalized_skill = '')
    GROUP BY es.skill_text
    ORDER BY frequency DESC
    LIMIT 50
    """

    pipeline_a_unmapped = analyze_unmapped_esco_skills(
        "Pipeline A (NER+Regex)",
        pipeline_a_unmapped_query
    )

    # Guardar resultados
    results = {
        'cluster_analysis': {
            'manual': manual_analysis,
            'pipeline_b_pre': pipeline_b_pre
        },
        'unmapped_esco': {
            'manual': classify_unmapped_skills_interactive(manual_unmapped),
            'pipeline_b': classify_unmapped_skills_interactive(pipeline_b_unmapped),
            'pipeline_a': classify_unmapped_skills_interactive(pipeline_a_unmapped)
        }
    }

    output_file = 'outputs/clustering/qualitative_analysis_results.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"\n✅ Resultados guardados en: {output_file}")

    logger.info("\n" + "="*80)
    logger.info("ANÁLISIS COMPLETO")
    logger.info("="*80)
    logger.info("\nPróximos pasos:")
    logger.info("1. Revisar outputs arriba")
    logger.info("2. Clasificar manualmente top 50 skills sin ESCO de cada fuente")
    logger.info("3. Documentar hallazgos en CLUSTERING_IMPLEMENTATION_LOG.md")

if __name__ == "__main__":
    main()
