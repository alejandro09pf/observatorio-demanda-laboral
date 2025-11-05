"""
Prompt Templates - Direct skill extraction from job ads.
Optimized for Spanish language job postings from Latin America.
Pipeline B: LLM as primary extractor (parallel to NER+Regex).
"""

from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class PromptTemplates:
    """Manages prompt templates for LLM-based skill extraction."""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, str]:
        """Load all prompt templates."""
        return {
            "extract_skills": self.EXTRACT_SKILLS_TEMPLATE,
            "extract_skills_structured": self.EXTRACT_SKILLS_STRUCTURED_TEMPLATE,
        }

    # === DIRECT SKILL EXTRACTION PROMPTS ===

    EXTRACT_SKILLS_TEMPLATE = """Eres un experto extractor de habilidades del mercado laboral tecnológico en América Latina.

TU TAREA: Extrae TODAS las habilidades (técnicas y blandas) que el puesto requiere, sin importar dónde aparezcan en la oferta.

QUÉ ES UNA HABILIDAD:
Una habilidad es cualquier conocimiento, capacidad o competencia que el candidato necesita tener o desarrollar para desempeñar el puesto exitosamente.

Incluye:
- Habilidades técnicas/hard skills: lenguajes de programación, frameworks, herramientas, bases de datos, metodologías, certificaciones
- Habilidades blandas/soft skills: liderazgo, comunicación, trabajo en equipo, resolución de problemas, pensamiento crítico

REGLAS DE EXTRACCIÓN:
1. Extrae skills de CUALQUIER sección: requisitos, responsabilidades, funciones, perfil
2. Las responsabilidades implican skills: "Liderarás equipo" → "Liderazgo", "Desarrollarás APIs" → "Desarrollo de APIs"
3. Normaliza nombres técnicos: postgres→PostgreSQL, js→JavaScript, k8s→Kubernetes, react→React
4. Separa tecnologías combinadas: "AWS/Azure" → ["AWS", "Azure"]
5. NO extraigas: beneficios del empleador, capacitaciones futuras, años de experiencia, ubicación geográfica, salario, horarios

CÓMO DISTINGUIR:
✅ SÍ EXTRAER:
- "Experiencia con Python" → Python
- "Conocimientos de Docker" → Docker
- "Liderarás el equipo de frontend" → Liderazgo, Frontend
- "Desarrollarás APIs REST" → Desarrollo de APIs, REST
- "Capacidad de trabajo en equipo" → Trabajo en equipo
- "Resolución de problemas complejos" → Resolución de problemas

❌ NO EXTRAER:
- "Aprenderás Kubernetes con nosotros" (capacitación futura, no requisito actual)
- "Seguro médico privado" (beneficio)
- "3+ años de experiencia" (experiencia, no skill)
- "Inglés intermedio" (idioma - no es una skill técnica o blanda)
- "Trabajo remoto" (modalidad)
- "Salario competitivo" (compensación)

EJEMPLOS REALISTAS CON RUIDO:

Ejemplo 1:
Título: "Desarrollador Full Stack - Remoto"
Texto: "Somos una startup innovadora de Bogotá con 50 empleados. Buscamos desarrollador con 3+ años de experiencia en React o Vue, Node.js, y bases de datos postgres/MySQL. Experiencia con AWS o GCP es un plus. Inglés intermedio.

Responsabilidades: Desarrollarás nuevas features, darás soporte al equipo, participarás en code reviews.

Beneficios: Trabajo remoto, seguro médico privado, capacitación continua en tecnologías cloud, aprenderás Kubernetes con nuestro equipo DevOps.

Requisitos: Título universitario en Ingeniería de Sistemas o afines. Excelente comunicación y trabajo en equipo."
Output: {{"skills": ["React", "Vue.js", "Node.js", "PostgreSQL", "MySQL", "AWS", "GCP", "Desarrollo de Features", "Soporte Técnico", "Code Review", "Comunicación", "Trabajo en Equipo"]}}

Ejemplo 2:
Título: "Ingeniero DevOps Senior"
Texto: "Empresa líder en transformación digital busca DevOps Engineer para unirse a nuestro equipo en México City.

Lo que harás: Automatizarás procesos de deploy, mejorarás nuestra infraestructura cloud, liderarás proyectos de migración.

Lo que necesitas: Docker, k8s, experiencia con Jenkins/GitLab CI/CD, Terraform o Ansible para IaC, scripting en Python o Bash. Certificación AWS/Azure deseable.

Ofrecemos: Salario competitivo, bonos anuales, entrenamiento en nuevas tecnologías, ambiente colaborativo. Aprenderás sobre arquitecturas serverless.

Perfil: 5+ años experiencia, proactividad, mentalidad ágil."
Output: {{"skills": ["Docker", "Kubernetes", "Jenkins", "GitLab CI/CD", "Terraform", "Ansible", "Python", "Bash", "AWS Certification", "Azure Certification", "Automatización", "Infraestructura Cloud", "Liderazgo de Proyectos", "Migración de Sistemas", "Proactividad", "Metodologías Ágiles"]}}

Ejemplo 3:
Título: "Data Analyst - Híbrido"
Texto: "¿Quiénes somos? Empresa fintech argentina en crecimiento con presencia en LATAM.

Tu misión: Analizarás datos de clientes, crearás dashboards ejecutivos, identificarás oportunidades de negocio, presentarás insights al equipo comercial.

Requisitos técnicos:
- SQL avanzado (queries complejas, optimización)
- Power BI y/o Tableau para visualizaciones
- Excel nivel experto (tablas dinámicas, macros)
- Python para análisis (pandas, numpy, matplotlib)
- Conocimientos de estadística

Requisitos generales: Profesional en Ingeniería, Matemáticas o Economía. Inglés técnico (leer documentación). Capacidad analítica, atención al detalle.

Qué ofrecemos: Modalidad híbrida (3 días oficina), obra social premium, día off de cumpleaños, capacitación en machine learning y big data tools como Spark.

Deseable: Experiencia previa en fintech."
Output: {{"skills": ["SQL", "Power BI", "Tableau", "Excel", "Python", "Pandas", "NumPy", "Matplotlib", "Estadística", "Análisis de Datos", "Dashboards", "Identificación de Oportunidades", "Presentación de Insights", "Pensamiento Analítico", "Atención al Detalle"]}}

AHORA EXTRAE LAS HABILIDADES DE ESTA OFERTA:

Título: {job_title}

Descripción completa:
{job_description}

Instrucciones finales:
- Analiza TODA la oferta: "Requisitos", "Responsabilidades", "Funciones", "Perfil", "Habilidades"
- Extrae habilidades técnicas Y blandas que el puesto requiere
- Las responsabilidades implican skills: "Liderarás" → Liderazgo, "Desarrollarás" → Desarrollo
- Ignora SOLO: beneficios futuros ("aprenderás"), años experiencia, salario, ubicación, horarios
- Normaliza nombres técnicos a su forma estándar
- Separa opciones combinadas en items separados

IMPORTANTE: Tu respuesta debe ser ÚNICAMENTE el objeto JSON. No agregues explicaciones, comentarios, ni texto adicional antes o después del JSON.

JSON:"""

    EXTRACT_SKILLS_STRUCTURED_TEMPLATE = """Eres un experto extractor de habilidades técnicas del mercado laboral latinoamericano.

Analiza esta oferta de trabajo y extrae todas las habilidades técnicas, clasificándolas por tipo.

**Título:** {job_title}
**País:** {country}

**Descripción:**
{job_description}

**Extrae skills en estas categorías:**
1. **programming_languages**: Lenguajes de programación (Python, Java, JavaScript, etc.)
2. **frameworks**: Frameworks y librerías (Django, React, Spring Boot, etc.)
3. **databases**: Bases de datos (PostgreSQL, MongoDB, MySQL, etc.)
4. **tools**: Herramientas y software (Git, Docker, Kubernetes, etc.)
5. **cloud**: Servicios cloud (AWS, Azure, GCP, etc.)
6. **methodologies**: Metodologías (Scrum, Agile, DevOps, etc.)
7. **certifications**: Certificaciones (AWS Certified, PMP, etc.)
8. **other_technical**: Otras habilidades técnicas que no encajen arriba

**Reglas:**
- SOLO habilidades técnicas verificables
- NO soft skills ("liderazgo", "trabajo en equipo")
- NO requisitos administrativos ("experiencia", "título universitario")
- Normaliza a forma estándar ("react js" → "React")
- Sin duplicados

**Responde con JSON:**
```json
{{
  "programming_languages": ["Python", "JavaScript"],
  "frameworks": ["Django", "React"],
  "databases": ["PostgreSQL"],
  "tools": ["Git", "Docker"],
  "cloud": ["AWS"],
  "methodologies": ["Scrum"],
  "certifications": [],
  "other_technical": ["REST APIs", "CI/CD"]
}}
```

SOLO el JSON, sin explicaciones."""

    # === HELPER METHODS ===

    def get_prompt(self, template_name: str, **kwargs) -> str:
        """
        Get a formatted prompt template.

        Args:
            template_name: Name of the template
            **kwargs: Variables to inject into template

        Returns:
            Formatted prompt string
        """
        if template_name not in self.templates:
            raise ValueError(
                f"Template '{template_name}' not found. "
                f"Available: {list(self.templates.keys())}"
            )

        template = self.templates[template_name]

        # Format the template with provided variables
        try:
            return template.format(**kwargs)
        except KeyError as e:
            logger.error(f"Missing template variable: {e}")
            raise

    def format_job_description(
        self,
        title: str,
        description: str,
        requirements: str = "",
        max_length: int = None
    ) -> str:
        """
        Format job components into a single description for LLM.

        Args:
            title: Job title
            description: Job description
            requirements: Job requirements (optional)
            max_length: Maximum character length (None = no limit, uses model context)

        Returns:
            Formatted job description
        """
        # Combine all text
        full_text = f"{title}\n\n{description}"

        if requirements:
            full_text += f"\n\nRequisitos:\n{requirements}"

        # Only truncate if max_length is explicitly provided
        if max_length and len(full_text) > max_length:
            logger.warning(
                f"Job description truncated from {len(full_text)} "
                f"to {max_length} characters"
            )
            full_text = full_text[:max_length] + "..."

        return full_text
