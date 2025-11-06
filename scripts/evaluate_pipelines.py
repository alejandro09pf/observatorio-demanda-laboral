#!/usr/bin/env python3
"""
Script de evaluación de pipelines - Único script necesario.

MODOS DE USO:

1. MODO GOLD STANDARD - Evaluación completa vs ground truth
   Compara Pipeline A y/o Pipeline B contra gold standard (300 jobs anotados)
   Incluye: comparación texto normalizado + post-ESCO + análisis de impacto

   python scripts/evaluate_pipelines.py \\
     --mode gold-standard \\
     --pipelines pipeline-a llama-3.2-3b gemma-3-4b

2. MODO LLM COMPARISON - Comparar múltiples LLMs entre sí
   Compara LLMs head-to-head: overlap, avg skills/job, estadísticas

   python scripts/evaluate_pipelines.py \\
     --mode llm-comparison \\
     --llm-models llama-3.2-3b gemma-3-4b qwen2.5-3b mistral-7b

3. MODO DESCRIPTIVE - Análisis descriptivo de un pipeline
   Analiza Pipeline A o B sin gold standard: stats + cobertura ESCO

   python scripts/evaluate_pipelines.py \\
     --mode descriptive \\
     --pipeline pipeline-a

OUTPUTS:
  - Reporte Markdown: data/reports/EVALUATION_REPORT_<timestamp>.md
  - CSV: data/reports/*.csv
  - JSON: data/reports/*.json
"""

import sys
import os
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import json
import csv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.evaluation.dual_comparator import DualPipelineComparator
from src.evaluation.metrics import print_metrics

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def mode_gold_standard(comparator: DualPipelineComparator, pipelines: List[str], output_dir: Path, skill_type: str = None):
    """
    Modo 1: Evaluación completa contra gold standard.

    Args:
        comparator: DualPipelineComparator instance
        pipelines: Lista de pipelines (ej: ["pipeline-a", "llama-3.2-3b"])
        output_dir: Directorio de salida
        skill_type: Filtrar por 'hard', 'soft', 'both', o None (todas)
    """
    logger.info("\n" + "="*80)
    logger.info("MODE: GOLD STANDARD EVALUATION")
    if skill_type and skill_type != 'both':
        logger.info(f"SKILL TYPE FILTER: {skill_type.upper()}")
    logger.info("="*80)

    # Cargar gold standard
    logger.info("\n[1/3] Loading gold standard...")
    gold_standard = comparator.load_gold_standard()
    job_ids = list(gold_standard.skills_by_job.keys())
    logger.info(f"  ✅ {len(job_ids)} jobs loaded")

    # Cargar pipelines
    logger.info("\n[2/3] Loading pipelines...")
    pipeline_data = []

    for pipeline_name in pipelines:
        if pipeline_name.lower() == 'pipeline-a':
            logger.info(f"  Loading Pipeline A...")
            pipeline = comparator.load_pipeline_a(job_ids=job_ids)
            if pipeline.skills_by_job:
                pipeline_data.append(pipeline)
            else:
                logger.warning(f"  ⚠️  Pipeline A has no data")
        else:
            # Assume it's an LLM model
            logger.info(f"  Loading Pipeline B ({pipeline_name})...")
            try:
                pipeline = comparator.load_pipeline_b(llm_model=pipeline_name, job_ids=job_ids)
                if pipeline.skills_by_job:
                    pipeline_data.append(pipeline)
                else:
                    logger.warning(f"  ⚠️  {pipeline_name} has no data")
            except Exception as e:
                logger.error(f"  ❌ Error loading {pipeline_name}: {e}")

    if not pipeline_data:
        logger.error("❌ No pipeline data available for evaluation!")
        return

    logger.info(f"  ✅ {len(pipeline_data)} pipelines loaded")

    # Si skill_type es 'both', ejecutar ambas evaluaciones
    if skill_type == 'both':
        logger.info("\n[3/3] Running dual comparison for HARD skills...")
        report_hard = comparator.run_dual_comparison(gold_standard, pipeline_data, skill_type_filter='hard')
        generate_gold_standard_report(report_hard, output_dir, suffix='_hard')

        logger.info("\n[3/3] Running dual comparison for SOFT skills...")
        report_soft = comparator.run_dual_comparison(gold_standard, pipeline_data, skill_type_filter='soft')
        generate_gold_standard_report(report_soft, output_dir, suffix='_soft')
    else:
        # Ejecutar comparación dual con filtro
        logger.info("\n[3/3] Running dual comparison...")
        filter_value = skill_type if skill_type and skill_type != 'both' else None
        report = comparator.run_dual_comparison(gold_standard, pipeline_data, skill_type_filter=filter_value)
        # Generar reportes
        generate_gold_standard_report(report, output_dir)

    logger.info("\n" + "="*80)
    logger.info("✅ EVALUATION COMPLETE")
    logger.info(f"   Reports saved to: {output_dir}")
    logger.info("="*80)


def mode_llm_comparison(comparator: DualPipelineComparator, llm_models: List[str], output_dir: Path):
    """
    Modo 2: Comparar múltiples LLMs head-to-head.

    Args:
        comparator: DualPipelineComparator instance
        llm_models: Lista de modelos LLM
        output_dir: Directorio de salida
    """
    logger.info("\n" + "="*80)
    logger.info("MODE: LLM HEAD-TO-HEAD COMPARISON")
    logger.info("="*80)

    logger.info(f"\nComparing {len(llm_models)} LLMs:")
    for model in llm_models:
        logger.info(f"  - {model}")

    # Comparar
    results = comparator.compare_llms_head_to_head(llm_models)

    # Generar reporte
    generate_llm_comparison_report(results, output_dir)

    logger.info("\n" + "="*80)
    logger.info("✅ COMPARISON COMPLETE")
    logger.info(f"   Reports saved to: {output_dir}")
    logger.info("="*80)


def mode_descriptive(comparator: DualPipelineComparator, pipeline: str, output_dir: Path):
    """
    Modo 3: Análisis descriptivo de un pipeline.

    Args:
        comparator: DualPipelineComparator instance
        pipeline: Nombre del pipeline ("pipeline-a" o nombre de LLM)
        output_dir: Directorio de salida
    """
    logger.info("\n" + "="*80)
    logger.info("MODE: DESCRIPTIVE ANALYSIS")
    logger.info("="*80)

    # Cargar pipeline
    if pipeline.lower() == 'pipeline-a':
        logger.info("\nLoading Pipeline A...")
        pipeline_data = comparator.load_pipeline_a()
    else:
        logger.info(f"\nLoading Pipeline B ({pipeline})...")
        pipeline_data = comparator.load_pipeline_b(llm_model=pipeline)

    if not pipeline_data.skills_by_job:
        logger.error(f"❌ No data found for {pipeline}")
        return

    # Analizar
    analysis = comparator.evaluate_pipeline_without_gold(pipeline_data, map_to_esco=True)

    # Generar reporte
    generate_descriptive_report(analysis, output_dir)

    logger.info("\n" + "="*80)
    logger.info("✅ ANALYSIS COMPLETE")
    logger.info(f"   Reports saved to: {output_dir}")
    logger.info("="*80)


def generate_gold_standard_report(report, output_dir: Path, suffix: str = ''):
    """Genera reportes para modo gold standard."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Markdown report
    md_file = output_dir / f"EVALUATION_REPORT{suffix}_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# Evaluación de Pipelines vs Gold Standard\n\n")
        f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Jobs evaluados:** {report.total_jobs}\n")
        f.write(f"**Pipelines:** {', '.join(report.pipeline_names)}\n\n")
        f.write("---\n\n")

        # Comparación 1: Texto normalizado
        f.write("## 1. Extracción Pura (Sin Mapeo ESCO)\n\n")
        f.write("| Pipeline | Precision | Recall | F1-Score | Support | Predicted |\n")
        f.write("|----------|-----------|--------|----------|---------|----------|\n")
        for name, result in report.pure_text_results.items():
            m = result.metrics
            f.write(f"| {name:30s} | {m.precision:.4f} | {m.recall:.4f} | {m.f1_score:.4f} | {m.support:4d} | {m.predicted_count:4d} |\n")

        # Ganador
        best = max(report.pure_text_results.items(), key=lambda x: x[1].metrics.f1_score)
        f.write(f"\n**Ganador:** {best[0]} (F1={best[1].metrics.f1_score:.4f})\n\n")

        # Comparación 2: Post-ESCO
        f.write("---\n\n## 2. Post-Mapeo ESCO (Estandarización)\n\n")
        f.write("| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |\n")
        f.write("|----------|-----------|--------|----------|----------------|\n")
        for name, result in report.post_esco_results.items():
            m = result.metrics
            cov = result.coverage_esco or 0.0
            f.write(f"| {name:30s} | {m.precision:.4f} | {m.recall:.4f} | {m.f1_score:.4f} | {cov:.2%} |\n")

        best_esco = max(report.post_esco_results.items(), key=lambda x: x[1].metrics.f1_score)
        f.write(f"\n**Ganador:** {best_esco[0]} (F1={best_esco[1].metrics.f1_score:.4f})\n\n")

        # Impacto ESCO
        f.write("---\n\n## 3. Impacto del Mapeo a ESCO\n\n")
        f.write("| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |\n")
        f.write("|----------|------|----------|----------------|\n")
        for name, impact in report.esco_impact.items():
            f.write(f"| {name:30s} | {impact['delta_f1']:+.4f} | {impact['delta_f1_percent']:+.2f}% | {impact['skills_lost_count']:3d} |\n")

        # Skills emergentes
        f.write(f"\n---\n\n## 4. Skills Emergentes (No en ESCO)\n\n")
        f.write(f"**Total:** {len(report.emergent_skills)}\n\n")
        if report.emergent_skills:
            for skill in report.emergent_skills[:30]:
                f.write(f"- {skill}\n")

    logger.info(f"  ✅ Markdown: {md_file}")

    # CSV: Pure text
    csv_pure = output_dir / f"comparison_pure{suffix}_{timestamp}.csv"
    with open(csv_pure, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Pipeline', 'Precision', 'Recall', 'F1', 'Support', 'Predicted'])
        for name, result in report.pure_text_results.items():
            m = result.metrics
            writer.writerow([name, f"{m.precision:.4f}", f"{m.recall:.4f}", f"{m.f1_score:.4f}", m.support, m.predicted_count])

    # CSV: Post-ESCO
    csv_esco = output_dir / f"comparison_esco{suffix}_{timestamp}.csv"
    with open(csv_esco, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Pipeline', 'Precision', 'Recall', 'F1', 'ESCO_Coverage'])
        for name, result in report.post_esco_results.items():
            m = result.metrics
            cov = result.coverage_esco or 0.0
            writer.writerow([name, f"{m.precision:.4f}", f"{m.recall:.4f}", f"{m.f1_score:.4f}", f"{cov:.4f}"])

    logger.info(f"  ✅ CSV Pure: {csv_pure}")
    logger.info(f"  ✅ CSV ESCO: {csv_esco}")

    # JSON
    json_file = output_dir / f"evaluation{suffix}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

    logger.info(f"  ✅ JSON: {json_file}")


def generate_llm_comparison_report(results: Dict, output_dir: Path):
    """Genera reportes para modo LLM comparison."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Markdown
    md_file = output_dir / f"LLM_COMPARISON_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write("# Comparación Head-to-Head de LLMs\n\n")
        f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"**Modelos:** {', '.join(results['models_compared'])}\n\n")
        f.write("---\n\n")

        # Estadísticas
        f.write("## Estadísticas por Modelo\n\n")
        f.write("| Modelo | Jobs | Total Skills | Unique Skills | Avg/Job |\n")
        f.write("|--------|------|--------------|---------------|----------|\n")
        for model, stats in results['statistics'].items():
            f.write(f"| {model:30s} | {stats['total_jobs']:4d} | {stats['total_skills']:5d} | {stats['unique_skills']:4d} | {stats['avg_skills_per_job']:5.1f} |\n")

        # Overlaps
        if results['overlaps']:
            f.write("\n## Overlap entre Modelos (Jaccard Similarity)\n\n")
            f.write("| Comparación | Jaccard | Skills Comunes | Total Único |\n")
            f.write("|-------------|---------|----------------|-------------|\n")
            for comp, data in results['overlaps'].items():
                f.write(f"| {comp:40s} | {data['jaccard_similarity']:.4f} | {data['common_skills']:4d} | {data['total_unique']:4d} |\n")

    logger.info(f"  ✅ Markdown: {md_file}")

    # JSON
    json_file = output_dir / f"llm_comparison_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    logger.info(f"  ✅ JSON: {json_file}")


def generate_descriptive_report(analysis: Dict, output_dir: Path):
    """Genera reportes para modo descriptive."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pipeline_name = analysis['pipeline_name'].replace(' ', '_')

    # Markdown
    md_file = output_dir / f"DESCRIPTIVE_{pipeline_name}_{timestamp}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(f"# Análisis Descriptivo: {analysis['pipeline_name']}\n\n")
        f.write(f"**Fecha:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")

        f.write("## Estadísticas Generales\n\n")
        f.write(f"- **Total jobs:** {analysis['total_jobs']}\n")
        f.write(f"- **Total extracciones:** {analysis['total_skill_extractions']}\n")
        f.write(f"- **Skills únicos (raw):** {analysis['unique_skills']}\n")
        f.write(f"- **Skills únicos (normalized):** {analysis['unique_skills_normalized']}\n")
        f.write(f"- **Promedio skills/job:** {analysis['avg_skills_per_job']:.1f}\n\n")

        if 'esco_coverage' in analysis:
            f.write("## Cobertura ESCO\n\n")
            f.write(f"- **Cobertura:** {analysis['esco_coverage']:.2%}\n")
            f.write(f"- **Mapeados:** {analysis['esco_mapped_count']}\n")
            f.write(f"- **No mapeados:** {analysis['esco_unmapped_count']}\n\n")

            if analysis.get('esco_unmapped_sample'):
                f.write("### Skills No Mapeados (sample)\n\n")
                for skill in analysis['esco_unmapped_sample']:
                    f.write(f"- {skill}\n")

    logger.info(f"  ✅ Markdown: {md_file}")

    # JSON
    json_file = output_dir / f"descriptive_{pipeline_name}_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(analysis, f, indent=2, ensure_ascii=False)

    logger.info(f"  ✅ JSON: {json_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Evaluación de pipelines - Único script necesario",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        '--mode',
        required=True,
        choices=['gold-standard', 'llm-comparison', 'descriptive'],
        help='Modo de evaluación'
    )

    # Gold standard mode
    parser.add_argument(
        '--pipelines',
        nargs='+',
        help='[gold-standard] Pipelines a evaluar (ej: pipeline-a llama-3.2-3b)'
    )

    # LLM comparison mode
    parser.add_argument(
        '--llm-models',
        nargs='+',
        help='[llm-comparison] Modelos LLM a comparar'
    )

    # Descriptive mode
    parser.add_argument(
        '--pipeline',
        help='[descriptive] Pipeline a analizar (pipeline-a o nombre de LLM)'
    )

    parser.add_argument(
        '--output-dir',
        default='data/reports',
        help='Directorio de salida (default: data/reports)'
    )

    parser.add_argument(
        '--skill-type',
        choices=['hard', 'soft', 'both', 'all'],
        default='all',
        help='[gold-standard] Filtrar por tipo de skill: hard, soft, both (evalúa ambos por separado), all (evalúa todas juntas) - default: all'
    )

    args = parser.parse_args()

    # Validar argumentos por modo
    if args.mode == 'gold-standard' and not args.pipelines:
        parser.error("--pipelines es requerido para modo gold-standard")
    if args.mode == 'llm-comparison' and not args.llm_models:
        parser.error("--llm-models es requerido para modo llm-comparison")
    if args.mode == 'descriptive' and not args.pipeline:
        parser.error("--pipeline es requerido para modo descriptive")

    # Crear output dir
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Inicializar comparator
    comparator = DualPipelineComparator()

    # Ejecutar modo correspondiente
    if args.mode == 'gold-standard':
        skill_type = None if args.skill_type == 'all' else args.skill_type
        mode_gold_standard(comparator, args.pipelines, output_dir, skill_type=skill_type)
    elif args.mode == 'llm-comparison':
        mode_llm_comparison(comparator, args.llm_models, output_dir)
    elif args.mode == 'descriptive':
        mode_descriptive(comparator, args.pipeline, output_dir)


if __name__ == '__main__':
    main()
