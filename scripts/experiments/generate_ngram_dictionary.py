#!/usr/bin/env python3
"""
Pipeline A.2 - Experimento: Generación de Diccionario de N-gramas desde ESCO

Este script genera un diccionario que mapea n-gramas (1-4 gramas) a skills de ESCO.
Permite matching exhaustivo de skills técnicas contra la taxonomía oficial.

Output: data/processed/ngram_skill_dictionary.json
"""

import json
import re
import unicodedata
from collections import defaultdict
from typing import Dict, List, Set
import psycopg2


def normalize_text(text: str) -> str:
    """
    Normaliza texto para matching robusto.

    - Lowercase
    - Elimina acentos (á → a)
    - Elimina caracteres especiales excepto espacios
    - Strip whitespace
    """
    # Lowercase
    text = text.lower()

    # Eliminar acentos (NFD decomposition)
    text = unicodedata.normalize('NFD', text)
    text = ''.join(char for char in text if unicodedata.category(char) != 'Mn')

    # Reemplazar caracteres especiales por espacios (pero mantener alphanumerics)
    text = re.sub(r'[^a-z0-9\s]', ' ', text)

    # Colapsar espacios múltiples
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def generate_ngrams(text: str, max_n: int = 4) -> List[tuple]:
    """
    Genera n-gramas de tamaño 1 a max_n desde un texto.

    Returns:
        List[(ngram_text, ngram_size)]
    """
    tokens = text.split()
    ngrams = []

    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.append((ngram, n))

    return ngrams


def load_esco_skills(db_config: Dict) -> List[Dict]:
    """
    Carga skills de ESCO desde PostgreSQL.

    Returns:
        List[{
            'skill_id': str,
            'preferred_label': str,
            'description': str,
            'skill_type': str
        }]
    """
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


def build_ngram_dictionary(skills: List[Dict], max_n: int = 4) -> Dict:
    """
    Construye diccionario {ngram: [list of skills]}.

    Estructura:
    {
        "python": [
            {
                "skill_id": "...",
                "preferred_label": "Python",
                "skill_type": "onet_in_demand",
                "ngram_size": 1,
                "source_field": "preferred_label"
            },
            {
                "skill_id": "...",
                "preferred_label": "Python (programación informática)",
                "skill_type": "knowledge",
                "ngram_size": 1,
                "source_field": "preferred_label"
            }
        ],
        "machine learning": [...],
        ...
    }
    """
    ngram_dict = defaultdict(list)

    print(f"Procesando {len(skills)} skills de ESCO...")

    for idx, skill in enumerate(skills):
        if (idx + 1) % 1000 == 0:
            print(f"  Procesadas {idx + 1}/{len(skills)} skills...")

        # Generar n-gramas desde preferred_label
        label_normalized = normalize_text(skill['preferred_label'])
        ngrams_from_label = generate_ngrams(label_normalized, max_n)

        for ngram, ngram_size in ngrams_from_label:
            # Evitar n-gramas demasiado genéricos (stopwords sueltas)
            if ngram_size == 1 and len(ngram) <= 2:
                continue

            ngram_dict[ngram].append({
                'skill_id': skill['skill_id'],
                'preferred_label': skill['preferred_label'],
                'skill_type': skill['skill_type'],
                'ngram_size': ngram_size,
                'source_field': 'preferred_label'
            })

        # OPCIONAL: También generar n-gramas desde description (más ruido pero más cobertura)
        # if skill['description']:
        #     desc_normalized = normalize_text(skill['description'])
        #     ngrams_from_desc = generate_ngrams(desc_normalized, max_n=2)  # Solo bigramas en descriptions
        #     for ngram, ngram_size in ngrams_from_desc:
        #         ngram_dict[ngram].append({...})

    print(f"\n✅ Diccionario generado con {len(ngram_dict)} n-gramas únicos")

    return dict(ngram_dict)


def analyze_dictionary_stats(ngram_dict: Dict) -> Dict:
    """
    Calcula estadísticas del diccionario generado.
    """
    stats = {
        'total_ngrams': len(ngram_dict),
        'ngram_size_distribution': defaultdict(int),
        'skills_per_ngram': {
            'mean': 0,
            'median': 0,
            'max': 0,
            'max_ngram': ''
        },
        'top_10_most_common_ngrams': []
    }

    ngram_sizes = []
    skills_counts = []

    for ngram, skills in ngram_dict.items():
        # Contar por tamaño de n-grama
        ngram_size = len(ngram.split())
        stats['ngram_size_distribution'][ngram_size] += 1
        ngram_sizes.append(ngram_size)

        # Contar skills por n-grama
        num_skills = len(skills)
        skills_counts.append(num_skills)

        if num_skills > stats['skills_per_ngram']['max']:
            stats['skills_per_ngram']['max'] = num_skills
            stats['skills_per_ngram']['max_ngram'] = ngram

    # Calcular mean y median
    if skills_counts:
        stats['skills_per_ngram']['mean'] = sum(skills_counts) / len(skills_counts)
        skills_counts_sorted = sorted(skills_counts)
        mid = len(skills_counts_sorted) // 2
        stats['skills_per_ngram']['median'] = skills_counts_sorted[mid]

    # Top 10 n-gramas más comunes
    sorted_ngrams = sorted(ngram_dict.items(), key=lambda x: len(x[1]), reverse=True)
    stats['top_10_most_common_ngrams'] = [
        {'ngram': ngram, 'num_skills': len(skills)}
        for ngram, skills in sorted_ngrams[:10]
    ]

    # Convertir defaultdict a dict regular
    stats['ngram_size_distribution'] = dict(stats['ngram_size_distribution'])

    return stats


def main():
    """
    Script principal para generar diccionario de N-gramas.
    """
    print("=" * 60)
    print("PIPELINE A.2 - GENERACIÓN DE DICCIONARIO DE N-GRAMAS")
    print("=" * 60)
    print()

    # Configuración de base de datos
    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    # Parámetros
    MAX_NGRAM_SIZE = 4  # Monogramas, bigramas, trigramas, 4-gramas
    OUTPUT_PATH = 'data/processed/ngram_skill_dictionary.json'
    STATS_PATH = 'data/processed/ngram_dictionary_stats.json'

    # 1. Cargar skills de ESCO
    print("📥 Cargando skills de ESCO desde base de datos...")
    esco_skills = load_esco_skills(DB_CONFIG)
    print(f"   Cargadas {len(esco_skills)} skills de ESCO\n")

    # 2. Generar diccionario de n-gramas
    print(f"🔧 Generando n-gramas (tamaño máximo: {MAX_NGRAM_SIZE})...")
    ngram_dict = build_ngram_dictionary(esco_skills, max_n=MAX_NGRAM_SIZE)
    print()

    # 3. Analizar estadísticas
    print("📊 Calculando estadísticas del diccionario...")
    stats = analyze_dictionary_stats(ngram_dict)
    print()

    # 4. Guardar resultados
    print(f"💾 Guardando diccionario en: {OUTPUT_PATH}")
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(ngram_dict, f, ensure_ascii=False, indent=2)

    print(f"💾 Guardando estadísticas en: {STATS_PATH}")
    with open(STATS_PATH, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    # 5. Mostrar resumen
    print("\n" + "=" * 60)
    print("📈 RESUMEN DEL DICCIONARIO GENERADO")
    print("=" * 60)
    print(f"Total de n-gramas únicos: {stats['total_ngrams']:,}")
    print(f"\nDistribución por tamaño:")
    for size in sorted(stats['ngram_size_distribution'].keys()):
        count = stats['ngram_size_distribution'][size]
        print(f"  {size}-gramas: {count:,}")

    print(f"\nSkills por n-grama:")
    print(f"  Media: {stats['skills_per_ngram']['mean']:.2f}")
    print(f"  Mediana: {stats['skills_per_ngram']['median']}")
    print(f"  Máximo: {stats['skills_per_ngram']['max']} (n-grama: '{stats['skills_per_ngram']['max_ngram']}')")

    print(f"\nTop 10 n-gramas más comunes:")
    for item in stats['top_10_most_common_ngrams']:
        print(f"  '{item['ngram']}': {item['num_skills']} skills")

    print("\n✅ Diccionario generado exitosamente\n")


if __name__ == '__main__':
    main()
