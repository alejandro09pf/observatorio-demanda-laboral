#!/usr/bin/env python3
"""
Pipeline A.2 - VERSIÓN MEJORADA

Mejoras implementadas:
1. Alias expansion: AWS, GCP, K8s, etc.
2. Fuzzy matching: Levenshtein distance ≤ 1
3. Substring matching: n-grams del texto contenidos en skills ESCO (≥3 chars)
4. Custom skills: Agregar skills comunes que no están en ESCO
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


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calcula distancia de Levenshtein entre dos strings"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# ==============================================================================
# MEJORA 1: ALIAS EXPANSION
# ==============================================================================

SKILL_ALIASES = {
    # Cloud providers
    "aws": ["Amazon Web Services", "AWS Lambda", "AWS CloudFormation", "AWS"],
    "gcp": ["Google Cloud Platform", "GCP"],
    "azure": ["Microsoft Azure", "Azure"],

    # Databases
    "sql server": ["Microsoft SQL Server"],
    "mysql": ["MySQL"],
    "postgresql": ["PostgreSQL", "Postgres"],
    "postgres": ["PostgreSQL"],
    "mongodb": ["MongoDB", "Mongo"],
    "mongo": ["MongoDB"],
    "redis": ["Redis"],
    "oracle": ["Oracle Database", "Oracle"],

    # Programming languages - short forms
    "js": ["JavaScript"],
    "ts": ["TypeScript"],
    "py": ["Python"],

    # Containers/Orchestration
    "k8s": ["Kubernetes"],
    "docker": ["Docker"],

    # Frameworks
    "react": ["React", "ReactJS"],
    "vue": ["Vue.js", "Vue"],
    "angular": ["Angular", "AngularJS"],

    # Version control
    "git": ["Git"],
    "github": ["GitHub"],
    "gitlab": ["GitLab"],

    # CI/CD
    "jenkins": ["Jenkins"],
    "circleci": ["CircleCI"],

    # Concepts (abbreviations)
    "bbdd": ["bases de datos", "base de datos"],
    "bd": ["bases de datos", "base de datos"],
    "ia": ["inteligencia artificial"],
    "ml": ["machine learning"],
    "dl": ["deep learning"],
    "api": ["API", "REST API"],
    "rest": ["REST", "REST API"],
    "sql": ["SQL"],
    "nosql": ["NoSQL"],
    "html": ["HTML"],
    "css": ["CSS"],
}


# ==============================================================================
# MEJORA 4: CUSTOM SKILLS (no están en ESCO pero son comunes)
# ==============================================================================

CUSTOM_SKILLS = [
    # Project management & tools
    "Jira", "Confluence", "Trello", "Asana", "Monday",

    # CI/CD & DevOps
    "Jenkins", "CircleCI", "Travis CI", "GitLab CI/CD", "GitHub Actions",
    "Terraform", "Ansible", "Puppet", "Chef",
    "Control-M", "Airflow", "Luigi",

    # Data tools
    "Tableau", "Power BI", "Looker", "Metabase",
    "dbt", "Airflow", "Prefect", "Dagster",

    # Testing
    "Selenium", "Cypress", "Jest", "Mocha", "Pytest", "JUnit",
    "Postman", "SoapUI",

    # Programming concepts
    "Bucles", "Loops", "Condicionales", "Recursión", "Recursion",
    "POO", "Programación orientada a objetos", "OOP",
    "Algoritmos", "Estructuras de datos",
    "Patrones de diseño", "Design patterns",

    # Database concepts
    "Optimización de queries", "Query optimization",
    "Índices", "Indexes",
    "Particionamiento", "Partitioning",
    "Cursores", "Cursors",
    "Stored procedures", "Procedimientos almacenados",
    "Triggers", "Disparadores",
    "Vistas", "Views",
    "Transacciones", "Transactions",

    # Web concepts
    "Responsive design", "Diseño responsivo",
    "SEO", "Optimización para motores de búsqueda",
    "Accesibilidad web", "Web accessibility",

    # Architecture
    "Microservicios", "Microservices",
    "Serverless",
    "Event-driven architecture", "Arquitectura orientada a eventos",
    "SOA", "Service-oriented architecture",

    # Security
    "OAuth", "JWT", "SAML",
    "Encriptación", "Encryption",
    "SSL/TLS",

    # Methodologies
    "Kanban", "Lean", "Six Sigma",
    "TDD", "BDD", "DDD",

    # Monitoring
    "Grafana", "Prometheus", "New Relic", "Datadog",
    "Splunk", "ELK Stack", "Elasticsearch",

    # Message queues
    "RabbitMQ", "Kafka", "ActiveMQ", "SQS",

    # Operating systems
    "Linux", "Unix", "Windows Server", "Ubuntu", "CentOS", "Red Hat",

    # Networking
    "TCP/IP", "HTTP/HTTPS", "DNS", "Load balancing",
    "VPN", "Firewall",
]


def generate_ngrams_from_text(text: str, max_n: int = 4) -> Set[str]:
    """Genera todos los n-gramas del texto (1-4 palabras)"""
    tokens = text.split()
    ngrams = set()

    for n in range(1, min(max_n + 1, len(tokens) + 1)):
        for i in range(len(tokens) - n + 1):
            ngram = " ".join(tokens[i:i+n])
            ngrams.add(ngram)

    return ngrams


def load_esco_skills_enhanced(db_config: Dict, tech_only: bool = True) -> Dict[str, List[Dict]]:
    """
    Carga skills de ESCO + custom skills como diccionario.
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
            SELECT skill_id, preferred_label_es, skill_type
            FROM esco_skills
            WHERE is_active = TRUE
            ORDER BY preferred_label_es
        """

    cur.execute(query)
    rows = cur.fetchall()

    esco_dict = defaultdict(list)

    # Agregar skills de ESCO
    for row in rows:
        skill_id = row[0]
        preferred_label = row[1]
        skill_type = row[2]

        normalized_label = normalize_text(preferred_label)

        esco_dict[normalized_label].append({
            'skill_id': skill_id,
            'preferred_label': preferred_label,
            'skill_type': skill_type,
            'source': 'esco'
        })

    cur.close()
    conn.close()

    # MEJORA 4: Agregar custom skills
    for custom_skill in CUSTOM_SKILLS:
        normalized = normalize_text(custom_skill)
        if normalized not in esco_dict:  # Solo agregar si no existe
            esco_dict[normalized].append({
                'skill_id': f'custom_{normalized}',
                'preferred_label': custom_skill,
                'skill_type': 'custom',
                'source': 'custom'
            })

    return dict(esco_dict)


def extract_skills_improved(
    job_description: str,
    esco_skills_dict: Dict[str, List[Dict]],
    max_n: int = 4,
    fuzzy_threshold: int = 1,
    use_substring: bool = True
) -> List[Dict]:
    """
    Extracción mejorada con:
    1. Exact matching
    2. Alias expansion
    3. Fuzzy matching (Levenshtein ≤ threshold)
    4. Substring matching (n-gram del texto contenido en skill ESCO)
    """
    normalized_text = normalize_text(job_description)
    text_ngrams = generate_ngrams_from_text(normalized_text, max_n)

    matches = []
    matched_skill_ids = set()

    # PASO 1: Exact matching
    for ngram in text_ngrams:
        if ngram in esco_skills_dict:
            for skill_info in esco_skills_dict[ngram]:
                if skill_info['skill_id'] not in matched_skill_ids:
                    matches.append({
                        'skill_id': skill_info['skill_id'],
                        'skill_text': skill_info['preferred_label'],
                        'normalized_skill': ngram,
                        'ngram_size': len(ngram.split()),
                        'match_type': 'exact',
                        'skill_type': skill_info['skill_type'],
                        'source': skill_info.get('source', 'esco')
                    })
                    matched_skill_ids.add(skill_info['skill_id'])

    # PASO 2: Alias expansion
    for ngram in text_ngrams:
        if ngram in SKILL_ALIASES:
            for alias in SKILL_ALIASES[ngram]:
                alias_norm = normalize_text(alias)
                if alias_norm in esco_skills_dict:
                    for skill_info in esco_skills_dict[alias_norm]:
                        if skill_info['skill_id'] not in matched_skill_ids:
                            matches.append({
                                'skill_id': skill_info['skill_id'],
                                'skill_text': skill_info['preferred_label'],
                                'normalized_skill': alias_norm,
                                'ngram_size': len(ngram.split()),
                                'match_type': 'alias',
                                'skill_type': skill_info['skill_type'],
                                'source': skill_info.get('source', 'esco')
                            })
                            matched_skill_ids.add(skill_info['skill_id'])

    # PASO 3: Fuzzy matching (solo n-gramas ≥3 chars y solo candidatos cercanos en longitud)
    if fuzzy_threshold > 0:
        for ngram in text_ngrams:
            if len(ngram) < 3:  # Skip very short
                continue

            # Optimización: solo comparar con skills de longitud similar (±2 chars)
            for esco_skill_norm, skill_infos in esco_skills_dict.items():
                if abs(len(ngram) - len(esco_skill_norm)) > fuzzy_threshold + 1:
                    continue  # Skip si la diferencia de longitud es demasiado grande

                if levenshtein_distance(ngram, esco_skill_norm) <= fuzzy_threshold:
                    for skill_info in skill_infos:
                        if skill_info['skill_id'] not in matched_skill_ids:
                            matches.append({
                                'skill_id': skill_info['skill_id'],
                                'skill_text': skill_info['preferred_label'],
                                'normalized_skill': esco_skill_norm,
                                'ngram_size': len(ngram.split()),
                                'match_type': 'fuzzy',
                                'skill_type': skill_info['skill_type'],
                                'source': skill_info.get('source', 'esco')
                            })
                            matched_skill_ids.add(skill_info['skill_id'])

    # PASO 4: Substring matching (n-gram del texto contenido en skill ESCO)
    # MUY ESTRICTO: solo si el n-grama es ≥70% del largo de la skill
    if use_substring:
        for ngram in text_ngrams:
            if len(ngram) < 5:  # Skip muy cortos (mínimo 5 chars)
                continue

            for esco_skill_norm, skill_infos in esco_skills_dict.items():
                # Si el n-grama del texto está CONTENIDO en la skill de ESCO
                if ngram in esco_skill_norm and ngram != esco_skill_norm:
                    # Solo match si el ngram es al menos 70% del largo de la skill
                    # Esto evita "sql" matcheando con "microsoft sql server enterprise edition"
                    if len(ngram) / len(esco_skill_norm) >= 0.7:
                        for skill_info in skill_infos:
                            if skill_info['skill_id'] not in matched_skill_ids:
                                matches.append({
                                    'skill_id': skill_info['skill_id'],
                                    'skill_text': skill_info['preferred_label'],
                                    'normalized_skill': esco_skill_norm,
                                    'ngram_size': len(ngram.split()),
                                    'match_type': 'substring',
                                    'skill_type': skill_info['skill_type'],
                                    'source': skill_info.get('source', 'esco')
                                })
                                matched_skill_ids.add(skill_info['skill_id'])

    return matches


# ==============================================================================
# SCRIPT DE PRUEBA
# ==============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("PIPELINE A.2 - VERSIÓN MEJORADA")
    print("=" * 70)
    print()

    DB_CONFIG = {
        'host': 'localhost',
        'port': 5433,
        'database': 'labor_observatory',
        'user': 'labor_user',
        'password': '123456'
    }

    print("📥 Cargando skills (ESCO + custom)...")
    esco_dict = load_esco_skills_enhanced(DB_CONFIG, tech_only=True)
    print(f"   ✅ {len(esco_dict)} skills cargadas\n")

    # Cargar job de ejemplo
    print("📥 Cargando job de prueba...")
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = '''
        SELECT j.job_id::text, j.combined_text, ARRAY_AGG(DISTINCT g.skill_text) as gold_skills
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
    print("🔍 Extrayendo skills con mejoras...\n")
    extracted = extract_skills_improved(
        job_text,
        esco_dict,
        max_n=4,
        fuzzy_threshold=1,
        use_substring=True
    )

    print("=" * 70)
    print("RESULTADOS:")
    print("=" * 70)
    print(f"Skills extraídas: {len(extracted)}")
    print()

    # Agrupar por tipo de match
    from collections import Counter
    match_types = Counter(s['match_type'] for s in extracted)

    print("Por tipo de match:")
    for match_type, count in match_types.items():
        print(f"  {match_type}: {count}")

    print()
    print("Skills extraídas (primeras 30):")
    for i, skill in enumerate(extracted[:30], 1):
        print(f"  {i:2}. {skill['skill_text']:<40} [{skill['match_type']}]")

    print()
    print("Gold standard (primeras 20):")
    for i, skill in enumerate(gold_skills[:20], 1):
        print(f"  {i:2}. {skill}")

    print()
