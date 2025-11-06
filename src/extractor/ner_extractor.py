import spacy
from spacy.tokens import Doc, Span
from typing import List, Dict, Tuple, Optional, Any
import logging
import os
from pathlib import Path
from dataclasses import dataclass
from config.settings import get_settings
import re

logger = logging.getLogger(__name__)

# ============================================================================
# STOPWORDS AND FILTERS (NLP Engineering)
# ============================================================================

# Web navigation and UI terms (not technical skills)
WEB_NAVIGATION_STOPWORDS = {
    'regresar', 'volver', 'inicio', 'home', 'apply', 'aplicar', 'postularme',
    'postular', 'enviar', 'submit', 'registrarse', 'login', 'ingresar',
    'sugerencias', 'suggestions', 'buscar', 'search', 'filtrar', 'filter',
    'ver', 'view', 'más', 'more', 'menos', 'less', 'siguiente', 'next',
    'anterior', 'previous', 'página', 'page', 'puesto', 'vacante', 'job'
}

# Generic verbs (not skills)
VERB_STOPWORDS = {
    'desarrollar', 'develop', 'implementar', 'implement', 'crear', 'create',
    'diseñar', 'design', 'colaborar', 'collaborate', 'participar', 'participate',
    'trabajar', 'work', 'realizar', 'perform', 'ejecutar', 'execute',
    'mantener', 'maintain', 'gestionar', 'manage', 'analizar', 'analyze',
    'mejorar', 'improve', 'optimizar', 'optimize', 'integrar', 'integrate',
    'configurar', 'configure', 'administrar', 'administrate', 'coordinar',
    'transformando', 'transforming', 'buscamos', 'seeking', 'ofrecemos',
    'construyendo', 'building', 'creando', 'creating'
}

# Generic nouns and adjectives (not skills)
GENERIC_STOPWORDS = {
    'senior', 'junior', 'mid', 'jr', 'sr', 'lead', 'principal', 'staff',
    'experiencia', 'experience', 'conocimiento', 'knowledge', 'habilidad',
    'skill', 'capacidad', 'ability', 'requisito', 'requirement', 'deseable',
    'nice to have', 'indispensable', 'excluyente', 'required', 'preferred',
    'años', 'years', 'meses', 'months', 'nivel', 'level', 'grado', 'degree',
    'universitario', 'university', 'título', 'title', 'certificación',
    'nuestro', 'our', 'tu', 'your', 'su', 'their', 'the', 'a', 'an',
    'equipo', 'team', 'empresa', 'company', 'proyecto', 'project',
    'producto', 'product', 'cliente', 'client', 'usuario', 'user',
    'dont', 'don\'t', 'cant', 'can\'t', 'wont', 'won\'t', 'isnt', 'isn\'t',
    'información', 'information', 'datos', 'data', 'documentación',
    'deseables', 'conocimientos', 'habilidades', 'competencias',
    'responsabilidades', 'responsibilities', 'funciones', 'functions'
}

# Latin American countries (not skills, unless it's a location-specific skill)
LATAM_COUNTRIES = {
    'argentina', 'bolivia', 'brasil', 'brazil', 'chile', 'colombia',
    'costa rica', 'cuba', 'ecuador', 'el salvador', 'guatemala',
    'honduras', 'méxico', 'mexico', 'nicaragua', 'panamá', 'panama',
    'paraguay', 'perú', 'peru', 'república dominicana', 'uruguay',
    'venezuela', 'puerto rico'
}

# Common company names (not skills)
COMPANY_NAMES = {
    'google', 'microsoft', 'amazon', 'facebook', 'meta', 'apple',
    'ibm', 'oracle', 'sap', 'salesforce', 'adobe', 'intel', 'nvidia',
    'bbva', 'santander', 'bancolombia', 'mercadolibre', 'globant',
    'accenture', 'deloitte', 'pwc', 'kpmg', 'cognizant', 'infosys'
}

# Words that are too short or ambiguous (except known technical acronyms)
# Technical acronyms that ARE valid are in VALID_TECHNICAL_ACRONYMS
AMBIGUOUS_SHORT_WORDS = {
    'it', 'x', 'y', 'z', 'a', 'b', 'c', 'i', 'o', 'e', 's', 't', 'n',
    'job', 'ad', 'tu', 'su', 'el', 'la', 'un', 'de', 'en', 'con', 'por',
    'para', 'como', 'que', 'se', 'no', 'si', 'or', 'and', 'but', 'if',
    'banco', 'bank', 'ks', 'vs', 'etc', 'eg', 'ie'
}

# Technical generic terms (too vague to be skills - FASE 3 Mejora #3)
# These words appear in technical contexts but are NOT specific skills
TECH_GENERIC_STOPWORDS = {
    'backend', 'frontend', 'fullstack', 'full-stack', 'full stack',
    'development', 'engineering', 'developer', 'engineer', 'desarrollador',
    'ingeniero', 'programador', 'programmer', 'software', 'system', 'systems',
    'aplicaciones', 'applications', 'app', 'apps', 'web', 'mobile', 'móvil',
    'desktop', 'escritorio',
    # NOTA: 'cloud', 'data', 'bi', 'apis' removidos - pueden ser skills válidas en contexto
    'base de datos', 'database', 'código', 'code', 'coding', 'codificación',
    'rest api', 'restful', 'microservicio', 'microservice',
    'framework', 'frameworks', 'library', 'libraries', 'librería', 'librerías',
    'herramienta', 'herramientas', 'tool', 'tools', 'tecnología', 'technology',
    'plataforma', 'platform', 'service', 'services', 'servicio', 'servicios',
    'proyecto', 'project', 'projects', 'producto', 'product', 'products',
    'solución', 'solution', 'solutions', 'cliente', 'client', 'server',
    'servidor', 'infraestructura', 'infrastructure', 'arquitectura', 'architecture',
    'diseño', 'design', 'testing', 'tests', 'pruebas', 'calidad', 'quality',
    'performance', 'rendimiento', 'optimización', 'optimization',
    'integración', 'integration', 'deployment', 'despliegue', 'producción', 'production',
    'ambiente', 'environment', 'entorno', 'configuración', 'configuration',
    'documentación', 'documentation', 'soporte', 'support', 'maintenance', 'mantenimiento',
    'análisis', 'analysis', 'implementación', 'implementation', 'desarrollo',
    # Spanish descriptive words (not skills)
    'adicionales', 'bonus', 'contribuciones', 'familiaridad', 'conocimiento',
    'experiencia', 'habilidad', 'capacidad', 'dominio', 'manejo', 'uso',
    'colaborar', 'colaboración', 'trabajo', 'equipo', 'team'
}

# Valid technical acronyms (these are NOT stopwords)
VALID_TECHNICAL_ACRONYMS = {
    'ai', 'ml', 'nlp', 'cv', 'dl', 'rl', 'gan', 'cnn', 'rnn', 'lstm',
    'api', 'rest', 'soap', 'grpc', 'sdk', 'ide', 'cli', 'gui', 'ui', 'ux',
    'ci', 'cd', 'qa', 'qc', 'devops', 'mlops', 'devsecops',
    'aws', 'gcp', 'oci', 'vpc', 'cdn', 'dns', 'ssl', 'tls', 'tcp', 'udp',
    'http', 'https', 'ssh', 'ftp', 'smtp', 'imap', 'pop',
    'sql', 'nosql', 'rdbms', 'orm', 'etl', 'olap', 'oltp',
    'html', 'css', 'xml', 'json', 'yaml', 'csv', 'pdf',
    'oop', 'mvc', 'mvvm', 'ddd', 'tdd', 'bdd', 'solid', 'dry',
    'git', 'svn', 'crm', 'erp', 'bi', 'kpi', 'roi', 'sla', 'slo'
}

# Combine all stopwords
ALL_STOPWORDS = (
    WEB_NAVIGATION_STOPWORDS | VERB_STOPWORDS | GENERIC_STOPWORDS |
    LATAM_COUNTRIES | COMPANY_NAMES | AMBIGUOUS_SHORT_WORDS |
    TECH_GENERIC_STOPWORDS
)

@dataclass
class NERSkill:
    """Represents a skill found by NER."""
    skill_text: str
    skill_type: str
    confidence: float
    position: tuple
    context: str
    ner_label: str
    extraction_method: str

class NERExtractor:
    """Extract skills using Named Entity Recognition."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.settings = get_settings()
        self.nlp = None
        
        # Load spaCy model
        if model_path and Path(model_path).exists():
            try:
                self.nlp = spacy.load(model_path)
                logger.info(f"Loaded custom NER model from {model_path}")
            except Exception as e:
                logger.warning(f"Failed to load custom model: {e}")
                self._load_default_model()
        else:
            self._load_default_model()
        
        # Add custom pipeline components
        if self.nlp:
            self._add_tech_entity_ruler()
    
    def _load_default_model(self):
        """Load default spaCy model."""
        try:
            # Try Spanish large model first (Mejora 1.5 - 2025-01-05)
            # Large model has better accuracy for multi-word NER (~92% vs ~85%)
            self.nlp = spacy.load("es_core_news_lg")
            logger.info("✅ Loaded Spanish spaCy LARGE model (es_core_news_lg)")
        except OSError:
            try:
                # Fallback to English
                self.nlp = spacy.load("en_core_web_sm")
                logger.info("Loaded English spaCy model")
            except OSError:
                logger.warning("No spaCy models found. NER extraction will be disabled.")
                self.nlp = None
    
    def _add_tech_entity_ruler(self):
        """
        Add rule-based entity recognition for ESCO technical skills.

        As a Senior NLP Engineer, I'm loading ~500 technical skills from ESCO
        to create an EntityRuler that recognizes tech skills BEFORE the generic NER.

        Strategy:
        1. Query ESCO for technical skills (onet_hot_tech, onet_in_demand, tier1_critical)
        2. Create patterns for ES + EN labels + common aliases
        3. Add EntityRuler before NER → tech skills won't be confused with generic entities
        """
        if not self.nlp:
            return

        try:
            import psycopg2

            db_url = self.settings.database_url
            if db_url.startswith('postgresql://'):
                db_url = db_url.replace('postgresql://', 'postgres://')

            # Query technical skills from ESCO
            with psycopg2.connect(db_url) as conn:
                cursor = conn.cursor()

                # Get technical skills (hot tech + in-demand + critical + technical knowledge)
                # EXPANDED (Mejora 2.3 - 2025-01-05): Include technical "knowledge" skills
                cursor.execute("""
                    SELECT DISTINCT
                        preferred_label_es,
                        preferred_label_en
                    FROM esco_skills
                    WHERE is_active = TRUE
                      AND (
                        -- Hot tech, in-demand, critical
                        skill_type IN ('onet_hot_tech', 'onet_in_demand',
                                       'tier1_critical', 'tier0_critical')
                        -- OR technical knowledge (filtered by keywords)
                        OR (skill_type = 'knowledge' AND (
                            preferred_label_es ILIKE '%programación%' OR
                            preferred_label_es ILIKE '%software%' OR
                            preferred_label_es ILIKE '%base de datos%' OR
                            preferred_label_es ILIKE '%cloud%' OR
                            preferred_label_es ILIKE '%desarrollo%' OR
                            preferred_label_es ILIKE '%web%' OR
                            preferred_label_es ILIKE '%API%' OR
                            preferred_label_es ILIKE '%aplicación%' OR
                            preferred_label_es ILIKE '%sistema informático%' OR
                            preferred_label_es ILIKE '%tecnología de la información%' OR
                            preferred_label_es ILIKE '%seguridad informática%' OR
                            preferred_label_es ILIKE '%machine learning%' OR
                            preferred_label_es ILIKE '%inteligencia artificial%' OR
                            preferred_label_es ILIKE '%DevOps%' OR
                            preferred_label_en ILIKE '%programming%' OR
                            preferred_label_en ILIKE '%software%' OR
                            preferred_label_en ILIKE '%database%' OR
                            preferred_label_en ILIKE '%machine learning%' OR
                            preferred_label_en ILIKE '%artificial intelligence%'
                        ))
                      )
                    ORDER BY preferred_label_es;
                """)

                esco_skills = cursor.fetchall()

            # Create patterns for EntityRuler
            patterns = []

            for label_es, label_en in esco_skills:
                # Spanish label
                if label_es:
                    # Exact match (case-insensitive)
                    patterns.append({
                        "label": "TECH_SKILL",
                        "pattern": [{"LOWER": label_es.lower()}]
                    })

                    # Handle multi-word skills (e.g., "React Native")
                    if ' ' in label_es:
                        words = label_es.split()
                        patterns.append({
                            "label": "TECH_SKILL",
                            "pattern": [{"LOWER": w.lower()} for w in words]
                        })

                # English label (if different from Spanish)
                if label_en and label_en != label_es:
                    patterns.append({
                        "label": "TECH_SKILL",
                        "pattern": [{"LOWER": label_en.lower()}]
                    })

                    if ' ' in label_en:
                        words = label_en.split()
                        patterns.append({
                            "label": "TECH_SKILL",
                            "pattern": [{"LOWER": w.lower()} for w in words]
                        })

            # Add EntityRuler to pipeline BEFORE NER
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            ruler.add_patterns(patterns)

            logger.info(f"✅ Added EntityRuler with {len(patterns)} ESCO technical skill patterns (from {len(esco_skills)} skills)")

            # Add O*NET + ESCO Technical Skills (276 skills) - Hardcoded
            # External taxonomies - NO data leakage
            # Source: O*NET 2024 Hot Technologies + ESCO tier0/tier1/tier2/onet_hot_tech/onet_in_demand
            onet_esco_skills = [
                "AJAX", "API Design", "API Security", "ASP.NET Core", "AWS Lambda",
                "Adobe Acrobat", "Adobe After Effects", "Adobe Illustrator", "Adobe InDesign",
                "Adobe Photoshop", "Agile", "Alteryx software", "Amazon DynamoDB",
                "Amazon Elastic Compute Cloud EC2", "Amazon Redshift",
                "Amazon Simple Storage Service S3", "Amazon Web Services AWS CloudFormation",
                "Ansible software", "Apache Airflow", "Apache Cassandra", "Apache Hadoop",
                "Apache Hive", "Apache Kafka", "Apache Maven", "Apache Pulsar", "Apache Spark",
                "Apache Subversion SVN", "Apache Tomcat", "Apple Safari", "Apple iOS",
                "Apple macOS", "Atlassian Bitbucket", "Atlassian Confluence", "Atlassian JIRA",
                "Auth0", "Authentication", "Authorization", "Autodesk AutoCAD", "Autodesk Revit",
                "Backend Development", "Bash", "Behavior-Driven Development", "Bentley MicroStation",
                "BigQuery", "Bootstrap", "Border Gateway Protocol BGP", "C", "C#", "C++",
                "Cascading style sheets CSS", "Chef", "CircleCI", "Cisco Webex", "Clerk",
                "Cloud Native", "Cloudflare", "Code Review", "Computer Vision",
                "Container Orchestration", "Containerization", "Contentful",
                "Continuous Deployment", "Continuous Integration", "Cypress", "Dart",
                "Data Infrastructure", "Data Lake", "Data Pipeline", "Data Warehouse",
                "Datadog", "Deep Learning", "Django", "Docker", "Domain-Driven Design",
                "Drupal", "ETL", "Eclipse IDE", "Eclipse Jersey", "Elasticsearch",
                "Entity Framework", "Epic Systems", "Event-Driven Architecture", "Expo",
                "Express.js", "Extensible markup language XML", "Facebook", "FastAPI",
                "Figma", "Firebase", "Flask", "Flutter", "Frontend Development",
                "Full-Stack Development", "Git", "GitHub", "GitHub Actions", "GitLab",
                "GitLab CI/CD", "Go", "Google Analytics", "Google Android", "Google Angular",
                "Google Cloud Platform", "Google Docs", "Google Sheets", "Grafana", "GraphQL",
                "GraphQL API", "Helm", "Heroku", "Hibernate ORM", "HubSpot software",
                "Hugging Face", "Hypertext markup language HTML", "IBM DB2", "IBM SPSS Statistics",
                "IBM Terraform", "IBM WebSphere MQ", "Informatica software",
                "Infrastructure as Code", "Ionic", "JUnit", "JWT", "JavaScript",
                "JavaScript Object Notation JSON", "Jenkins CI", "Jest", "Jupyter Notebook",
                "Keras", "Keycloak", "Kotlin", "Kubernetes", "LangChain", "Laravel", "Linux",
                "MEDITECH software", "MLOps", "Machine Learning", "Magento",
                "Marketo Marketing Automation", "Material-UI", "Microservices",
                "Microsoft .NET Framework", "Microsoft ASP.NET", "Microsoft Access",
                "Microsoft Active Directory", "Microsoft Active Server Pages ASP",
                "Microsoft Azure", "Microsoft Dynamics", "Microsoft Excel", "Microsoft Outlook",
                "Microsoft Power BI", "Microsoft PowerPoint", "Microsoft PowerShell",
                "Microsoft Project", "Microsoft SQL Server",
                "Microsoft SQL Server Integration Services SSIS",
                "Microsoft SQL Server Reporting Services SSRS", "Microsoft SharePoint",
                "Microsoft Team Foundation Server", "Microsoft Teams", "Microsoft Visio",
                "Microsoft Visual Basic", "Microsoft Visual Studio", "Microsoft Windows",
                "Microsoft Windows Server", "Microsoft Word", "MongoDB", "Mozilla Firefox",
                "MySQL", "NATS", "Natural Language Processing", "NestJS", "Netlify",
                "New Relic", "Next.js", "Nginx", "NoSQL", "Node.js", "NumPy", "Nuxt.js",
                "OAuth 2.0", "OWASP", "Oracle Database", "Oracle Java",
                "Oracle Java 2 Platform Enterprise Edition J2EE", "Oracle PL/SQL",
                "Oracle PeopleSoft", "Oracle Primavera Enterprise Project Portfolio Management",
                "Oracle SQL Developer", "PHP", "Pair Programming", "Pandas", "Perl",
                "Playwright", "PostgreSQL", "Postman", "Prisma", "Progressive Web Apps",
                "Prometheus", "Puppet", "PyTorch", "Pytest", "Python", "R", "REST API",
                "RESTful API", "RabbitMQ", "React", "React Native", "React Testing Library",
                "Red Hat Enterprise Linux", "Red Hat OpenShift", "Redis", "Redux",
                "Reinforcement Learning", "Remix", "Responsive Design", "Ruby",
                "Ruby on Rails", "Rust", "SAP ERP", "SAP software", "SAS", "Salesforce software",
                "Sanity", "Scala", "Scikit-learn", "Scrum", "Selenium", "Sentry", "Sequelize",
                "Serverless", "ServiceNow", "Shadcn/ui", "Shell script", "Shopify",
                "Single Page Application", "Slack", "Snowflake", "Splunk Enterprise",
                "Spring Boot", "Spring Framework", "Strapi", "Stream Processing", "Stripe",
                "Structured query language SQL", "Supabase", "Svelte", "Swift", "Tableau",
                "Tailwind CSS", "TensorFlow", "Teradata Database", "Test-Driven Development",
                "The MathWorks MATLAB", "Transact-SQL", "Trimble SketchUp Pro", "TypeScript",
                "UNIX", "UNIX Shell", "Vercel", "Vite", "Vitest", "Vue.js", "Web Security",
                "Webpack", "WooCommerce", "WordPress", "Workday software", "Yardi software",
                "Zoom", "Zustand", "dbt", "jQuery", "tRPC"
            ]

            # Convert O*NET/ESCO skills to EntityRuler patterns and add to existing patterns
            onet_patterns_added = 0
            for skill in onet_esco_skills:
                # Single word pattern
                patterns.append({
                    "label": "TECH_SKILL",
                    "pattern": skill
                })
                onet_patterns_added += 1

                # Multi-word pattern (case-insensitive token matching)
                if ' ' in skill:
                    words = skill.split()
                    patterns.append({
                        "label": "TECH_SKILL",
                        "pattern": [{"LOWER": w.lower()} for w in words]
                    })
                    onet_patterns_added += 1

            # Update the ruler with all patterns (ESCO from DB + O*NET/ESCO hardcoded)
            ruler.add_patterns(patterns)
            logger.info(f"✅ Added {onet_patterns_added} O*NET/ESCO hardcoded patterns ({len(onet_esco_skills)} skills) to EntityRuler")

        except Exception as e:
            logger.warning(f"Failed to load ESCO skills for EntityRuler: {e}")
            # Fallback to basic patterns
            basic_patterns = [
                {"label": "TECH_SKILL", "pattern": [{"LOWER": "python"}]},
                {"label": "TECH_SKILL", "pattern": [{"LOWER": "javascript"}]},
                {"label": "TECH_SKILL", "pattern": [{"LOWER": "react"}]},
                {"label": "TECH_SKILL", "pattern": [{"LOWER": "docker"}]},
                {"label": "TECH_SKILL", "pattern": [{"LOWER": "kubernetes"}]},
            ]
            ruler = self.nlp.add_pipe("entity_ruler", before="ner")
            ruler.add_patterns(basic_patterns)
            logger.info(f"Added EntityRuler with {len(basic_patterns)} basic patterns (fallback)")
    
    def extract_skills(self, text: str) -> List[NERSkill]:
        """Extract skills from text using NER."""
        if not text or not self.nlp:
            return []
        
        logger.info(f"Extracting skills with NER from text (length: {len(text)})")
        skills = []
        
        try:
            doc = self.nlp(text)
            
            # Extract named entities
            for ent in doc.ents:
                if self._is_technical_skill(ent.text):
                    skill = NERSkill(
                        skill_text=ent.text,
                        skill_type='ner_entity',
                        confidence=0.6,
                        position=(ent.start_char, ent.end_char),
                        context=ent.sent.text.strip(),
                        ner_label=ent.label_,
                        extraction_method='ner'
                    )
                    skills.append(skill)

            # ============================================================================
            # NOUN CHUNKS DISABLED - Experimento #8 (2025-01-05)
            # Razón: Hit rate 7-20% (93% ruido) según análisis deep_analysis_missing_skills.py
            # Extrae: "Cuales", "Entrega", "Auxilio", "Vacaciones", frases largas, etc.
            # Decisión: Desactivar para reducir ruido. Las skills válidas se agregan a Regex.
            # ============================================================================
            # for chunk in doc.noun_chunks:
            #     if self._is_technical_skill(chunk.text):
            #         skill = NERSkill(
            #             skill_text=chunk.text,
            #             skill_type='noun_chunk',
            #             confidence=0.5,
            #             position=(chunk.start_char, chunk.end_char),
            #             context=chunk.sent.text.strip(),
            #             ner_label='NOUN_CHUNK',
            #             extraction_method='ner'
            #         )
            #         skills.append(skill)

            # Remove duplicates
            unique_skills = self._deduplicate_skills(skills)

            # Filter garbage (stopwords, non-technical terms)
            filtered_skills = self._filter_garbage(unique_skills)
            logger.info(f"Found {len(filtered_skills)} unique skills with NER (filtered from {len(unique_skills)} raw extractions)")
            return filtered_skills
            
        except Exception as e:
            logger.error(f"Error in NER extraction: {e}")
            return []
    
    def _is_technical_skill(self, text: str) -> bool:
        """Check if text looks like a technical skill."""
        text_lower = text.lower()
        
        # Technical indicators
        tech_indicators = [
            'framework', 'library', 'tool', 'platform', 'service',
            'database', 'language', 'technology', 'stack', 'api',
            'cloud', 'devops', 'frontend', 'backend', 'fullstack'
        ]
        
        # Check for technical terms
        for indicator in tech_indicators:
            if indicator in text_lower:
                return True
        
        # Check for common tech patterns
        tech_patterns = [
            r'\.js$', r'\.py$', r'\.net$', r'\.io$', r'\.com$',
            r'^[A-Z][a-z]+$',  # CamelCase
            r'^[A-Z]+$',       # ALL_CAPS
        ]
        
        for pattern in tech_patterns:
            if re.search(pattern, text):
                return True
        
        return False
    
    def _deduplicate_skills(self, skills: List[NERSkill]) -> List[NERSkill]:
        """Remove duplicate skills based on normalized text."""
        unique_skills = []
        seen_texts = set()

        for skill in skills:
            normalized = skill.skill_text.lower().strip()
            if normalized not in seen_texts:
                seen_texts.add(normalized)
                unique_skills.append(skill)

        return unique_skills

    def _filter_garbage(self, skills: List[NERSkill]) -> List[NERSkill]:
        """
        Filter out non-technical garbage from NER extractions.

        As a Senior NLP Engineer, I'm implementing multi-level filters:
        1. Stopwords filter (web nav, verbs, generic nouns, countries, companies)
        2. Length filter (≤2 chars unless technical acronym)
        3. Technical acronym validation (uppercase check)
        4. Numeric-only filter

        Returns:
            List of filtered NERSkill objects (only valid technical skills)
        """
        filtered = []

        for skill in skills:
            skill_lower = skill.skill_text.lower().strip()
            skill_upper = skill.skill_text.upper().strip()

            # Filter 1: Stopwords (comprehensive list)
            if skill_lower in ALL_STOPWORDS:
                logger.debug(f"Filtered stopword: '{skill.skill_text}'")
                continue

            # Filter 2: Very short words (≤2 chars)
            if len(skill.skill_text) <= 2:
                # Exception: Technical acronyms in uppercase
                if skill_upper in {acr.upper() for acr in VALID_TECHNICAL_ACRONYMS}:
                    filtered.append(skill)  # Valid acronym like "AI", "ML", "UI"
                else:
                    logger.debug(f"Filtered short non-technical: '{skill.skill_text}'")
                continue

            # Filter 3: Numeric-only or mostly numeric (not skills)
            if skill.skill_text.replace(' ', '').replace('.', '').isdigit():
                logger.debug(f"Filtered numeric: '{skill.skill_text}'")
                continue

            # Filter 4: Pure punctuation or symbols
            if not any(c.isalnum() for c in skill.skill_text):
                logger.debug(f"Filtered non-alphanumeric: '{skill.skill_text}'")
                continue

            # Filter 4b: Skills starting with punctuation (,Python, ;Java, etc.)
            # FASE 3 - Mejora #3: Catch malformed extractions
            if len(skill.skill_text) > 0 and skill.skill_text[0] in ',;:+·•-':
                logger.debug(f"Filtered punctuation prefix: '{skill.skill_text}'")
                continue

            # Filter 5: ALL_CAPS generic words (CONOCIMIENTOS, FUNCIONES, etc.)
            # But allow known technical acronyms
            if skill.skill_text.isupper() and len(skill.skill_text) > 3:
                if skill_lower not in VALID_TECHNICAL_ACRONYMS:
                    # Check if it's a generic word in caps
                    if skill_lower in ALL_STOPWORDS:
                        logger.debug(f"Filtered ALL_CAPS stopword: '{skill.skill_text}'")
                        continue

            # Passed all filters - this is likely a valid skill
            filtered.append(skill)

        logger.debug(f"Garbage filter: {len(skills)} → {len(filtered)} skills ({len(skills) - len(filtered)} filtered)")
        return filtered 