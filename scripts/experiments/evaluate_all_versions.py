#!/usr/bin/env python3
"""
Pipeline A.2 - Evaluación de Todas las Versiones

Evalúa las 4 versiones contra gold standard:
- A2.0: Original (85,039 n-gramas)
- A2.1: Largos + baja frecuencia (55,589 n-gramas)
- A2.2: Solo tech skills (24,134 n-gramas)
- A2.3: Sin genéricos (84,792 n-gramas)
"""

import json
import sys
import psycopg2
from typing import Dict, List, Set
from datetime import datetime

sys.path.insert(0, '/Users/nicocamacho/Documents/Tesis/observatorio-demanda-laboral')
from scripts.experiments.pipeline_a2_ngram_extractor import extract_skills_ngrams, normalize_text, deduplicate_skills


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

    from collections import defaultdict
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
    """Carga descripciones de ofertas"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    placeholders = ','.join(['%s'] * len(job_ids))
    query = f"""
        SELECT
            job_id::text,
            combined_text
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


def evaluate_version(
    version_name: str,
    ngram_dict_path: str,
    job_descriptions: Dict[str, str],
    gold_standard: Dict[str, Set[str]]
) -> Dict:
    """Evalúa una versión específica del pipeline"""

    print(f"\n🚀 Evaluando {version_name}...")
    print(f"   Diccionario: {ngram_dict_path}")

    # Cargar diccionario
    with open(ngram_dict_path, 'r', encoding='utf-8') as f:
        ngram_dict = json.load(f)

    print(f"   N-gramas: {len(ngram_dict):,}")

    per_job_results = []
    all_predicted = set()
    all_gold = set()

    for idx, (job_id, job_description) in enumerate(job_descriptions.items(), 1):
        if idx % 50 == 0:
            print(f"   Procesadas {idx}/{len(job_descriptions)} ofertas...")

        # Extraer skills
        raw_skills = extract_skills_ngrams(job_description, ngram_dict, max_n=4)
        unique_skills = deduplicate_skills(raw_skills)
        predicted_skills = {normalize_text(s['skill_text']) for s in unique_skills}

        # Gold standard
        gold_skills = gold_standard.get(job_id, set())

        # Métricas por oferta
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

    # Métricas globales
    overall_metrics = calculate_metrics(all_predicted, all_gold)
    overall_metrics['avg_skills_per_job'] = round(
        sum(r['predicted_count'] for r in per_job_results) / len(per_job_results), 2
    )
    overall_metrics['total_jobs'] = len(per_job_results)

    print(f"   ✅ F1: {overall_metrics['f1']:.2f}% | P: {overall_metrics['precision']:.2f}% | R: {overall_metrics['recall']:.2f}%")

    return {
        'version': version_name,
        'overall_metrics': overall_metrics,
        'per_job_metrics': per_job_results
    }


def main():
    print("=" * 70)
    print("PIPELINE A.2 - EVALUACIÓN DE TODAS LAS VERSIONES")
    print("=" * 70)

    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    # Cargar gold standard
    print("\n📥 Cargando gold standard...")
    gold_standard = load_gold_standard(DB_CONFIG)
    print(f"   ✅ {len(gold_standard)} ofertas cargadas")

    # Cargar descripciones
    print("\n📥 Cargando descripciones...")
    job_ids = list(gold_standard.keys())
    job_descriptions = load_job_descriptions(DB_CONFIG, job_ids)
    print(f"   ✅ {len(job_descriptions)} descripciones cargadas")

    # Evaluar las 4 versiones
    versions = [
        ('A2.0 (Original)', 'data/processed/ngram_skill_dictionary.json'),
        ('A2.1 (Largos+Freq)', 'data/processed/ngram_dict_v21.json'),
        ('A2.2 (Tech only)', 'data/processed/ngram_dict_v22.json'),
        ('A2.3 (Sin genéricos)', 'data/processed/ngram_dict_v23.json'),
    ]

    results = {}

    for version_name, dict_path in versions:
        try:
            result = evaluate_version(version_name, dict_path, job_descriptions, gold_standard)
            results[version_name] = result
        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    # Guardar resultados
    output_path = 'outputs/evaluation/pipeline_a2_all_versions_results.json'
    print(f"\n💾 Guardando resultados en: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Mostrar tabla comparativa
    print("\n" + "=" * 70)
    print("📊 RESULTADOS COMPARATIVOS")
    print("=" * 70)
    print()
    print(f"{'Versión':<25} | {'F1':>7} | {'Precision':>9} | {'Recall':>7} | {'Skills/Job':>11}")
    print("-" * 70)

    # Ordenar por F1
    sorted_results = sorted(
        results.items(),
        key=lambda x: x[1]['overall_metrics']['f1'],
        reverse=True
    )

    for version_name, result in sorted_results:
        metrics = result['overall_metrics']
        print(f"{version_name:<25} | {metrics['f1']:>6.2f}% | {metrics['precision']:>8.2f}% | {metrics['recall']:>6.2f}% | {metrics['avg_skills_per_job']:>10.2f}")

    print()
    print("✅ Evaluación completada")
    print()


if __name__ == '__main__':
    main()
