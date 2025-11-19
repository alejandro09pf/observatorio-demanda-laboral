# Observatorio de Demanda Laboral para América Latina

Sistema automatizado para monitoreo y análisis de demanda de habilidades técnicas en el mercado laboral latinoamericano mediante web scraping, procesamiento de lenguaje natural y análisis de datos.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Autores:** Nicolás Francisco Camacho Alarcón y Alejandro Pinzón
**Institución:** Pontificia Universidad Javeriana, Colombia
**Año:** 2025

---

## Índice

- [Sobre el Proyecto](#sobre-el-proyecto)
- [Arquitectura](#arquitectura)
- [Prerequisitos](#prerequisitos)
- [Instalación](#instalación)
- [Uso del Sistema](#uso-del-sistema)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Troubleshooting](#troubleshooting)
- [Documentación](#documentación)
- [Licencia](#licencia)

---

## Sobre el Proyecto

### Problema

Identificar tendencias y demandas de habilidades técnicas en el mercado laboral latinoamericano es complejo debido a la fragmentación de fuentes de información y la falta de herramientas automatizadas de análisis.

### Solución

Sistema integral que:
- Extrae ofertas laborales de portales principales de empleo
- Identifica y normaliza habilidades técnicas mediante NLP
- Genera embeddings vectoriales para análisis semántico
- Agrupa habilidades en clusters significativos
- Proporciona visualizaciones y reportes

### Alcance

**Países:**
- Colombia (CO)
- México (MX)
- Argentina (AR)

**Portales de empleo:**
- Computrabajo
- Bumeran
- ElEmpleo
- OccMundial
- ZonaJobs
- Magneto

### Estado del Proyecto

**Componentes funcionales:**
- ✓ Web scraping (Scrapy + Selenium)
- ✓ Base de datos PostgreSQL con pgvector
- ✓ Extracción de habilidades (NER + Regex + ESCO)
- ✓ API REST (FastAPI)
- ✓ Sistema de workers (Celery)
- ✓ Frontend web (Next.js)
- ✓ Orquestador CLI

**En desarrollo:**
- Procesamiento LLM para normalización avanzada
- Embeddings semánticos (E5 Multilingual)
- Clustering (HDBSCAN + UMAP)
- Visualizaciones interactivas

---

## Arquitectura

### Pipeline de Datos

El sistema implementa un pipeline de 8 etapas:

```
1. SCRAPING → 2. EXTRACCIÓN → 3. PROCESAMIENTO LLM → 4. EMBEDDINGS
                                                             ↓
8. REPORTES ← 7. VISUALIZACIÓN ← 6. CLUSTERING ← 5. REDUCCIÓN DIMENSIONALIDAD
```

**1. Scraping:** Extracción de ofertas laborales con Scrapy/Selenium
**2. Extracción:** Identificación de habilidades con NER + Regex + ESCO
**3. Procesamiento LLM:** Normalización y categorización (en desarrollo)
**4. Embeddings:** Generación de vectores semánticos con E5 (en desarrollo)
**5. Reducción:** UMAP para proyección dimensional (en desarrollo)
**6. Clustering:** Agrupación con HDBSCAN (en desarrollo)
**7. Visualización:** Gráficos y dashboards (en desarrollo)
**8. Reportes:** Generación de análisis en PDF/CSV (en desarrollo)

### Arquitectura de Servicios

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ PostgreSQL  │────▶│   FastAPI   │────▶│  Next.js    │
│   + pgvector│     │     API     │     │  Frontend   │
└─────────────┘     └─────────────┘     └─────────────┘
       │                    │
       │            ┌───────┴───────┐
       │            ▼               ▼
       │      ┌──────────┐   ┌──────────┐
       └─────▶│  Celery  │   │  Celery  │
              │  Workers │   │   Beat   │
              └──────────┘   └──────────┘
                     │
                     ▼
              ┌──────────┐
              │  Redis   │
              └──────────┘
```

**Componentes:**

- **PostgreSQL:** Base de datos principal con extensión pgvector para búsqueda semántica
- **Redis:** Message broker para Celery y cache
- **FastAPI:** API REST para acceso a datos y operaciones
- **Celery Workers:** Procesamiento asíncrono de tareas (scraping, extracción, clustering)
- **Celery Beat:** Scheduler para ejecución automática periódica
- **Next.js:** Interfaz web para visualización y administración
- **Orquestador CLI:** Interfaz de línea de comandos para control del sistema

---

## Prerequisitos

**Software requerido:**

- Python 3.10 o superior
- Docker y Docker Compose
- Git
- 8GB RAM mínimo (16GB recomendado para procesamiento LLM)

**Opcional para desarrollo:**

- Node.js 18+ (si se modifica el frontend)
- PostgreSQL 15+ local (alternativa a Docker)

---

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/observatorio-demanda-laboral.git
cd observatorio-demanda-laboral
```

### 2. Crear entorno virtual de Python

**macOS/Linux:**
```bash
python -m venv venv
source venv/bin/activate
```

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar con tus configuraciones
nano .env
```

Variables principales:
```bash
# Database
DATABASE_URL=postgresql://labor_user:123456@localhost:5433/labor_observatory

# Scraping
SCRAPER_CONCURRENT_REQUESTS=16
SCRAPER_DOWNLOAD_DELAY=1.0

# API (si usas OpenAI como fallback)
OPENAI_API_KEY=tu_api_key_aqui  # Opcional
```

### 5. Levantar infraestructura con Docker

```bash
# Levantar todo el sistema
docker-compose up -d

# O solo base de datos y Redis (para desarrollo)
docker-compose up -d postgres redis
```

Verificar que los servicios estén corriendo:
```bash
docker-compose ps
```

### 6. Inicializar base de datos

Las migraciones se ejecutan automáticamente al levantar PostgreSQL. Para importar la taxonomía ESCO:

```bash
# Con venv activado
python scripts/import_real_esco.py
```

### 7. Verificar instalación

```bash
# Estado del sistema
python -m src.orchestrator status

# Verificar conexión a BD
python -m src.orchestrator health
```

**Acceso a servicios:**

- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs
- Flower (monitoring): http://localhost:5555 (si está activado)

---

## Uso del Sistema

### Flujo de Trabajo Típico

```bash
# 1. Activar entorno virtual (siempre necesario)
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# 2. Levantar infraestructura (si no está corriendo)
docker-compose up -d postgres redis

# 3. Ejecutar comandos del orquestador
python -m src.orchestrator [comando] [opciones]
```

### Orquestador CLI

El orquestador es la herramienta principal para controlar el sistema.

**Comandos básicos:**

```bash
# Ver ayuda general
python -m src.orchestrator --help

# Estado del sistema
python -m src.orchestrator status

# Listar scrapers disponibles
python -m src.orchestrator list-spiders

# Estado del sistema de automatización
python -m src.orchestrator automation-status

# Health check
python -m src.orchestrator health
```

**Scraping de ofertas laborales:**

```bash
# Ejecutar un scraper específico (una vez)
python -m src.orchestrator run-once bumeran CO --limit 50 --max-pages 5

# Ejecutar múltiples scrapers para un país
python -m src.orchestrator run "computrabajo,elempleo" CO --limit 100

# Scraping con modo verbose
python -m src.orchestrator run-once occmundial MX -v

# Limitar páginas y jobs por página
python -m src.orchestrator run-once computrabajo AR --max-pages 10 --limit 20
```

**Procesamiento de datos:**

```bash
# Procesar jobs pendientes (extracción de habilidades)
python -m src.orchestrator process-jobs

# Procesar con límite
python -m src.orchestrator process-jobs --limit 100
```

**Sistema de automatización:**

```bash
# Iniciar sistema de scrapers automáticos
python -m src.orchestrator start-automation

# Ver trabajos programados
python -m src.orchestrator list-jobs

# Forzar ejecución de un job específico
python -m src.orchestrator force-job bumeran_CO_cron
```

### API REST

La API proporciona acceso programático a los datos y funcionalidades.

**Endpoints principales:**

```bash
# Estadísticas generales
GET http://localhost:8000/api/stats

# Listar jobs
GET http://localhost:8000/api/jobs?country=CO&limit=50

# Obtener skills
GET http://localhost:8000/api/skills?country=MX

# Clusters (cuando esté implementado)
GET http://localhost:8000/api/clusters

# Documentación interactiva
http://localhost:8000/api/docs
```

**Ejemplo con curl:**

```bash
curl http://localhost:8000/api/stats | jq
```

### Frontend Web

Acceder a http://localhost:3000

**Funcionalidades:**

- Dashboard con estadísticas generales
- Explorador de ofertas laborales
- Visualización de habilidades extraídas
- Panel de administración
- (En desarrollo) Visualización de clusters

### Workers y Celery

**Monitorear workers:**

```bash
# Ver logs de workers
docker-compose logs -f celery_worker

# Ver logs de scheduler
docker-compose logs -f celery_beat
```

**Acceder a Flower (monitoring UI):**

```bash
# Levantar con perfil de monitoring
docker-compose --profile with-monitoring up -d

# Acceder a http://localhost:5555
```

**Escalar workers:**

```bash
# Aumentar número de workers
docker-compose up -d --scale celery_worker=4
```

### Backups

**Backup de base de datos:**

```bash
# Dump completo
docker-compose exec postgres pg_dump -U labor_user labor_observatory > backup_$(date +%Y%m%d).sql

# Backup comprimido
docker-compose exec postgres pg_dump -U labor_user labor_observatory | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Restaurar backup:**

```bash
# Desde dump SQL
docker-compose exec -T postgres psql -U labor_user labor_observatory < backup_20250118.sql

# Desde dump comprimido
gunzip -c backup_20250118.sql.gz | docker-compose exec -T postgres psql -U labor_user labor_observatory
```

### Logs

**Ubicación de logs:**

- Sistema: `logs/labor_observatory.log`
- Scraping masivo: `logs/mass_scraping.log`
- Docker: `docker-compose logs [servicio]`

**Ver logs en tiempo real:**

```bash
# Todos los servicios
docker-compose logs -f

# Servicio específico
docker-compose logs -f api
docker-compose logs -f celery_worker
```

---

## Estructura del Proyecto

```
observatorio-demanda-laboral/
├── src/                          # Código fuente principal
│   ├── scraper/                  # Módulo de web scraping
│   │   ├── spiders/             # Spiders de Scrapy
│   │   ├── settings.py          # Configuración de Scrapy
│   │   └── middlewares.py       # Middlewares personalizados
│   ├── extractor/               # Extracción de habilidades
│   │   ├── ner_extractor.py    # NER con spaCy
│   │   ├── regex_extractor.py  # Extractor basado en regexes
│   │   └── esco_matcher.py     # Matching con taxonomía ESCO
│   ├── llm_processor/           # Procesamiento con LLM (en desarrollo)
│   ├── embedder/                # Generación de embeddings (en desarrollo)
│   ├── analyzer/                # Clustering y análisis (en desarrollo)
│   ├── database/                # Operaciones de base de datos
│   │   ├── operations.py       # CRUD operations
│   │   └── migrations/         # SQL migrations
│   ├── api/                     # API REST con FastAPI
│   │   ├── main.py             # Aplicación principal
│   │   └── routes/             # Endpoints
│   ├── tasks/                   # Tareas de Celery
│   │   ├── scraping_tasks.py
│   │   ├── extraction_tasks.py
│   │   └── clustering_tasks.py
│   ├── automation/              # Sistema de automatización
│   └── orchestrator.py          # CLI principal
├── frontend/                     # Frontend Next.js
│   ├── app/                     # Páginas de la aplicación
│   ├── components/              # Componentes React
│   └── lib/                     # Utilidades
├── config/                       # Archivos de configuración
│   ├── esco_config.yaml
│   └── user_agents.txt
├── data/                         # Datos y recursos
│   ├── esco/                    # Taxonomía ESCO
│   ├── backups/                 # Backups de BD
│   └── models/                  # Modelos de ML (ignorado)
├── docs/                         # Documentación técnica
├── scripts/                      # Scripts auxiliares
├── tests/                        # Tests unitarios e integración
├── logs/                         # Archivos de log (ignorado)
├── outputs/                      # Resultados y reportes (ignorado)
├── docker-compose.yml           # Orquestación de servicios
├── Dockerfile.api               # Dockerfile para API
├── Dockerfile.worker            # Dockerfile para workers
├── requirements.txt             # Dependencias Python
├── .env.example                 # Plantilla de variables de entorno
└── README.md                    # Este archivo
```

---

## Troubleshooting

### Error: "Connection refused" a PostgreSQL

**Causa:** PostgreSQL no está corriendo o no es accesible.

**Solución:**
```bash
# Verificar que Docker esté corriendo
docker-compose ps

# Si no hay contenedores, levantar servicios
docker-compose up -d postgres redis

# Verificar logs de PostgreSQL
docker-compose logs postgres
```

### Error: Puerto ya en uso (8000, 3000, 5433)

**Causa:** Otro proceso está usando el puerto.

**Solución:**
```bash
# macOS/Linux - Ver qué proceso usa el puerto
lsof -i :8000
lsof -i :3000

# Matar proceso
kill -9 <PID>

# Windows - Ver procesos
netstat -ano | findstr :8000

# Matar proceso
taskkill /PID <PID> /F
```

### Error: Módulo no encontrado (ModuleNotFoundError)

**Causa:** El entorno virtual no está activado o las dependencias no están instaladas.

**Solución:**
```bash
# Activar venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: Scraper falla o no encuentra elementos

**Causa:** El sitio web cambió su estructura o detectó bot.

**Solución:**
```bash
# Ejecutar con verbose para ver detalles
python -m src.orchestrator run-once [spider] [country] -v

# Revisar logs
tail -f logs/labor_observatory.log
```

### Error: Base de datos sin taxonomía ESCO

**Causa:** No se importó la taxonomía ESCO.

**Solución:**
```bash
python scripts/import_real_esco.py
```

### Frontend no conecta con API

**Causa:** URL de API incorrecta o API no está corriendo.

**Solución:**
```bash
# Verificar que API esté corriendo
curl http://localhost:8000/api/stats

# Si usas Docker, verificar variable de entorno en frontend
# En docker-compose.yml debe estar:
# NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Workers de Celery no procesan tareas

**Causa:** Redis no está corriendo o workers están detenidos.

**Solución:**
```bash
# Verificar Redis
docker-compose ps redis

# Reiniciar workers
docker-compose restart celery_worker celery_beat

# Ver logs
docker-compose logs -f celery_worker
```

---

## Documentación

Documentación técnica adicional disponible en `docs/`:

- **[COMANDOS_UTILES.md](docs/COMANDOS_UTILES.md)** - Cheatsheet de comandos del orquestador
- **[architecture.md](docs/architecture.md)** - Arquitectura detallada del sistema
- **[technical-specification.md](docs/technical-specification.md)** - Especificación técnica completa
- **[implementation-guide.md](docs/implementation-guide.md)** - Guía de implementación de componentes
- **[data-flow-reference.md](docs/data-flow-reference.md)** - Flujo de datos entre módulos
- **[api_reference.md](docs/api_reference.md)** - Referencia de API

---

## Agradecimientos

Este proyecto utiliza y se beneficia de las siguientes tecnologías y recursos:

- **ESCO** - European Skills, Competences, Qualifications and Occupations
- **spaCy** - Procesamiento de lenguaje natural
- **Hugging Face** - Modelos de embeddings y transformers
- **Scrapy** - Framework de web scraping
- **PostgreSQL + pgvector** - Base de datos vectorial
- **FastAPI** - Framework de API REST
- **Celery** - Sistema de tareas distribuidas
- **Next.js** - Framework de React

---

## Licencia

Este proyecto está licenciado bajo la Licencia MIT. Ver archivo [LICENSE](LICENSE) para más detalles.

Copyright (c) 2025 Nicolás Francisco Camacho Alarcón y Alejandro Pinzón
