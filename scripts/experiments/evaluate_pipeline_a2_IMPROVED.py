#!/usr/bin/env python3
"""
Evaluación de Pipeline A.2 - Versión MEJORADA
"""

import json
import sys
import psycopg2
from typing import Dict, List, Set
from collections import defaultdict

sys.path.insert(0, '/Users/nicocamacho/Documents/Tesis/observatorio-demanda-laboral')
from scripts.experiments.pipeline_a2_IMPROVED import (
    extract_skills_improved,
    load_esco_skills_enhanced,
    normalize_text
)


def load_gold_standard(db_config: Dict) -> Dict[str, Set[str]]:
    """Carga gold standard (hard skills)"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    query = """
        SELECT job_id, skill_text
        FROM gold_standard_annotations
        WHERE skill_type = 'hard'
        ORDER BY job_id
    """

    cur.execute(query)
    rows = cur.fetchall()

    gold_standard = defaultdict(set)

    for row in rows:
        job_id = row[0]
        skill_text = row[1]
        normalized = normalize_text(skill_text)
        gold_standard[job_id].add(normalized)

    cur.close()
    conn.close()

    return dict(gold_standard)


def load_job_descriptions(db_config: Dict, job_ids: List[str]) -> Dict[str, str]:
    """Carga descripciones"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    placeholders = ','.join(['%s'] * len(job_ids))
    query = f"""
        SELECT job_id::text, combined_text
        FROM cleaned_jobs
        WHERE job_id IN ({placeholders})
    """

    cur.execute(query, job_ids)
    rows = cur.fetchall()

    job_descriptions = {row[0]: row[1] for row in rows}

    cur.close()
    conn.close()

    return job_descriptions


def calculate_metrics(predicted: Set[str], gold: Set[str]) -> Dict:
    """Calcula Precision, Recall, F1"""
    tp = len(predicted.intersection(gold))
    fp = len(predicted - gold)
    fn = len(gold - predicted)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'precision': round(precision * 100, 2),
        'recall': round(recall * 100, 2),
        'f1': round(f1 * 100, 2),
        'true_positives': tp,
        'false_positives': fp,
        'false_negatives': fn
    }


def main():
    print("=" * 70)
    print("PIPELINE A.2 - EVALUACIÓN VERSIÓN MEJORADA")
    print("=" * 70)
    print()

    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    # Cargar ESCO + custom
    print("📥 Cargando skills (ESCO + custom)...")
    esco_dict = load_esco_skills_enhanced(DB_CONFIG, tech_only=True)
    print(f"   ✅ {len(esco_dict)} skills cargadas\n")

    # Cargar gold standard
    print("📥 Cargando gold standard...")
    gold_standard = load_gold_standard(DB_CONFIG)
    print(f"   ✅ {len(gold_standard)} ofertas cargadas\n")

    # Cargar descripciones
    print("📥 Cargando descripciones...")
    job_ids = list(gold_standard.keys())
    job_descriptions = load_job_descriptions(DB_CONFIG, job_ids)
    print(f"   ✅ {len(job_descriptions)} descripciones cargadas\n")

    # Evaluar
    print("🚀 Evaluando Pipeline A.2 MEJORADO...")
    print("   (Con alias, fuzzy=0, substring, custom skills)")
    print()

    per_job_results = []
    all_predicted = set()
    all_gold = set()

    for idx, (job_id, job_description) in enumerate(job_descriptions.items(), 1):
        if idx % 50 == 0:
            print(f"   Procesadas {idx}/{len(job_descriptions)} ofertas...")

        # Extraer skills (fuzzy=0 para velocidad)
        extracted = extract_skills_improved(
            job_description,
            esco_dict,
            max_n=4,
            fuzzy_threshold=0,  # Desactivar fuzzy por velocidad
            use_substring=True
        )

        predicted_skills = {normalize_text(s['skill_text']) for s in extracted}
        gold_skills = gold_standard.get(job_id, set())

        metrics = calculate_metrics(predicted_skills, gold_skills)

        per_job_results.append({
            'job_id': job_id,
            'predicted_count': len(predicted_skills),
            'gold_count': len(gold_skills),
            'f1': metrics['f1'],
            'precision': metrics['precision'],
            'recall': metrics['recall'],
            'true_positives': metrics['true_positives'],
            'false_positives': metrics['false_positives'],
            'false_negatives': metrics['false_negatives']
        })

        all_predicted.update(predicted_skills)
        all_gold.update(gold_skills)

    print("   ✅ Evaluación completada\n")

    # Métricas globales
    overall_metrics = calculate_metrics(all_predicted, all_gold)
    overall_metrics['avg_skills_per_job'] = round(
        sum(r['predicted_count'] for r in per_job_results) / len(per_job_results), 2
    )
    overall_metrics['total_jobs'] = len(per_job_results)

    # Guardar resultados
    output_path = 'outputs/evaluation/pipeline_a2_IMPROVED_results.json'
    print(f"💾 Guardando resultados en: {output_path}")

    results = {
        'overall_metrics': overall_metrics,
        'per_job_metrics': per_job_results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Mostrar resultados
    print()
    print("=" * 70)
    print("📊 RESULTADOS FINALES - PIPELINE A.2 MEJORADO")
    print("=" * 70)
    print()
    print(f"F1 Score:       {overall_metrics['f1']:.2f}%")
    print(f"Precision:      {overall_metrics['precision']:.2f}%")
    print(f"Recall:         {overall_metrics['recall']:.2f}%")
    print(f"Skills/job:     {overall_metrics['avg_skills_per_job']:.2f}")
    print(f"True Positives: {overall_metrics['true_positives']}")
    print(f"False Positives: {overall_metrics['false_positives']}")
    print(f"False Negatives: {overall_metrics['false_negatives']}")

    if overall_metrics['true_positives'] > 0:
        fp_tp_ratio = overall_metrics['false_positives'] / overall_metrics['true_positives']
        print(f"Ratio FP/TP:    {fp_tp_ratio:.2f}x")

    zero_f1 = sum(1 for job in per_job_results if job['f1'] == 0)
    print(f"Ofertas F1=0:   {zero_f1}/300 ({zero_f1/300*100:.1f}%)")

    print()
    print("=" * 70)
    print("COMPARACIÓN EVOLUTIVA:")
    print("=" * 70)
    print()
    print(f"{'Versión':<30} | {'F1':>7} | {'P':>7} | {'R':>7} | {'Skills/Job':>11}")
    print("-" * 70)
    print(f"{'Pipeline A (Regex)':<30} | {79.15:>6.2f}% | {86.11:>6.2f}% | {73.23:>6.2f}% | {23.4:>10.2f}")
    print(f"{'Pipeline B (LLM)':<30} | {84.26:>6.2f}% | {88.54:>6.2f}% | {82.67:>6.2f}% | {31.2:>10.2f}")
    print("-" * 70)
    print(f"{'A2.IMPROVED':<30} | {overall_metrics['f1']:>6.2f}% | {overall_metrics['precision']:>6.2f}% | {overall_metrics['recall']:>6.2f}% | {overall_metrics['avg_skills_per_job']:>10.2f}")
    print(f"{'A2.FIXED':<30} | {16.99:>6.2f}% | {66.18:>6.2f}% | {9.74:>6.2f}% | {9.03:>10.2f}")
    print(f"{'A2.2 (Tech only)':<30} | {9.73:>6.2f}% | {10.61:>6.2f}% | {8.99:>6.2f}% | {95.28:>10.2f}")
    print(f"{'A2.0 (Original)':<30} | {6.68:>6.2f}% | {5.39:>6.2f}% | {8.78:>6.2f}% | {124.57:>10.2f}")
    print()
    print("✅ ¡Evaluación completada!")
    print()


if __name__ == '__main__':
    main()
