"""
Skill Normalizer - Normalización unificada de skills para comparación justa.

Este módulo asegura que skills extraídas por diferentes pipelines se puedan
comparar de manera consistente, eliminando diferencias triviales como:
- Capitalización (Python vs python vs PYTHON)
- Variantes comunes (postgres vs PostgreSQL, js vs JavaScript)
- Espacios extras, caracteres especiales

Usado por:
- Gold Standard annotations
- Pipeline A (NER+Regex)
- Pipeline B (LLM)
"""

from typing import List, Dict, Set
import re
import logging
from unicodedata import normalize as unicode_normalize

logger = logging.getLogger(__name__)


class SkillNormalizer:
    """Normalizador de skills con diccionario canónico y reglas de limpieza."""

    # Diccionario canónico de tecnologías - nombres oficiales
    CANONICAL_NAMES = {
        # Lenguajes de programación
        'python': 'Python',
        'javascript': 'JavaScript',
        'js': 'JavaScript',
        'typescript': 'TypeScript',
        'ts': 'TypeScript',
        'java': 'Java',
        'c#': 'C#',
        'csharp': 'C#',
        'c++': 'C++',
        'cpp': 'C++',
        'c': 'C',
        'go': 'Go',
        'golang': 'Go',
        'rust': 'Rust',
        'ruby': 'Ruby',
        'php': 'PHP',
        'swift': 'Swift',
        'kotlin': 'Kotlin',
        'scala': 'Scala',
        'r': 'R',
        'matlab': 'MATLAB',
        'perl': 'Perl',
        'shell': 'Shell',
        'bash': 'Bash',
        'powershell': 'PowerShell',
        'sql': 'SQL',

        # Frontend frameworks
        'react': 'React',
        'reactjs': 'React',
        'react.js': 'React',
        'vue': 'Vue.js',
        'vuejs': 'Vue.js',
        'vue.js': 'Vue.js',
        'angular': 'Angular',
        'angularjs': 'Angular',
        'svelte': 'Svelte',
        'next': 'Next.js',
        'nextjs': 'Next.js',
        'next.js': 'Next.js',
        'nuxt': 'Nuxt.js',
        'nuxtjs': 'Nuxt.js',
        'gatsby': 'Gatsby',
        'ember': 'Ember.js',
        'backbone': 'Backbone.js',

        # Backend frameworks
        'django': 'Django',
        'flask': 'Flask',
        'fastapi': 'FastAPI',
        'express': 'Express.js',
        'expressjs': 'Express.js',
        'nestjs': 'NestJS',
        'nest': 'NestJS',
        'spring': 'Spring',
        'spring boot': 'Spring Boot',
        'springboot': 'Spring Boot',
        'rails': 'Ruby on Rails',
        'ruby on rails': 'Ruby on Rails',
        'laravel': 'Laravel',
        'symfony': 'Symfony',
        'asp.net': 'ASP.NET',
        'aspnet': 'ASP.NET',
        '.net': '.NET',
        'dotnet': '.NET',
        'node': 'Node.js',
        'nodejs': 'Node.js',
        'node.js': 'Node.js',

        # Databases
        'postgres': 'PostgreSQL',
        'postgresql': 'PostgreSQL',
        'mysql': 'MySQL',
        'mongodb': 'MongoDB',
        'mongo': 'MongoDB',
        'redis': 'Redis',
        'elasticsearch': 'Elasticsearch',
        'cassandra': 'Cassandra',
        'dynamodb': 'DynamoDB',
        'oracle': 'Oracle',
        'sql server': 'SQL Server',
        'sqlserver': 'SQL Server',
        'mariadb': 'MariaDB',
        'sqlite': 'SQLite',
        'couchdb': 'CouchDB',
        'neo4j': 'Neo4j',
        'influxdb': 'InfluxDB',
        'timescaledb': 'TimescaleDB',

        # Cloud platforms
        'aws': 'AWS',
        'amazon web services': 'AWS',
        'azure': 'Azure',
        'microsoft azure': 'Azure',
        'gcp': 'GCP',
        'google cloud': 'GCP',
        'google cloud platform': 'GCP',
        'heroku': 'Heroku',
        'digitalocean': 'DigitalOcean',
        'vercel': 'Vercel',
        'netlify': 'Netlify',
        'cloudflare': 'Cloudflare',

        # DevOps & Infrastructure
        'docker': 'Docker',
        'kubernetes': 'Kubernetes',
        'k8s': 'Kubernetes',
        'jenkins': 'Jenkins',
        'gitlab': 'GitLab',
        'github': 'GitHub',
        'bitbucket': 'Bitbucket',
        'terraform': 'Terraform',
        'ansible': 'Ansible',
        'puppet': 'Puppet',
        'chef': 'Chef',
        'vagrant': 'Vagrant',
        'circleci': 'CircleCI',
        'travis': 'Travis CI',
        'teamcity': 'TeamCity',
        'bamboo': 'Bamboo',

        # Tools & Libraries
        'git': 'Git',
        'svn': 'SVN',
        'mercurial': 'Mercurial',
        'npm': 'npm',
        'yarn': 'Yarn',
        'webpack': 'Webpack',
        'babel': 'Babel',
        'eslint': 'ESLint',
        'prettier': 'Prettier',
        'jest': 'Jest',
        'mocha': 'Mocha',
        'chai': 'Chai',
        'pytest': 'Pytest',
        'junit': 'JUnit',
        'selenium': 'Selenium',
        'cypress': 'Cypress',
        'postman': 'Postman',
        'swagger': 'Swagger',
        'graphql': 'GraphQL',
        'rest': 'REST',
        'restful': 'REST',
        'api': 'API',
        'grpc': 'gRPC',
        'soap': 'SOAP',

        # Data Science & ML
        'pandas': 'Pandas',
        'numpy': 'NumPy',
        'scipy': 'SciPy',
        'scikit-learn': 'Scikit-learn',
        'sklearn': 'Scikit-learn',
        'tensorflow': 'TensorFlow',
        'keras': 'Keras',
        'pytorch': 'PyTorch',
        'torch': 'PyTorch',
        'opencv': 'OpenCV',
        'matplotlib': 'Matplotlib',
        'seaborn': 'Seaborn',
        'tableau': 'Tableau',
        'power bi': 'Power BI',
        'powerbi': 'Power BI',
        'excel': 'Excel',
        'spark': 'Apache Spark',
        'apache spark': 'Apache Spark',
        'hadoop': 'Hadoop',
        'kafka': 'Kafka',
        'apache kafka': 'Kafka',
        'airflow': 'Apache Airflow',
        'apache airflow': 'Apache Airflow',

        # Mobile
        'react native': 'React Native',
        'flutter': 'Flutter',
        'ionic': 'Ionic',
        'xamarin': 'Xamarin',

        # Testing
        'unit testing': 'Unit Testing',
        'integration testing': 'Integration Testing',
        'e2e': 'E2E Testing',
        'tdd': 'TDD',
        'bdd': 'BDD',

        # Methodologies
        'agile': 'Agile',
        'scrum': 'Scrum',
        'kanban': 'Kanban',
        'devops': 'DevOps',
        'ci/cd': 'CI/CD',
        'cicd': 'CI/CD',
        'microservices': 'Microservices',
        'microservicios': 'Microservices',

        # Soft skills (en español e inglés)
        'liderazgo': 'Liderazgo',
        'leadership': 'Liderazgo',
        'comunicación': 'Comunicación',
        'communication': 'Comunicación',
        'trabajo en equipo': 'Trabajo en Equipo',
        'teamwork': 'Trabajo en Equipo',
        'team work': 'Trabajo en Equipo',
        'resolución de problemas': 'Resolución de Problemas',
        'problem solving': 'Resolución de Problemas',
        'pensamiento crítico': 'Pensamiento Crítico',
        'critical thinking': 'Pensamiento Crítico',
        'creatividad': 'Creatividad',
        'creativity': 'Creatividad',
        'adaptabilidad': 'Adaptabilidad',
        'adaptability': 'Adaptabilidad',
        'organización': 'Organización',
        'organization': 'Organización',
        'gestión del tiempo': 'Gestión del Tiempo',
        'time management': 'Gestión del Tiempo',
    }

    # Palabras que NO son skills (ruido común)
    BLACKLIST = {
        'experiencia', 'experience', 'años', 'years', 'año', 'year',
        'deseable', 'desired', 'plus', 'beneficio', 'benefit',
        'remoto', 'remote', 'híbrido', 'hybrid', 'presencial', 'onsite',
        'salario', 'salary', 'sueldo', 'wage',
        'horario', 'schedule', 'tiempo completo', 'full time', 'fulltime',
        'medio tiempo', 'part time', 'parttime',
        'ubicación', 'location', 'ciudad', 'city',
        'empresa', 'company', 'compañía',
        'inglés', 'english', 'español', 'spanish',
        'título', 'degree', 'universitario', 'university',
    }

    def __init__(self):
        """Inicializa el normalizador."""
        logger.info(f"SkillNormalizer initialized with {len(self.CANONICAL_NAMES)} canonical names")

    def normalize(self, skill_text: str) -> str:
        """
        Normaliza un skill text a su forma canónica.

        Args:
            skill_text: Texto del skill a normalizar

        Returns:
            Skill normalizado
        """
        if not skill_text or not isinstance(skill_text, str):
            return ""

        # 1. Limpieza básica
        normalized = skill_text.strip()

        # 2. Remover acentos (para matching)
        normalized_for_lookup = self._remove_accents(normalized).lower()

        # 3. Verificar si está en blacklist
        if normalized_for_lookup in self.BLACKLIST:
            logger.debug(f"Skill '{skill_text}' está en blacklist, se descarta")
            return ""

        # 4. Buscar en diccionario canónico
        if normalized_for_lookup in self.CANONICAL_NAMES:
            canonical = self.CANONICAL_NAMES[normalized_for_lookup]
            logger.debug(f"Normalized '{skill_text}' -> '{canonical}' (canonical)")
            return canonical

        # 5. Fallback: Title case (primera letra de cada palabra en mayúscula)
        normalized = self._clean_text(normalized)
        normalized = self._to_title_case(normalized)

        logger.debug(f"Normalized '{skill_text}' -> '{normalized}' (title case)")
        return normalized

    def normalize_list(self, skills: List[str]) -> List[str]:
        """
        Normaliza una lista de skills y elimina duplicados.

        Args:
            skills: Lista de skill texts

        Returns:
            Lista de skills normalizados únicos
        """
        normalized = []
        seen = set()

        for skill in skills:
            norm_skill = self.normalize(skill)

            # Ignorar vacíos y duplicados
            if not norm_skill:
                continue

            norm_lower = norm_skill.lower()
            if norm_lower not in seen:
                seen.add(norm_lower)
                normalized.append(norm_skill)

        logger.info(f"Normalized {len(skills)} skills -> {len(normalized)} unique")
        return normalized

    def _remove_accents(self, text: str) -> str:
        """Remueve acentos de un texto."""
        return unicode_normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')

    def _clean_text(self, text: str) -> str:
        """Limpia texto de caracteres especiales innecesarios."""
        # Remover múltiples espacios
        text = re.sub(r'\s+', ' ', text)
        # Remover caracteres especiales al inicio/final
        text = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', text)
        return text.strip()

    def _to_title_case(self, text: str) -> str:
        """
        Convierte a title case respetando acrónimos y casos especiales.

        Ejemplos:
        - "python" -> "Python"
        - "API REST" -> "API REST" (mantiene mayúsculas)
        - "machine learning" -> "Machine Learning"
        """
        # Si todo está en mayúsculas y es corto, probablemente es un acrónimo
        if text.isupper() and len(text) <= 5:
            return text

        # Si tiene mezcla de mayúsculas/minúsculas, probablemente está bien
        if any(c.isupper() for c in text) and any(c.islower() for c in text):
            return text

        # Caso default: title case
        return text.title()


# Funciones de conveniencia para uso directo

_normalizer_instance = None

def get_normalizer() -> SkillNormalizer:
    """Obtiene instancia singleton del normalizador."""
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = SkillNormalizer()
    return _normalizer_instance


def normalize_skill(skill_text: str) -> str:
    """
    Normaliza un skill text (función de conveniencia).

    Args:
        skill_text: Texto del skill

    Returns:
        Skill normalizado
    """
    return get_normalizer().normalize(skill_text)


def normalize_skills_list(skills: List[str]) -> List[str]:
    """
    Normaliza lista de skills (función de conveniencia).

    Args:
        skills: Lista de skill texts

    Returns:
        Lista de skills normalizados únicos
    """
    return get_normalizer().normalize_list(skills)


def get_canonical_name(skill_text: str) -> str:
    """
    Obtiene el nombre canónico de un skill si existe.

    Args:
        skill_text: Texto del skill

    Returns:
        Nombre canónico o el texto original
    """
    normalizer = get_normalizer()
    key = normalizer._remove_accents(skill_text.strip().lower())
    return normalizer.CANONICAL_NAMES.get(key, skill_text)
