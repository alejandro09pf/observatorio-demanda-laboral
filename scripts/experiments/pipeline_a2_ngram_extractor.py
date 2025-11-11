#!/usr/bin/env python3
"""
Pipeline A.2 - N-gram Skill Extractor

Extrae skills técnicas de ofertas de trabajo mediante matching de n-gramas
contra la taxonomía ESCO completa.

Algoritmo:
1. Normaliza el texto de la oferta
2. Genera n-gramas (1-4) del texto
3. Busca matches en el diccionario ESCO
4. Prioriza n-gramas más largos (evitar overlapping)
5. Deduplica resultados
"""

import json
import re
import unicodedata
from typing import Dict, List, Set, Tuple
from collections import defaultdict


def normalize_text(text: str) -> str:
    """
    Normaliza texto para matching robusto (idéntico a generate_ngram_dictionary.py).
    """
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_ngrams_with_positions(text: str, max_n: int = 4) -> List[Tuple[str, int, int, int]]:
    """
    Genera n-gramas con información de posición.

    Returns:
        List[(ngram_text, start_token_idx, end_token_idx, ngram_size)]
    """
    tokens = text.split()
    ngrams = []

    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.append((ngram, i, i + n - 1, n))

    return ngrams


def extract_skills_ngrams(
    job_description: str,
    ngram_dict: Dict,
    max_n: int = 4,
    min_ngram_length: int = 3
) -> List[Dict]:
    """
    Extrae skills usando n-gram matching contra ESCO.

    Args:
        job_description: Texto de la oferta de trabajo
        ngram_dict: Diccionario {ngram: [skills]} generado por generate_ngram_dictionary.py
        max_n: Tamaño máximo de n-grama (default 4)
        min_ngram_length: Longitud mínima del n-grama en caracteres (default 3)

    Returns:
        List[{
            'skill_id': str,
            'skill_text': str,
            'normalized_skill': str,
            'ngram_matched': str,
            'ngram_size': int,
            'taxonomy_source': 'esco',
            'extraction_method': 'ngram',
            'skill_type': str,
            'token_position': (start, end)
        }]
    """
    # Normalizar texto
    normalized_text = normalize_text(job_description)

    # Generar n-gramas con posiciones
    ngrams_with_positions = generate_ngrams_with_positions(normalized_text, max_n)

    # Buscar matches en diccionario
    raw_matches = []

    for ngram, start_pos, end_pos, ngram_size in ngrams_with_positions:
        # Filtrar n-gramas muy cortos (reducir ruido)
        if len(ngram) < min_ngram_length:
            continue

        if ngram in ngram_dict:
            # Puede haber múltiples skills con el mismo n-grama
            for skill_entry in ngram_dict[ngram]:
                raw_matches.append({
                    'skill_id': skill_entry['skill_id'],
                    'skill_text': skill_entry['preferred_label'],
                    'normalized_skill': normalize_text(skill_entry['preferred_label']),
                    'ngram_matched': ngram,
                    'ngram_size': ngram_size,
                    'taxonomy_source': 'esco',
                    'extraction_method': 'ngram',
                    'skill_type': skill_entry.get('skill_type', 'unknown'),
                    'token_position': (start_pos, end_pos)
                })

    # Resolver overlapping: priorizar n-gramas más largos
    # Si "machine learning engineer" y "learning" matchean en la misma posición,
    # solo quedarse con "machine learning engineer"
    deduplicated_matches = resolve_overlapping(raw_matches)

    return deduplicated_matches


def resolve_overlapping(matches: List[Dict]) -> List[Dict]:
    """
    Resuelve overlapping dando prioridad a n-gramas más largos.

    Algoritmo:
    1. Ordenar por ngram_size (descendente) y luego por posición
    2. Marcar posiciones ocupadas
    3. Solo agregar match si no overlaps con posiciones ya usadas
    """
    if not matches:
        return []

    # Ordenar: primero n-gramas más largos, luego por posición
    sorted_matches = sorted(
        matches,
        key=lambda x: (-x['ngram_size'], x['token_position'][0])
    )

    occupied_positions = set()
    final_matches = []

    for match in sorted_matches:
        start, end = match['token_position']
        positions = set(range(start, end + 1))

        # Verificar si hay overlap con posiciones ya ocupadas
        if not positions.intersection(occupied_positions):
            final_matches.append(match)
            occupied_positions.update(positions)

    return final_matches


def deduplicate_skills(matches: List[Dict]) -> List[Dict]:
    """
    Deduplica skills idénticas (mismo skill_id).

    Si la misma skill aparece múltiples veces (por diferentes n-gramas),
    quedarse con la que tiene el n-grama más largo.
    """
    skill_dict = {}

    for match in matches:
        skill_id = match['skill_id']

        if skill_id not in skill_dict:
            skill_dict[skill_id] = match
        else:
            # Si ya existe, quedarse con el n-grama más largo
            if match['ngram_size'] > skill_dict[skill_id]['ngram_size']:
                skill_dict[skill_id] = match

    return list(skill_dict.values())


def extract_skills_pipeline_a2(
    job_description: str,
    ngram_dict_path: str = 'data/processed/ngram_skill_dictionary.json',
    max_n: int = 4
) -> Dict:
    """
    Pipeline A.2 completo: extrae skills y retorna metadata.

    Returns:
        {
            'skills_extracted': List[Dict],
            'metadata': {
                'total_skills': int,
                'unique_skills': int,
                'ngram_sizes_distribution': Dict[int, int],
                'avg_ngram_size': float
            }
        }
    """
    # Cargar diccionario de n-gramas
    with open(ngram_dict_path, 'r', encoding='utf-8') as f:
        ngram_dict = json.load(f)

    # Extraer skills
    raw_skills = extract_skills_ngrams(job_description, ngram_dict, max_n)

    # Deduplica skills (misma skill_id)
    unique_skills = deduplicate_skills(raw_skills)

    # Calcular metadata
    ngram_dist = defaultdict(int)
    for skill in unique_skills:
        ngram_dist[skill['ngram_size']] += 1

    avg_ngram_size = (
        sum(s['ngram_size'] for s in unique_skills) / len(unique_skills)
        if unique_skills else 0
    )

    return {
        'skills_extracted': unique_skills,
        'metadata': {
            'total_skills': len(unique_skills),
            'unique_skills': len(set(s['skill_id'] for s in unique_skills)),
            'ngram_sizes_distribution': dict(ngram_dist),
            'avg_ngram_size': round(avg_ngram_size, 2)
        }
    }


# ==============================================================================
# EJEMPLO DE USO
# ==============================================================================

if __name__ == '__main__':
    # Ejemplo de uso con texto de prueba
    sample_job = """
    Buscamos Ingeniero de Machine Learning con experiencia en Python y TensorFlow.

    Requisitos:
    - Dominio de Python, scikit-learn, pandas
    - Experiencia en Machine Learning y Deep Learning
    - Conocimientos de AWS, Docker, Kubernetes
    - SQL y bases de datos relacionales
    - Git y metodologías ágiles

    Deseable:
    - Apache Spark
    - MLOps y CI/CD
    - Inglés avanzado
    """

    print("=" * 70)
    print("PIPELINE A.2 - N-GRAM SKILL EXTRACTOR - EJEMPLO")
    print("=" * 70)
    print("\n📄 Texto de prueba:")
    print(sample_job)
    print("\n" + "-" * 70)

    try:
        result = extract_skills_pipeline_a2(sample_job)

        print(f"\n✅ Skills extraídas: {result['metadata']['total_skills']}")
        print(f"   Skills únicas: {result['metadata']['unique_skills']}")
        print(f"   Tamaño promedio de n-grama: {result['metadata']['avg_ngram_size']}")

        print(f"\n📊 Distribución por tamaño de n-grama:")
        for size, count in sorted(result['metadata']['ngram_sizes_distribution'].items()):
            print(f"   {size}-gramas: {count}")

        print(f"\n🔍 Primeras 10 skills extraídas:")
        for i, skill in enumerate(result['skills_extracted'][:10], 1):
            print(f"   {i}. {skill['skill_text']} (matched: '{skill['ngram_matched']}', n={skill['ngram_size']})")

    except FileNotFoundError:
        print("\n❌ Error: Diccionario de n-gramas no encontrado.")
        print("   Ejecuta primero: python scripts/experiments/generate_ngram_dictionary.py")
