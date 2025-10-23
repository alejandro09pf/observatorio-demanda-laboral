#!/usr/bin/env python3
"""
Add manually curated tech skills (Tier 1 + Tier 2) to esco_skills table.

This script adds 95 critical and important tech skills that are common
in LatAm tech jobs but missing from O*NET dataset.
"""

import psycopg2
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.settings import get_settings


# TIER 1: CRITICAL (66 skills) - Very common in LatAm tech jobs
TIER1_SKILLS = [
    # Frontend Frameworks & Libraries (11)
    ('Next.js', 'Framework React con SSR/SSG para producción', 'Frontend Frameworks'),
    ('Nuxt.js', 'Framework Vue.js con SSR/SSG', 'Frontend Frameworks'),
    ('Svelte', 'Framework JavaScript reactivo compilado', 'Frontend Frameworks'),
    ('Tailwind CSS', 'Framework CSS utility-first', 'Frontend Tools'),
    ('Redux', 'State management para React', 'Frontend Libraries'),
    ('Material-UI', 'React component library Material Design', 'Frontend Libraries'),
    ('Vite', 'Build tool y dev server moderno', 'Frontend Tools'),
    ('Webpack', 'Module bundler para JavaScript', 'Frontend Tools'),
    ('Remix', 'Framework React full-stack moderno', 'Frontend Frameworks'),
    ('Shadcn/ui', 'Component library moderna para React', 'Frontend Libraries'),
    ('Zustand', 'State management ligero para React', 'Frontend Libraries'),

    # Backend Frameworks (8)
    ('FastAPI', 'Framework Python moderno para APIs', 'Backend Frameworks'),
    ('Flask', 'Microframework Python para web', 'Backend Frameworks'),
    ('Express.js', 'Framework web minimalista Node.js', 'Backend Frameworks'),
    ('NestJS', 'Framework Node.js empresarial progresivo', 'Backend Frameworks'),
    ('Laravel', 'Framework PHP full-stack', 'Backend Frameworks'),
    ('Ruby on Rails', 'Framework web Ruby MVC', 'Backend Frameworks'),
    ('Prisma', 'ORM moderno para Node.js/TypeScript', 'Backend Tools'),
    ('Sequelize', 'ORM tradicional para Node.js', 'Backend Tools'),

    # Mobile Development (5)
    ('React Native', 'Framework móvil multiplataforma con React', 'Mobile Development'),
    ('Flutter', 'Framework móvil multiplataforma de Google', 'Mobile Development'),
    ('Kotlin', 'Lenguaje de programación oficial Android', 'Mobile Development'),
    ('Expo', 'Plataforma y toolchain para React Native', 'Mobile Development'),
    ('Ionic', 'Framework móvil híbrido', 'Mobile Development'),

    # Cloud Platforms & Services (7)
    ('AWS Lambda', 'Servicio serverless computing AWS', 'Cloud Services'),
    ('Vercel', 'Plataforma hosting para frontend apps', 'Cloud Platforms'),
    ('Heroku', 'Platform as a Service (PaaS)', 'Cloud Platforms'),
    ('Netlify', 'Plataforma hosting JAMstack', 'Cloud Platforms'),
    ('Firebase', 'Backend as a Service de Google', 'Cloud Services'),
    ('Supabase', 'Alternativa open-source a Firebase', 'Cloud Services'),
    ('Cloudflare', 'CDN y servicios edge computing', 'Cloud Services'),

    # DevOps & CI/CD (5)
    ('GitHub Actions', 'CI/CD integrado con GitHub', 'DevOps Tools'),
    ('Nginx', 'Web server y reverse proxy', 'Infrastructure'),
    ('CircleCI', 'Plataforma de integración continua', 'DevOps Tools'),
    ('GitLab CI/CD', 'Sistema CI/CD integrado GitLab', 'DevOps Tools'),
    ('Helm', 'Package manager para Kubernetes', 'DevOps Tools'),

    # Testing Frameworks (6)
    ('Jest', 'Framework testing JavaScript', 'Testing'),
    ('Pytest', 'Framework testing Python', 'Testing'),
    ('Cypress', 'Framework E2E testing moderno', 'Testing'),
    ('Playwright', 'Framework E2E testing de Microsoft', 'Testing'),
    ('Vitest', 'Framework testing rápido para Vite', 'Testing'),
    ('React Testing Library', 'Testing library para React', 'Testing'),

    # Data Science & ML (7)
    ('Pandas', 'Biblioteca Python análisis de datos', 'Data Science'),
    ('NumPy', 'Biblioteca Python computación científica', 'Data Science'),
    ('Scikit-learn', 'Biblioteca machine learning Python', 'AI/ML'),
    ('Jupyter Notebook', 'Entorno interactivo data science', 'Data Science'),
    ('Keras', 'API high-level para deep learning', 'AI/ML'),
    ('LangChain', 'Framework para aplicaciones LLM', 'AI/ML'),
    ('Hugging Face', 'Plataforma y biblioteca Transformers', 'AI/ML'),

    # API & Backend Tools (3)
    ('REST API', 'Estilo arquitectónico para APIs web', 'API Design'),
    ('Postman', 'Plataforma para testing APIs', 'API Tools'),
    ('tRPC', 'TypeSafe APIs end-to-end', 'API Tools'),
]

# TIER 2: IMPORTANT (29 skills) - Common in senior/specialized jobs
TIER2_SKILLS = [
    # Monitoring & Observability (5)
    ('Grafana', 'Plataforma visualización y monitoring', 'Monitoring'),
    ('Prometheus', 'Sistema monitoring y alerting', 'Monitoring'),
    ('Sentry', 'Error tracking y performance monitoring', 'Monitoring'),
    ('Datadog', 'Plataforma APM y monitoring', 'Monitoring'),
    ('New Relic', 'Plataforma APM observability', 'Monitoring'),

    # Message Queues & Streaming (3)
    ('RabbitMQ', 'Message broker open-source', 'Message Queues'),
    ('Apache Pulsar', 'Sistema mensajería distribuido', 'Message Queues'),
    ('NATS', 'Sistema mensajería cloud-native', 'Message Queues'),

    # Authentication & Security (6)
    ('Auth0', 'Plataforma autenticación como servicio', 'Authentication'),
    ('JWT', 'JSON Web Tokens para autenticación', 'Authentication'),
    ('OAuth 2.0', 'Protocolo de autorización', 'Authentication'),
    ('Keycloak', 'Gestión identidad y acceso open-source', 'Authentication'),
    ('Clerk', 'Autenticación moderna para apps', 'Authentication'),
    ('OWASP', 'Estándares seguridad aplicaciones web', 'Security'),

    # CMS & E-commerce (7)
    ('Strapi', 'Headless CMS open-source', 'Content Management'),
    ('Contentful', 'Headless CMS como servicio', 'Content Management'),
    ('Sanity', 'Headless CMS estructurado', 'Content Management'),
    ('Shopify', 'Plataforma e-commerce', 'E-commerce'),
    ('WooCommerce', 'Plugin e-commerce WordPress', 'E-commerce'),
    ('Magento', 'Plataforma e-commerce empresarial', 'E-commerce'),
    ('Stripe', 'Plataforma procesamiento pagos online', 'Payment Processing'),

    # Programming Languages (2)
    ('Rust', 'Lenguaje programación systems seguro', 'Programming Languages'),
    ('Dart', 'Lenguaje programación para Flutter', 'Programming Languages'),

    # Data Engineering (4)
    ('Apache Airflow', 'Plataforma orquestación workflows', 'Data Engineering'),
    ('dbt', 'Data build tool transformaciones', 'Data Engineering'),
    ('Snowflake', 'Cloud data warehouse', 'Data Engineering'),
    ('BigQuery', 'Data warehouse Google Cloud', 'Data Engineering'),
]


def add_manual_skills():
    """Add manually curated tech skills to esco_skills table."""

    settings = get_settings()

    # Normalize database URL
    db_url = settings.database_url
    if db_url.startswith('postgresql://'):
        db_url = db_url.replace('postgresql://', 'postgres://')

    print("=" * 70)
    print("MANUAL TECH SKILLS IMPORT (TIER 1 + TIER 2)")
    print("=" * 70)

    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()

    # Check current count
    cursor.execute("SELECT COUNT(*) FROM esco_skills")
    before_count = cursor.fetchone()[0]
    print(f"📊 Current esco_skills count: {before_count:,}")
    print()

    # Combine all skills
    all_skills = TIER1_SKILLS + TIER2_SKILLS

    print(f"📋 Skills to import:")
    print(f"   Tier 1 (Critical):  {len(TIER1_SKILLS):,} skills")
    print(f"   Tier 2 (Important): {len(TIER2_SKILLS):,} skills")
    print(f"   Total:              {len(all_skills):,} skills")
    print()

    inserted = 0
    skipped = 0
    errors = 0

    print("🚀 Starting import...")
    print()

    for idx, (skill_name, description_es, category) in enumerate(all_skills):
        skill_uri = f"manual:curated:{idx:04d}"

        # Determine tier
        tier = 'tier1_critical' if idx < len(TIER1_SKILLS) else 'tier2_important'

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
                f"curated:{idx:04d}",
                skill_name,
                skill_name,  # Technical names don't translate
                description_es,
                description_es.replace('Tecnología:', 'Technology:'),  # Simple translation
                tier,
                category,
                'IT & Software Development',
                True
            ))

            # Check if actually inserted (not a duplicate)
            if cursor.rowcount > 0:
                inserted += 1

                if inserted % 25 == 0:
                    print(f"   ✓ Inserted {inserted} skills...")
                    conn.commit()
            else:
                skipped += 1

        except Exception as e:
            errors += 1
            print(f"   ❌ Error with '{skill_name}': {e}")
            continue

    conn.commit()

    # Final stats
    cursor.execute("SELECT COUNT(*) FROM esco_skills")
    after_count = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM esco_skills
        WHERE skill_type IN ('tier1_critical', 'tier2_important')
    """)
    manual_count = cursor.fetchone()[0]

    print()
    print("=" * 70)
    print("✅ IMPORT COMPLETED")
    print("=" * 70)
    print(f"   Inserted:       {inserted:,}")
    print(f"   Skipped:        {skipped:,} (duplicates)")
    print(f"   Errors:         {errors:,}")
    print()
    print(f"📊 Database Stats:")
    print(f"   Before:         {before_count:,}")
    print(f"   After:          {after_count:,}")
    print(f"   Manual skills:  {manual_count:,}")
    print(f"   O*NET skills:   152")
    print(f"   ESCO skills:    13,939")
    print()

    # Show breakdown by category
    print("📋 Skills by Category:")
    cursor.execute("""
        SELECT skill_group, COUNT(*) as count
        FROM esco_skills
        WHERE skill_type IN ('tier1_critical', 'tier2_important')
        GROUP BY skill_group
        ORDER BY count DESC
        LIMIT 15
    """)

    for category, count in cursor.fetchall():
        print(f"   {category:<30} {count:>3} skills")

    print()

    # Show sample of imported skills
    print("📋 Sample of imported skills (first 20):")
    cursor.execute("""
        SELECT preferred_label_en, skill_group, skill_type
        FROM esco_skills
        WHERE skill_type IN ('tier1_critical', 'tier2_important')
        ORDER BY skill_uri
        LIMIT 20
    """)

    for label, group, tier in cursor.fetchall():
        marker = "⭐⭐" if tier == 'tier1_critical' else "⭐"
        print(f"   {marker} {label:<25} ({group})")

    cursor.close()
    conn.close()

    print()
    print("✅ Done!")


if __name__ == '__main__':
    add_manual_skills()
