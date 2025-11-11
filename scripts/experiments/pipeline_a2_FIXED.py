#!/usr/bin/env python3
"""
Pipeline A.2 - VERSIÓN CORREGIDA

El problema del enfoque anterior:
- Generaba n-gramas desde ESCO y los buscaba en el texto
- Matcheaba palabras sueltas ("los", "para", "empresa")

El enfoque correcto:
- Generar n-gramas desde el TEXTO de la oferta
- Buscar esos n-gramas COMPLETOS en ESCO (exact match)
- Solo devolver skills de ESCO que estén literalmente en el texto

Ejemplo:
  Texto: "Buscamos desarrollador con Python y Docker"
  N-gramas del texto: ["python", "docker", "y docker", ...]
  Match en ESCO: "Python" ✅, "Docker" ✅
  NO match: "empleo de polvo" ❌ (no está en el texto)
"""

import json
import re
import unicodedata
from typing import Dict, List, Set
from collections import defaultdict
import psycopg2


def normalize_text(text: str) -> str:
    """Normaliza texto"""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def generate_ngrams_from_text(text: str, max_n: int = 4) -> Set[str]:
    """
    Genera TODOS los n-gramas del texto (1-4 palabras).
    Retorna un SET de n-gramas únicos.
    """
    tokens = text.split()
    ngrams = set()

    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.add(ngram)

    return ngrams


def load_esco_skills_as_set(db_config: Dict, tech_only: bool = True) -> Dict[str, List[Dict]]:
    """
    Carga skills de ESCO como un diccionario {normalized_label: [skill_info]}.

    Esto permite buscar RÁPIDO si una skill específica existe en ESCO.
    """
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()

    if tech_only:
        query = """
            SELECT
                skill_id,
                preferred_label_es,
                skill_type
            FROM esco_skills
            WHERE is_active = TRUE
            AND (
                skill_type IN ('onet_hot_tech', 'tier0_critical', 'tier1_critical',
                               'tier2_important', 'onet_in_demand', 'knowledge')
                OR preferred_label_es ~* '(software|programación|código|desarrollo|datos|sistema|aplicación|tecnología|informática|web|api|base de datos|algoritmo|red|servidor|cloud|digital|framework|librería)'
            )
            ORDER BY preferred_label_es
        """
    else:
        query = """
            SELECT
                skill_id,
                preferred_label_es,
                skill_type
            FROM esco_skills
            WHERE is_active = TRUE
            ORDER BY preferred_label_es
        """

    cur.execute(query)
    rows = cur.fetchall()

    # Crear diccionario: {normalized_label: [skill_info]}
    esco_dict = defaultdict(list)

    for row in rows:
        skill_id = row[0]
        preferred_label = row[1]
        skill_type = row[2]

        normalized_label = normalize_text(preferred_label)

        esco_dict[normalized_label].append({
            'skill_id': skill_id,
            'preferred_label': preferred_label,
            'skill_type': skill_type
        })

    cur.close()
    conn.close()

    return dict(esco_dict)


def extract_skills_correct_approach(
    job_description: str,
    esco_skills_dict: Dict[str, List[Dict]],
    max_n: int = 4
) -> List[Dict]:
    """
    Enfoque CORRECTO:
    1. Generar n-gramas del TEXTO de la oferta
    2. Para cada n-grama, verificar si existe en ESCO
    3. Solo devolver matches exactos
    """
    # Normalizar texto
    normalized_text = normalize_text(job_description)

    # Generar TODOS los n-gramas del texto
    text_ngrams = generate_ngrams_from_text(normalized_text, max_n)

    print(f"N-gramas generados del texto: {len(text_ngrams)}")

    # Buscar cada n-grama en ESCO
    matches = []

    for ngram in text_ngrams:
        if ngram in esco_skills_dict:
            # ¡Match! Este n-grama es una skill de ESCO
            for skill_info in esco_skills_dict[ngram]:
                matches.append({
                    'skill_id': skill_info['skill_id'],
                    'skill_text': skill_info['preferred_label'],
                    'normalized_skill': ngram,
                    'ngram_size': len(ngram.split()),
                    'taxonomy_source': 'esco',
                    'extraction_method': 'ngram_correct',
                    'skill_type': skill_info['skill_type']
                })

    print(f"Matches encontrados: {len(matches)}")

    # Deduplicar por skill_id (pueden haber múltiples matches de la misma skill)
    seen_skill_ids = set()
    unique_matches = []

    for match in matches:
        if match['skill_id'] not in seen_skill_ids:
            seen_skill_ids.add(match['skill_id'])
            unique_matches.append(match)

    print(f"Skills únicas: {len(unique_matches)}")

    return unique_matches


# ==============================================================================
# SCRIPT DE PRUEBA
# ==============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("PIPELINE A.2 - VERSIÓN CORREGIDA")
    print("=" * 70)
    print()

    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    # Cargar ESCO como diccionario
    print("📥 Cargando skills de ESCO...")
    esco_skills_dict = load_esco_skills_as_set(DB_CONFIG, tech_only=True)
    print(f"   ✅ {len(esco_skills_dict)} skills técnicas cargadas\n")

    # Cargar un job de ejemplo
    print("📥 Cargando job de prueba...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = '''
        SELECT
            j.job_id::text,
            j.combined_text,
            ARRAY_AGG(DISTINCT g.skill_text) as gold_skills
        FROM cleaned_jobs j
        JOIN gold_standard_annotations g ON j.job_id = g.job_id
        WHERE g.skill_type = 'hard'
        GROUP BY j.job_id, j.combined_text
        LIMIT 1
    '''

    cur.execute(query)
    row = cur.fetchone()

    job_id = row[0]
    job_text = row[1]
    gold_skills = row[2]

    cur.close()
    conn.close()

    print(f"   Job ID: {job_id}")
    print(f"   Gold standard skills: {len(gold_skills)}\n")

    # Extraer skills
    print("🔍 Extrayendo skills con enfoque CORRECTO...\n")
    extracted = extract_skills_correct_approach(job_text, esco_skills_dict, max_n=4)

    print()
    print("=" * 70)
    print("RESULTADOS:")
    print("=" * 70)
    print(f"Skills extraídas: {len(extracted)}")
    print()

    print("Skills extraídas:")
    for i, skill in enumerate(extracted[:30], 1):
        print(f"  {i:2}. {skill['skill_text']} ({skill['skill_type']})")

    print()
    print("Gold standard (primeras 20):")
    for i, skill in enumerate(gold_skills[:20], 1):
        print(f"  {i:2}. {skill}")

    print()
    print("=" * 70)
