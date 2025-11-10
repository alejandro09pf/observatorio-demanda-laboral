"""
ESCO Matcher Enhanced - Experimental Version with 4 Layers

Layer 1: Exact Match (SQL) → Confidence 1.00
Layer 2: Fuzzy Match (fuzzywuzzy, threshold 0.92) → Confidence 0.92-1.00
Layer 3: Substring/Contains Match (NEW) → Confidence 0.85-0.95
Layer 4: Manual Dictionary for High-Frequency Tech Terms (NEW) → Confidence 0.90

This is an EXPERIMENTAL version - does NOT modify production pipeline.
Use for testing and comparison only.
"""

import psycopg2
from typing import List, Dict, Any, Optional, Tuple
import logging
from fuzzywuzzy import fuzz
from dataclasses import dataclass

from config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class ESCOMatch:
    """Represents an ESCO skill match with detailed matching info."""
    skill_text: str
    matched_skill_text: str
    esco_skill_uri: str
    confidence_score: float
    match_method: str  # 'exact', 'fuzzy', 'substring', 'manual_dict'
    esco_skill_name: str
    skill_type: str
    skill_group: str


class ESCOMatcherEnhanced:
    """Enhanced ESCO matcher with substring and manual dictionary layers."""

    # Thresholds
    FUZZY_THRESHOLD = 0.86  # Lowered from 0.92 to catch more valid matches
    FUZZY_THRESHOLD_SHORT = 0.92  # Lowered from 0.95
    SUBSTRING_CONFIDENCE = 0.85  # Lower confidence for substring matches

    # Blacklisted ESCO labels that cause false positives for IT/tech skills
    # These are valid ESCO skills but in wrong domains (agriculture, food, construction, art, etc.)
    BLACKLISTED_LABELS = {
        'almacenar peces', 'almacenar escamas de jabón', 'cantar', 'clasificación del pescado',
        'organizar la depuración de moluscos', 'técnicas de autenticación de alimentos',
        'limpiar contenedores industriales', 'instalar conectores de bombas para andamios',
        'colecciones de arte', 'procurar la accesibilidad de la infraestructura',
        'aplicaciones de cadena de bloques', 'aplicaciones del barniz',
        'bases de datos de museos', 'crear bases de datos de terminología',
        'someter a auditorías a los contratistas', 'realizar auditorías energéticas de instalaciones',
        'colaboración entre personas y robots', 'consultoría de gestión',
        'componentes de la cadena de bloques', 'química analítica', 'pensar de forma analítica',
        'buenas prácticas de fabricación', 'palabras clave en contenidos digitales',
        'formar a los trabajadores sobre el proceso de control de calidad',
        'mejores prácticas de sistemas de copias de seguridad',
        'instalar software antivirus',
        'prestar un servicio de atención al cliente de primera calidad',
        # NEW: False matches with high fuzzy scores but wrong semantics
        'análisis de datos',  # Prevent "Análisis de defectos" → "análisis de datos"
        'contabilidad',  # Prevent "Confiabilidad" → "contabilidad"
        'cartografía',  # Prevent "Criptografía" → "cartografía"
        'control de gastos',  # Prevent "Control de accesos" → "control de gastos"
        'desarrollo iterativo',  # Prevent "Desarrollo nativo" → "desarrollo iterativo"
        'estimación de estado',  # Prevent "Gestión de estado" → "estimación de estado"
        'tomar decisiones clínicas',  # Prevent "Toma de decisiones técnicas" → "tomar decisiones clínicas"
        # V3 False positives from substring matching
        'almacenar materias primas alimenticias',  # Prevent "ALM" → food storage
        'utilizar una interfaz para aplicaciones específicas',  # Prevent "Aplicaciones" → generic interface use
        'amenazas de seguridad de aplicaciones web',  # Prevent "Aplicaciones web" → threats (too specific)
        'comunicarse con el departamento de atención al cliente',  # Prevent "Atención al cliente" → communication task
        'cuidar el detalle en la preparación de las auditorías',  # Prevent "Auditorías" → audit preparation task
        'clasificación e identificación de peces',  # Prevent "Clasificación" → fish classification
    }

    # Manual dictionary for high-frequency tech terms that don't exact/fuzzy match
    # Maps: extracted_skill → (esco_label, confidence)
    MANUAL_TECH_DICT = {
        # Programming languages
        'Java': ('Java (programación informática)', 0.95),
        'JAVA': ('Java (programación informática)', 0.95),

        # Cloud platforms
        'AWS': ('Amazon Web Services', 0.90),
        'GCP': ('Google Cloud Platform', 0.90),
        'Azure': ('Microsoft Azure', 0.95),
        'AKS': ('Azure Kubernetes Service', 0.90),
        'EKS': ('Amazon Elastic Kubernetes Service', 0.90),
        'GKE': ('Google Kubernetes Engine', 0.90),

        # Development approaches
        'Backend': ('Backend Development', 0.90),
        'Frontend': ('Frontend Development', 0.90),
        'Fullstack': ('Full-Stack Development', 0.85),
        'Full Stack': ('Full-Stack Development', 0.85),

        # CI/CD & DevOps
        'CI/CD': ('continuous integration', 0.85),
        'DevOps': ('DevOps', 0.95),
        'Continuous Deployment': ('Continuous Deployment', 0.95),
        'Deployment': ('software deployment', 0.80),

        # Testing
        'Testing': ('software testing', 0.85),
        'Testing automatizado': ('automated testing', 0.90),
        'Pruebas unitarias': ('unit testing', 0.90),
        'A/B testing': ('A/B testing', 0.95),

        # Methodologies
        'Agile': ('Agile', 0.95),
        'Scrum': ('Scrum', 0.95),
        'Lean': ('lean manufacturing', 0.80),
        'Kanban': ('Kanban', 0.95),

        # Architecture
        'Microservicios': ('Microservices', 0.90),
        'API REST': ('REST API', 0.85),
        'API': ('application programming interface API', 0.80),
        'Arquitectura de software': ('software architecture', 0.90),

        # Web technologies
        'HTML': ('Hypertext markup language HTML', 0.95),
        'HTML5': ('HTML5', 0.95),
        'CSS': ('Cascading Style Sheets CSS', 0.95),
        'CSS3': ('CSS3', 0.95),

        # Databases
        'Oracle': ('Oracle Database', 0.90),
        'Bases de datos relacionales': ('relational database management system', 0.85),
        'Administración de bases de datos': ('database management', 0.85),
        'Bases de datos': ('database management', 0.80),

        # General tech concepts
        'Cloud': ('cloud technologies', 0.80),
        'Seguridad': ('IT security', 0.75),
        'Automatización': ('automation', 0.75),

        # AI/ML (NEW - High frequency)
        'AI': ('artificial intelligence', 0.90),
        'Machine Learning': ('machine learning', 0.95),
        'ML': ('machine learning', 0.90),
        'Deep Learning': ('deep learning', 0.95),
        'NLP': ('natural language processing', 0.90),
        'Computer Vision': ('computer vision', 0.95),
        'AI training': ('machine learning', 0.80),

        # Data Analysis (NEW)
        'Análisis de datos': ('data analysis', 0.90),
        'Análisis exploratorio de datos': ('exploratory data analysis', 0.90),
        'Análisis predictivo': ('predictive analytics', 0.90),
        'Analítica predictiva': ('predictive analytics', 0.90),
        'Análisis de código': ('code analysis', 0.85),
        'Análisis de requisitos': ('requirements analysis', 0.85),
        'Análisis de requerimientos': ('requirements analysis', 0.85),

        # System Administration (NEW)
        'Administración de sistemas': ('system administration', 0.90),
        'Administración de sistemas operativos': ('operating system administration', 0.90),
        'Administración de contenedores': ('container management', 0.85),
        'Actualización de sistemas': ('system updates', 0.80),

        # Security (NEW)
        'Seguridad informática': ('IT security', 0.90),
        'Ciberseguridad': ('cybersecurity', 0.95),
        'Access management': ('access management', 0.90),
        'Autenticación': ('authentication', 0.85),

        # Development Concepts (NEW)
        'Desarrollo web': ('web development', 0.90),
        'Desarrollo móvil': ('mobile development', 0.90),
        'Desarrollo de software': ('software development', 0.90),
        'Desarrollo ágil': ('agile development', 0.90),
        'Adaptive design': ('responsive design', 0.80),

        # Data Engineering (NEW)
        'Carga de datos': ('data loading', 0.85),
        'ETL': ('extract transform load', 0.95),
        'Data pipeline': ('data pipeline', 0.90),
        'Data warehousing': ('data warehousing', 0.90),

        # Quality & Performance (NEW)
        'Control de calidad': ('quality control', 0.85),
        'Calidad de datos': ('data quality', 0.90),
        'Análisis de rendimiento': ('performance analysis', 0.85),
        'Alta disponibilidad': ('high availability', 0.85),
        'Alto rendimiento': ('high performance', 0.85),

        # Collaboration (NEW)
        'Trabajo en equipo': ('teamwork', 0.85),
        'Colaboración': ('collaboration', 0.80),
        'Comunicación': ('communication skills', 0.80),

        # Business Concepts (NEW)
        'Consultoría': ('consulting', 0.80),
        'Atención al cliente': ('customer service', 0.85),
        'Gestión de proyectos': ('project management', 0.90),

        # Specific Tools/Platforms (NEW)
        'Node': ('Node.js', 0.95),
        'Node.js': ('Node.js', 0.95),
        'Next.js': ('Next.js', 0.95),
        'Vue': ('Vue.js', 0.95),
        'Svelte': ('Svelte', 0.95),

        # VERSION NORMALIZATIONS (map versioned skills to base skill)
        'Angular 2': ('Angular', 0.95),
        'AngularJS': ('Angular', 0.95),
        'CSS3': ('Cascading Style Sheets CSS', 0.95),
        'SCSS': ('Cascading Style Sheets CSS', 0.90),
        '.NET Core': ('ASP.NET Core', 0.90),
        'ASP.NET Core MVC': ('ASP.NET Core', 0.95),
        'Entity Framework Core': ('Entity Framework', 0.95),
        'C++11': ('C++', 0.95),
        'ES6': ('ECMAScript', 0.90),
        'React Native Testing Library': ('React Testing Library', 0.90),
        'Material UI': ('Material-UI', 0.95),
        'Microsoft Dynamics CRM': ('Microsoft Dynamics', 0.95),
        'Microsoft 365': ('Microsoft Office', 0.85),
        'Ionic 2': ('Ionic', 0.95),

        # EASY WINS - Common tech concepts with Spanish/English variations
        'Containerización': ('Containerization', 0.95),
        'Procesamiento de lenguaje natural': ('procesamiento del lenguaje natural', 0.95),
        'Procesamiento de Lenguaje Natural': ('procesamiento del lenguaje natural', 0.95),
        'Ciclo de vida de desarrollo de software': ('ciclo de vida del desarrollo de sistemas', 0.90),
        'Ciclo de vida del desarrollo de software': ('ciclo de vida del desarrollo de sistemas', 0.90),
        'Detección de fraude': ('detección del fraude', 0.95),
        'Infraestructura de TI': ('infraestructura de las TIC', 0.95),
        'Gestión de proyectos técnicos': ('gestión de proyectos de TIC', 0.90),
        'Implementación de aplicaciones': ('implementación de soluciones', 0.85),
        'Modelado de datos': ('modelos de datos', 0.95),
        'Reconocimiento de imágenes': ('reconocimiento de imagen', 0.95),
        'Responsive web design': ('Responsive Design', 0.95),
        'Responsive Design': ('Responsive Design', 0.95),
        'Shell scripting': ('Shell script', 0.95),
        'Shell script': ('Shell script', 0.95),
        'Texturizado 3D': ('texturizado en 3D', 0.95),

        # Data concepts
        'Data lakehouse': ('Data Warehouse', 0.85),
        'Data Lakehouse': ('Data Warehouse', 0.85),
        'Data warehousing': ('Data Warehouse', 0.90),
        'Object storage': ('ObjectStore', 0.90),
        'Restauración de datos': ('extracción de datos', 0.80),

        # SQL variants
        'ESQL': ('SQL', 0.95),
        'SOQL': ('SQL', 0.90),

        # SaaS (not SAS statistical software)
        'SaaS': ('Software as a Service', 0.95),

        # Event-driven
        'Event-driven development': ('Test-Driven Development', 0.75),

        # OAuth2
        'OAuth2': ('OAuth 2.0', 0.95),
        'OAuth 2': ('OAuth 2.0', 0.95),

        # Cryptography
        'Criptografía': ('cryptography', 0.95),

        # Access control
        'Control de accesos': ('access control', 0.95),

        # State management
        'Gestión de estado': ('state management', 0.90),

        # Defect analysis
        'Análisis de defectos': ('defect analysis', 0.90),

        # Native development
        'Desarrollo nativo': ('native development', 0.90),

        # Reliability
        'Confiabilidad': ('reliability', 0.90),

        # Technical decision making
        'Toma de decisiones técnicas': ('technical decision making', 0.85),
    }

    def __init__(self):
        self.settings = get_settings()
        self.db_url = self.settings.database_url
        if self.db_url.startswith('postgresql://'):
            self.db_url = self.db_url.replace('postgresql://', 'postgres://')

        logger.info("✅ ESCOMatcherEnhanced initialized (EXPERIMENTAL)")

    def match_skill(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Match a single skill using 4-layer strategy.

        Layer order:
        1. Exact match (highest confidence)
        2. Manual dictionary (curated mappings)
        3. Fuzzy match
        4. Substring match (lowest confidence)
        """
        if not skill_text or len(skill_text.strip()) < 2:
            return None

        skill_text = skill_text.strip()

        # Layer 1: Exact Match
        match = self._layer1_exact_match(skill_text)
        if match:
            return match

        # Layer 2: Manual Dictionary (before fuzzy to ensure correct tech term mappings)
        match = self._layer2_manual_dict(skill_text)
        if match:
            return match

        # Layer 3: Fuzzy Match
        match = self._layer3_fuzzy_match(skill_text)
        if match:
            return match

        # Layer 4: Substring Match (NEW - more permissive)
        match = self._layer4_substring_match(skill_text)
        if match:
            return match

        # All layers failed → emergent skill
        return None

    def batch_match_skills(self, skill_texts: List[str]) -> Dict[str, Optional[ESCOMatch]]:
        """Match multiple skills in batch."""
        results = {}
        for skill_text in skill_texts:
            match = self.match_skill(skill_text)
            results[skill_text] = match
        return results

    def _layer1_exact_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """Layer 1: Exact match using SQL."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                cursor.execute("""
                    SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                    FROM esco_skills
                    WHERE is_active = TRUE
                      AND (LOWER(preferred_label_es) = LOWER(%s)
                           OR LOWER(preferred_label_en) = LOWER(%s))
                    LIMIT 1
                """, (skill_text, skill_text))

                result = cursor.fetchone()

                if result:
                    uri, label_es, label_en, skill_type, skill_group = result
                    matched_label = label_es if label_es else label_en

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=1.00,
                        match_method='exact',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 1 error for '{skill_text}': {e}")

        return None

    def _layer2_manual_dict(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Layer 2: Manual dictionary lookup for high-frequency tech terms.
        Provides curated mappings for terms that don't exact match.
        """
        # Check if skill is in manual dictionary
        if skill_text not in self.MANUAL_TECH_DICT:
            return None

        target_label, confidence = self.MANUAL_TECH_DICT[skill_text]

        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Search for the target ESCO label
                cursor.execute("""
                    SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                    FROM esco_skills
                    WHERE is_active = TRUE
                      AND (LOWER(preferred_label_es) LIKE LOWER(%s)
                           OR LOWER(preferred_label_en) LIKE LOWER(%s))
                    LIMIT 1
                """, (f'%{target_label}%', f'%{target_label}%'))

                result = cursor.fetchone()

                if result:
                    uri, label_es, label_en, skill_type, skill_group = result
                    matched_label = label_es if label_es else label_en

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=confidence,
                        match_method='manual_dict',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 2 (manual dict) error for '{skill_text}': {e}")

        return None

    def _layer3_fuzzy_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """Layer 3: Fuzzy matching (same as original matcher)."""
        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Get candidates
                words = [w.strip() for w in skill_text.lower().split() if len(w.strip()) >= 2]

                if words:
                    like_conditions = []
                    params = []
                    for word in words:
                        like_conditions.append("(LOWER(preferred_label_es) LIKE %s OR LOWER(preferred_label_en) LIKE %s)")
                        params.extend([f'%{word}%', f'%{word}%'])

                    where_clause = " OR ".join(like_conditions)

                    cursor.execute(f"""
                        SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                        FROM esco_skills
                        WHERE is_active = TRUE
                          AND ({where_clause})
                        LIMIT 1000
                    """, params)

                    candidates = cursor.fetchall()

                    if not candidates:
                        cursor.execute("""
                            SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                            FROM esco_skills
                            WHERE is_active = TRUE
                        """)
                        candidates = cursor.fetchall()
                else:
                    cursor.execute("""
                        SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                        FROM esco_skills
                        WHERE is_active = TRUE
                    """)
                    candidates = cursor.fetchall()

                best_match = None
                best_score = 0.0
                best_match_starts_with = False

                for uri, label_es, label_en, skill_type, skill_group in candidates:
                    # Try Spanish
                    if label_es:
                        score_ratio = fuzz.ratio(skill_text.lower(), label_es.lower()) / 100.0
                        score_partial = fuzz.partial_ratio(skill_text.lower(), label_es.lower()) / 100.0

                        if len(skill_text) <= 4:
                            score = score_ratio
                        elif len(label_es) > len(skill_text) and len(skill_text) <= 6:
                            score = max(score_ratio, score_partial)
                        else:
                            score = score_ratio

                        starts_with = label_es.lower().startswith(skill_text.lower())
                        if score > best_score or (score == best_score and starts_with and not best_match_starts_with):
                            best_score = score
                            best_match = (uri, label_es, skill_type, skill_group)
                            best_match_starts_with = starts_with

                    # Try English
                    if label_en:
                        score_ratio = fuzz.ratio(skill_text.lower(), label_en.lower()) / 100.0
                        score_partial = fuzz.partial_ratio(skill_text.lower(), label_en.lower()) / 100.0

                        if len(skill_text) <= 4:
                            score = score_ratio
                        elif len(label_en) > len(skill_text) and len(skill_text) <= 6:
                            score = max(score_ratio, score_partial)
                        else:
                            score = score_ratio

                        starts_with = label_en.lower().startswith(skill_text.lower())
                        if score > best_score or (score == best_score and starts_with and not best_match_starts_with):
                            best_score = score
                            best_match = (uri, label_en, skill_type, skill_group)
                            best_match_starts_with = starts_with

                effective_threshold = self.FUZZY_THRESHOLD_SHORT if len(skill_text) <= 4 else self.FUZZY_THRESHOLD

                if best_match and best_score >= effective_threshold:
                    uri, matched_label, skill_type, skill_group = best_match

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=round(best_score, 3),
                        match_method='fuzzy',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 3 (fuzzy) error for '{skill_text}': {e}")

        return None

    def _layer4_substring_match(self, skill_text: str) -> Optional[ESCOMatch]:
        """
        Layer 4: Substring/contains matching for skills that appear as part of ESCO labels.

        Rules:
        1. ESCO label contains the skill text as a whole word
        2. Prioritize matches where ESCO label starts with skill text
        3. Minimum skill length: 3 characters (avoid false positives)
        4. Return highest confidence match

        Confidence calculation:
        - Starts with skill_text: 0.90
        - Contains skill_text (word boundary): 0.85
        """
        if len(skill_text) < 3:
            return None  # Too short for substring matching

        try:
            with psycopg2.connect(self.db_url) as conn:
                cursor = conn.cursor()

                # Search for ESCO labels containing the skill text
                # Use word boundaries to avoid partial word matches
                search_pattern = f'%{skill_text.lower()}%'

                cursor.execute("""
                    SELECT skill_uri, preferred_label_es, preferred_label_en, skill_type, skill_group
                    FROM esco_skills
                    WHERE is_active = TRUE
                      AND (LOWER(preferred_label_es) LIKE %s
                           OR LOWER(preferred_label_en) LIKE %s)
                    LIMIT 100
                """, (search_pattern, search_pattern))

                candidates = cursor.fetchall()

                if not candidates:
                    return None

                best_match = None
                best_confidence = 0.0

                for uri, label_es, label_en, skill_type, skill_group in candidates:
                    # Check Spanish label
                    if label_es:
                        # Skip blacklisted labels (false positives from wrong domains)
                        if label_es.lower() in self.BLACKLISTED_LABELS:
                            continue

                        confidence = self._calculate_substring_confidence(skill_text, label_es)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = (uri, label_es, skill_type, skill_group)

                    # Check English label
                    if label_en:
                        # Skip blacklisted labels
                        if label_en.lower() in self.BLACKLISTED_LABELS:
                            continue

                        confidence = self._calculate_substring_confidence(skill_text, label_en)
                        if confidence > best_confidence:
                            best_confidence = confidence
                            best_match = (uri, label_en, skill_type, skill_group)

                # Only return if confidence meets minimum threshold
                if best_match and best_confidence >= self.SUBSTRING_CONFIDENCE:
                    uri, matched_label, skill_type, skill_group = best_match

                    return ESCOMatch(
                        skill_text=skill_text,
                        matched_skill_text=matched_label,
                        esco_skill_uri=uri,
                        confidence_score=round(best_confidence, 3),
                        match_method='substring',
                        esco_skill_name=matched_label,
                        skill_type=skill_type or 'unknown',
                        skill_group=skill_group or 'unknown'
                    )

        except Exception as e:
            logger.error(f"Layer 4 (substring) error for '{skill_text}': {e}")

        return None

    def _calculate_substring_confidence(self, skill_text: str, esco_label: str) -> float:
        """
        Calculate confidence score for substring match.

        Higher confidence for:
        - Exact word boundary matches
        - Matches at start of label
        - Shorter ESCO labels (more specific)
        """
        skill_lower = skill_text.lower()
        label_lower = esco_label.lower()

        # Check if skill appears as whole word in label
        words_in_label = label_lower.split()

        # Case 1: Exact word match at start (highest confidence)
        if label_lower.startswith(skill_lower + ' ') or label_lower.startswith(skill_lower + '('):
            return 0.95

        # Case 2: Skill is one of the words in the label
        if skill_lower in words_in_label:
            # Higher confidence if it's the first word
            if words_in_label[0] == skill_lower:
                return 0.92
            return 0.88

        # Case 3: Contains as substring (with word boundary check)
        if f' {skill_lower} ' in f' {label_lower} ':
            return 0.85

        # Case 4: Starts with skill but no space (e.g., "HTML" in "HTML5")
        if label_lower.startswith(skill_lower):
            return 0.87

        # Case 5: Contains but no clear word boundary (lowest confidence)
        if skill_lower in label_lower:
            return 0.80

        return 0.0

    def get_matching_stats(self, matches: Dict[str, Optional[ESCOMatch]]) -> Dict[str, Any]:
        """Get statistics about matching results."""
        total = len(matches)
        matched = sum(1 for m in matches.values() if m is not None)
        emergent = total - matched

        # Count by method
        exact_count = sum(1 for m in matches.values() if m and m.match_method == 'exact')
        fuzzy_count = sum(1 for m in matches.values() if m and m.match_method == 'fuzzy')
        substring_count = sum(1 for m in matches.values() if m and m.match_method == 'substring')
        manual_dict_count = sum(1 for m in matches.values() if m and m.match_method == 'manual_dict')

        return {
            'total_skills': total,
            'matched': matched,
            'match_rate': matched / total if total > 0 else 0.0,
            'emergent_skills': emergent,
            'emergent_rate': emergent / total if total > 0 else 0.0,
            'by_method': {
                'exact': exact_count,
                'fuzzy': fuzzy_count,
                'substring': substring_count,
                'manual_dict': manual_dict_count
            }
        }
