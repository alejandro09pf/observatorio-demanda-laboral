#!/usr/bin/env python3
"""
Pipeline A.2 - Versiones Filtradas

Genera 3 versiones mejoradas del diccionario de N-gramas:
- A2.1: Solo n-gramas largos (≥3 tokens) + frecuencia baja (≤10 skills)
- A2.2: Solo skills tech-related (276 tech puras + 634 potencialmente tech)
- A2.3: Eliminar n-gramas genéricos (aparecen en >50 skills)
"""

import json
import re
import unicodedata
from collections import defaultdict
from typing import Dict, List, Set
import psycopg2


def normalize_text(text: str) -> str:
    """Normaliza texto (idéntico a generate_ngram_dictionary.py)"""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_ngrams(text: str, max_n: int = 4) -> List[tuple]:
    """Genera n-gramas de tamaño 1 a max_n"""
    tokens = text.split()
    ngrams = []
    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.append((ngram, n))
    return ngrams


def load_all_esco_skills(db_config: Dict) -> List[Dict]:
    """Carga TODAS las skills de ESCO"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    query = """
        SELECT
            skill_id,
            preferred_label_es,
            description_es,
            skill_type
        FROM esco_skills
        WHERE is_active = TRUE
        ORDER BY preferred_label_es
    """

    cur.execute(query)
    rows = cur.fetchall()

    skills = []
    for row in rows:
        skills.append({
            'skill_id': row[0],
            'preferred_label': row[1],
            'description': row[2] or '',
            'skill_type': row[3] or 'unknown'
        })

    cur.close()
    conn.close()

    return skills


def load_tech_only_skills(db_config: Dict) -> List[Dict]:
    """Carga solo skills técnicas + potencialmente técnicas"""
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    # Tech puras + skills genéricas que mencionan tech keywords
    query = """
        SELECT
            skill_id,
            preferred_label_es,
            description_es,
            skill_type
        FROM esco_skills
        WHERE is_active = TRUE
        AND (
            skill_type IN ('onet_hot_tech', 'tier0_critical', 'tier1_critical', 'tier2_important', 'onet_in_demand', 'knowledge')
            OR preferred_label_es ~* '(software|programación|código|desarrollo|datos|sistema|aplicación|tecnología|informática|web|api|base de datos|algoritmo|red|servidor|cloud|digital)'
        )
        ORDER BY preferred_label_es
    """

    cur.execute(query)
    rows = cur.fetchall()

    skills = []
    for row in rows:
        skills.append({
            'skill_id': row[0],
            'preferred_label': row[1],
            'description': row[2] or '',
            'skill_type': row[3] or 'unknown'
        })

    cur.close()
    conn.close()

    return skills


def build_ngram_dict_v21(skills: List[Dict]) -> Dict:
    """
    Versión A2.1: N-gramas largos + baja frecuencia
    - Solo n-gramas ≥ 3 tokens
    - Solo n-gramas que aparecen en ≤ 10 skills
    """
    print("Generando diccionario A2.1 (n-gramas largos + baja frecuencia)...")

    # Primero generar diccionario completo
    ngram_dict_raw = defaultdict(list)

    for idx, skill in enumerate(skills):
        if (idx + 1) % 1000 == 0:
            print(f"  Procesadas {idx + 1}/{len(skills)} skills...")

        label_normalized = normalize_text(skill['preferred_label'])
        ngrams = generate_ngrams(label_normalized, max_n=4)

        for ngram, ngram_size in ngrams:
            ngram_dict_raw[ngram].append({
                'skill_id': skill['skill_id'],
                'preferred_label': skill['preferred_label'],
                'skill_type': skill['skill_type'],
                'ngram_size': ngram_size,
                'source_field': 'preferred_label'
            })

    # Filtrar: solo ≥3 tokens y ≤10 skills
    ngram_dict_filtered = {}

    for ngram, skills_list in ngram_dict_raw.items():
        ngram_size = len(ngram.split())
        num_skills = len(skills_list)

        if ngram_size >= 3 and num_skills <= 10:
            ngram_dict_filtered[ngram] = skills_list

    print(f"  ✅ Filtrado: {len(ngram_dict_raw):,} → {len(ngram_dict_filtered):,} n-gramas")

    return ngram_dict_filtered


def build_ngram_dict_v22(skills: List[Dict]) -> Dict:
    """
    Versión A2.2: Solo skills tech-related
    - Usa load_tech_only_skills()
    - Todas las n-gramas (1-4)
    """
    print("Generando diccionario A2.2 (solo skills tech)...")

    ngram_dict = defaultdict(list)

    for idx, skill in enumerate(skills):
        if (idx + 1) % 500 == 0:
            print(f"  Procesadas {idx + 1}/{len(skills)} skills...")

        label_normalized = normalize_text(skill['preferred_label'])
        ngrams = generate_ngrams(label_normalized, max_n=4)

        for ngram, ngram_size in ngrams:
            if len(ngram) < 3:  # Filtrar n-gramas muy cortos
                continue

            ngram_dict[ngram].append({
                'skill_id': skill['skill_id'],
                'preferred_label': skill['preferred_label'],
                'skill_type': skill['skill_type'],
                'ngram_size': ngram_size,
                'source_field': 'preferred_label'
            })

    print(f"  ✅ Generado: {len(ngram_dict):,} n-gramas")

    return dict(ngram_dict)


def build_ngram_dict_v23(skills: List[Dict]) -> Dict:
    """
    Versión A2.3: Eliminar n-gramas genéricos
    - Todas las skills
    - Eliminar n-gramas que aparecen en >50 skills
    """
    print("Generando diccionario A2.3 (sin n-gramas genéricos)...")

    # Primero generar diccionario completo
    ngram_dict_raw = defaultdict(list)

    for idx, skill in enumerate(skills):
        if (idx + 1) % 1000 == 0:
            print(f"  Procesadas {idx + 1}/{len(skills)} skills...")

        label_normalized = normalize_text(skill['preferred_label'])
        ngrams = generate_ngrams(label_normalized, max_n=4)

        for ngram, ngram_size in ngrams:
            if len(ngram) < 3:  # Filtrar muy cortos
                continue

            ngram_dict_raw[ngram].append({
                'skill_id': skill['skill_id'],
                'preferred_label': skill['preferred_label'],
                'skill_type': skill['skill_type'],
                'ngram_size': ngram_size,
                'source_field': 'preferred_label'
            })

    # Filtrar: eliminar n-gramas que aparecen en >50 skills
    ngram_dict_filtered = {}

    for ngram, skills_list in ngram_dict_raw.items():
        if len(skills_list) <= 50:
            ngram_dict_filtered[ngram] = skills_list

    print(f"  ✅ Filtrado: {len(ngram_dict_raw):,} → {len(ngram_dict_filtered):,} n-gramas")

    return ngram_dict_filtered


def main():
    print("=" * 70)
    print("PIPELINE A.2 - GENERACIÓN DE DICCIONARIOS FILTRADOS")
    print("=" * 70)
    print()

    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    # ========================================================================
    # Versión A2.1: N-gramas largos + baja frecuencia
    # ========================================================================
    print("📋 VERSIÓN A2.1: N-gramas largos (≥3 tokens) + baja frecuencia (≤10)")
    print()

    all_skills = load_all_esco_skills(DB_CONFIG)
    print(f"Cargadas {len(all_skills)} skills de ESCO\n")

    dict_v21 = build_ngram_dict_v21(all_skills)

    with open('data/processed/ngram_dict_v21.json', 'w', encoding='utf-8') as f:
        json.dump(dict_v21, f, ensure_ascii=False, indent=2)

    print(f"💾 Guardado: data/processed/ngram_dict_v21.json")
    print()
    print("-" * 70)
    print()

    # ========================================================================
    # Versión A2.2: Solo skills tech
    # ========================================================================
    print("📋 VERSIÓN A2.2: Solo skills tech-related")
    print()

    tech_skills = load_tech_only_skills(DB_CONFIG)
    print(f"Cargadas {len(tech_skills)} skills técnicas\n")

    dict_v22 = build_ngram_dict_v22(tech_skills)

    with open('data/processed/ngram_dict_v22.json', 'w', encoding='utf-8') as f:
        json.dump(dict_v22, f, ensure_ascii=False, indent=2)

    print(f"💾 Guardado: data/processed/ngram_dict_v22.json")
    print()
    print("-" * 70)
    print()

    # ========================================================================
    # Versión A2.3: Sin n-gramas genéricos
    # ========================================================================
    print("📋 VERSIÓN A2.3: Sin n-gramas genéricos (≤50 skills)")
    print()

    dict_v23 = build_ngram_dict_v23(all_skills)

    with open('data/processed/ngram_dict_v23.json', 'w', encoding='utf-8') as f:
        json.dump(dict_v23, f, ensure_ascii=False, indent=2)

    print(f"💾 Guardado: data/processed/ngram_dict_v23.json")
    print()

    # ========================================================================
    # Resumen comparativo
    # ========================================================================
    print("=" * 70)
    print("📊 RESUMEN COMPARATIVO")
    print("=" * 70)
    print(f"A2.0 (Original):     85,039 n-gramas")
    print(f"A2.1 (Largos+Freq):  {len(dict_v21):,} n-gramas ({len(dict_v21)/85039*100:.1f}%)")
    print(f"A2.2 (Tech only):    {len(dict_v22):,} n-gramas ({len(dict_v22)/85039*100:.1f}%)")
    print(f"A2.3 (Sin genéricos):{len(dict_v23):,} n-gramas ({len(dict_v23)/85039*100:.1f}%)")
    print()
    print("✅ Diccionarios generados exitosamente")
    print()


if __name__ == '__main__':
    main()
