#!/usr/bin/env python3
"""
Add Missing Critical Skills

Agrega skills técnicas modernas que son MUY comunes pero no están en la taxonomía:
- Machine Learning, Deep Learning, MLOps
- Data Pipeline, Data Infrastructure
- Agile, Scrum, TDD, BDD
- API Development, Microservices
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import psycopg2
from config.settings import get_settings

# Skills críticos que faltan
MISSING_CRITICAL_SKILLS = [
    # AI/ML Concepts (no solo herramientas)
    ('Machine Learning', 'Técnicas y algoritmos de aprendizaje automático', 'AI/ML Concepts'),
    ('Deep Learning', 'Redes neuronales profundas y aprendizaje profundo', 'AI/ML Concepts'),
    ('MLOps', 'Prácticas DevOps para sistemas de Machine Learning', 'AI/ML Operations'),
    ('Natural Language Processing', 'Procesamiento de lenguaje natural', 'AI/ML Concepts'),
    ('Computer Vision', 'Visión por computadora y procesamiento de imágenes', 'AI/ML Concepts'),
    ('Reinforcement Learning', 'Aprendizaje por refuerzo', 'AI/ML Concepts'),

    # Data Engineering Concepts
    ('Data Pipeline', 'Pipelines de procesamiento y transformación de datos', 'Data Engineering'),
    ('Data Infrastructure', 'Infraestructura para procesamiento de datos a escala', 'Data Engineering'),
    ('ETL', 'Extract Transform Load - procesos de integración de datos', 'Data Engineering'),
    ('Data Warehouse', 'Almacén de datos empresarial', 'Data Engineering'),
    ('Data Lake', 'Repositorio centralizado de datos raw', 'Data Engineering'),
    ('Stream Processing', 'Procesamiento de datos en tiempo real', 'Data Engineering'),

    # Software Development Practices
    ('Agile', 'Metodología ágil de desarrollo de software', 'Development Methodologies'),
    ('Scrum', 'Framework ágil para gestión de proyectos', 'Development Methodologies'),
    ('Test-Driven Development', 'TDD - desarrollo guiado por pruebas', 'Development Practices'),
    ('Behavior-Driven Development', 'BDD - desarrollo guiado por comportamiento', 'Development Practices'),
    ('Continuous Integration', 'CI - integración continua de código', 'DevOps Practices'),
    ('Continuous Deployment', 'CD - despliegue continuo automatizado', 'DevOps Practices'),
    ('Code Review', 'Revisión de código entre pares', 'Development Practices'),
    ('Pair Programming', 'Programación en pareja', 'Development Practices'),

    # Architecture Patterns
    ('Microservices', 'Arquitectura de microservicios distribuidos', 'Software Architecture'),
    ('Serverless', 'Arquitectura serverless/FaaS', 'Cloud Architecture'),
    ('API Design', 'Diseño de interfaces de programación', 'Software Architecture'),
    ('RESTful API', 'APIs REST siguiendo principios REST', 'API Development'),
    ('GraphQL API', 'APIs GraphQL para consultas flexibles', 'API Development'),
    ('Event-Driven Architecture', 'Arquitectura basada en eventos', 'Software Architecture'),
    ('Domain-Driven Design', 'DDD - diseño guiado por el dominio', 'Software Architecture'),

    # Cloud Native
    ('Cloud Native', 'Desarrollo nativo para la nube', 'Cloud Computing'),
    ('Containerization', 'Contenedorización de aplicaciones', 'DevOps'),
    ('Container Orchestration', 'Orquestación de contenedores', 'DevOps'),
    ('Infrastructure as Code', 'IaC - infraestructura como código', 'DevOps'),

    # Web Development
    ('Frontend Development', 'Desarrollo de interfaces de usuario', 'Web Development'),
    ('Backend Development', 'Desarrollo de lógica de servidor', 'Web Development'),
    ('Full-Stack Development', 'Desarrollo full-stack frontend y backend', 'Web Development'),
    ('Responsive Design', 'Diseño web responsive y adaptativo', 'Web Development'),
    ('Progressive Web Apps', 'PWA - aplicaciones web progresivas', 'Web Development'),
    ('Single Page Application', 'SPA - aplicaciones de página única', 'Web Development'),

    # Security
    ('API Security', 'Seguridad de APIs', 'Security'),
    ('Web Security', 'Seguridad de aplicaciones web', 'Security'),
    ('Authentication', 'Autenticación de usuarios', 'Security'),
    ('Authorization', 'Autorización y control de acceso', 'Security'),
]

def add_missing_skills():
    """Add missing critical skills."""

    settings = get_settings()
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    print("\n" + "="*80)
    print(" "*20 + "ADDING MISSING CRITICAL SKILLS")
    print("="*80 + "\n")

    # Check current manual skills
    cursor.execute("""
        SELECT COUNT(*) FROM esco_skills
        WHERE skill_uri LIKE 'manual:%'
    """)
    before_count = cursor.fetchone()[0]

    print(f"📊 Current manual skills: {before_count}")
    print(f"📋 Skills to add: {len(MISSING_CRITICAL_SKILLS)}\n")

    inserted = 0
    skipped = 0

    # Get next available ID
    cursor.execute("""
        SELECT MAX(CAST(SUBSTRING(skill_uri FROM 'manual:critical:([0-9]+)') AS INTEGER))
        FROM esco_skills
        WHERE skill_uri LIKE 'manual:critical:%'
    """)
    result = cursor.fetchone()[0]
    next_id = (result + 1) if result else 0

    for idx, (skill_name, description, category) in enumerate(MISSING_CRITICAL_SKILLS):
        skill_uri = f"manual:critical:{next_id + idx:04d}"

        try:
            cursor.execute("""
                INSERT INTO esco_skills (
                    skill_uri, skill_id,
                    preferred_label_en, preferred_label_es,
                    description_es, description_en,
                    skill_type, skill_group, skill_family,
                    is_active
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (skill_uri) DO NOTHING
            """, (
                skill_uri,
                f"critical:{next_id + idx:04d}",
                skill_name,
                skill_name,  # Tech terms don't translate
                description,
                description,  # Keep bilingual
                'tier0_critical',  # Higher priority than tier1
                category,
                'Modern Tech Practices',
                True
            ))

            if cursor.rowcount > 0:
                inserted += 1
                print(f"   ✅ {skill_name}")
            else:
                skipped += 1
                print(f"   ⏭️  {skill_name} (already exists)")

        except Exception as e:
            print(f"   ❌ Error with '{skill_name}': {e}")

    conn.commit()

    # Final stats
    cursor.execute("""
        SELECT COUNT(*) FROM esco_skills
        WHERE skill_uri LIKE 'manual:%'
    """)
    after_count = cursor.fetchone()[0]

    print(f"\n{'='*80}")
    print("✅ COMPLETED")
    print("="*80)
    print(f"   Inserted: {inserted}")
    print(f"   Skipped:  {skipped}")
    print(f"   Before:   {before_count}")
    print(f"   After:    {after_count}")
    print()

    # Show breakdown by category
    print("📋 Skills by Category:")
    cursor.execute("""
        SELECT skill_group, COUNT(*)
        FROM esco_skills
        WHERE skill_uri LIKE 'manual:critical:%'
        GROUP BY skill_group
        ORDER BY COUNT(*) DESC
    """)

    for category, count in cursor.fetchall():
        print(f"   {category:<35} {count:>2} skills")

    cursor.close()
    conn.close()

    print()

if __name__ == '__main__':
    add_missing_skills()
