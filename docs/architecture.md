# 🏗️ System Architecture - Labor Market Observatory

> **Arquitectura Híbrida: Microservicios en Capas + Event-Driven + API Gateway + CRISP-DM Pipeline**

## 📋 Table of Contents

- [🎯 System Overview](#-system-overview)
- [🏗️ Patrón Arquitectónico](#️-patrón-arquitectónico)
- [🔧 Los 7 Servicios](#-los-7-servicios)
- [📊 Ciclo Completo de Datos](#-ciclo-completo-de-datos)
- [🔌 Pub/Sub vs Request/Response](#-pubsub-vs-requestresponse)
- [🗄️ Database Design](#️-database-design)
- [🚀 Performance & Scalability](#-performance--scalability)
- [🔒 Security & Compliance](#-security--compliance)

## 🎯 System Overview

El **Labor Market Observatory** implementa una **Arquitectura Híbrida** que combina lo mejor de tres patrones arquitectónicos para crear un sistema escalable, asíncrono y eficiente para analizar la demanda de habilidades técnicas en mercados laborales latinoamericanos.

### **Arquitectura Híbrida**

```
┌─────────────────────────────────────────────────────────────────┐
│           LABOR MARKET OBSERVATORY - ARQUITECTURA HÍBRIDA       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  PATRÓN 1: API Gateway (Nginx)                           │  │
│  │  • Punto único de entrada                                │  │
│  │  • Routing, SSL, Load Balancing                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            │                                    │
│           ┌────────────────┴────────────────┐                  │
│           ▼                                 ▼                  │
│  ┌─────────────────┐              ┌─────────────────┐          │
│  │  PATRÓN 2:      │              │  PATRÓN 3:      │          │
│  │  Microservicios │              │  Event-Driven   │          │
│  │  en Capas       │              │  Architecture   │          │
│  │                 │              │                 │          │
│  │  • Frontend     │              │  • Celery Beat  │          │
│  │  • API REST     │              │  • Redis Queue  │          │
│  │  • PostgreSQL   │              │  • Workers      │          │
│  │                 │              │  • Pub/Sub      │          │
│  │  Request/       │              │  Asíncrono      │          │
│  │  Response       │              │  Desacoplado    │          │
│  └─────────────────┘              └─────────────────┘          │
│           │                                 │                  │
│           └────────────────┬────────────────┘                  │
│                            ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  CRISP-DM Pipeline (Procesamiento de Datos)              │  │
│  │  Scraping → Cleaning → Extraction → Enhancement →        │  │
│  │  Embedding → Clustering → Visualization                  │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🏗️ Patrón Arquitectónico

### **Arquitectura Híbrida que Combina:**

#### **1. Microservicios en Capas** (para Request/Response)

**Uso**: Operaciones síncronas que necesitan respuesta inmediata

**Componentes**:
- **Nginx** → Routing y load balancing
- **Frontend (Next.js)** → Interfaz de usuario
- **API (FastAPI)** → Lógica de negocio
- **PostgreSQL** → Persistencia de datos

**Casos de uso**:
- ✅ GET /api/jobs?limit=10 (consulta rápida)
- ✅ POST /api/jobs/clean (limpieza manual <5s)
- ✅ GET /api/stats (estadísticas)
- ✅ GET /api/tasks/abc123 (polling de estado)

**Patrón**: Request → Response inmediata

---

#### **2. Event-Driven Architecture** (para Procesamiento Asíncrono)

**Uso**: Operaciones largas (>5 segundos) que se procesan en background

**Componentes**:
- **Celery Beat** → Scheduler de tareas automáticas
- **Redis Queue** → Cola de mensajes (Pub/Sub)
- **Celery Workers** → Procesadores distribuidos

**Casos de uso**:
- ✅ Scraping automático cada 6 horas
- ✅ POST /api/extract/batch (100+ jobs)
- ✅ POST /api/jobs/clean/batch (10,000 jobs)
- ✅ POST /api/cluster (procesamiento pesado)

**Patrón**: Publish (API/Beat) → Queue (Redis) → Subscribe (Workers)

---

#### **3. API Gateway Pattern** (Nginx)

**Uso**: Punto único de entrada para todas las peticiones

**Funciones**:
- Routing: `/` → Frontend, `/api/*` → API
- SSL/TLS termination
- Compresión gzip
- Rate limiting
- Logging centralizado
- Load balancing (futuro: múltiples instancias de API)

---

## 🔧 Los 7 Servicios

### **1. NGINX - El Portero (API Gateway)**

**Rol**: Punto de entrada único

**Puerto**: 80 (producción) o directo a 3000/8000 (desarrollo)

**Funciones**:
- Recibe TODAS las peticiones de usuarios
- Enruta a Frontend (/) o API (/api/*)
- Compresión, logging, SSL, load balancing

**Configuración**:
```nginx
server {
    listen 80;

    # Frontend
    location / {
        proxy_pass http://frontend:3000;
    }

    # API
    location /api/ {
        proxy_pass http://api:8000;
    }
}
```

**Docker**: `nginx:alpine` (opcional, perfil `with-nginx`)

---

### **2. Frontend (Next.js) - La Cara**

**Rol**: Interfaz de usuario

**Puerto**: 3000 (accesible via nginx en `/`)

**Funciones**:
- Renderiza páginas web (SSR + React)
- Muestra dashboards, estadísticas, clusters
- Llama a la API REST
- Polling para monitorear tareas asíncronas

**Patrón de Comunicación**:
```
Request/Response SÍNCRONO:
Frontend → API: GET /api/jobs?country=CO&limit=10
API → Frontend: {jobs: [...], total: 150}

Request/Response ASÍNCRONO (Polling):
Frontend → API: POST /api/extract/batch {job_ids: [1,2,3]}
API → Frontend: {task_id: "xyz", status: "PENDING"}
[Polling cada 3s]
Frontend → API: GET /api/tasks/xyz
API → Frontend: {status: "SUCCESS", completed: 100}
```

**Docker**: Custom build (Dockerfile frontend)

---

### **3. API (FastAPI) - El Cerebro**

**Rol**: Lógica de negocio y coordinación

**Puerto**: 8000 (accesible via nginx en `/api/*`)

**Funciones**:
- **Request/Response**: Consultas rápidas (GET /jobs, /stats)
- **Task Publisher**: Publica tareas asíncronas a Redis
- **Task Monitor**: Consulta estado de tareas en Redis
- Validación de datos (Pydantic)
- Autenticación/autorización (futuro)

**Rutas principales**:
- `/api/jobs` - CRUD de trabajos
- `/api/stats` - Estadísticas y métricas
- `/api/skills` - Habilidades extraídas
- `/api/clusters` - Resultados de clustering
- `/api/admin/scrape` - Trigger scraping manual
- `/api/extract/batch` - Procesamiento batch
- `/api/tasks/{task_id}` - Estado de tareas

**Patrón Dual**:

**SÍNCRONO** (Request/Response):
```python
@app.get("/api/jobs")
async def get_jobs(country: str, limit: int = 10):
    # Consulta directa a PostgreSQL
    jobs = db.query(RawJob).filter_by(country=country).limit(limit).all()
    return {"jobs": jobs, "total": len(jobs)}
```

**ASÍNCRONO** (Pub/Sub):
```python
@app.post("/api/extract/batch")
async def extract_batch(job_ids: List[int], pipeline: str):
    # Publica 100 tareas a Redis (Pub/Sub)
    task_ids = []
    for job_id in job_ids:
        task = extract_skills_llm.delay(job_id, pipeline)
        task_ids.append(task.id)

    # Responde INMEDIATAMENTE (no espera)
    return {
        "batch_id": "batch_abc",
        "task_ids": task_ids,
        "status": "QUEUED",
        "total": len(job_ids)
    }
```

**Docker**: Custom build (Dockerfile.api)

---

### **4. PostgreSQL - La Memoria**

**Rol**: Persistencia de datos

**Puerto**: 5433 (host) → 5432 (container)

**Funciones**:
- Almacena TODOS los datos (raw_jobs, extracted_skills, enhanced_skills, etc.)
- Extensión pgvector para embeddings
- ACID compliance
- Consultas SQL optimizadas con índices

**Tablas principales**:
- `raw_jobs` - Jobs scrapeados (is_processed=FALSE hasta que se procesen)
- `cleaned_jobs` - Jobs limpios (is_usable, combined_text)
- `extracted_skills` - Habilidades extraídas (NER/Regex/ESCO)
- `enhanced_skills` - Habilidades normalizadas con LLM
- `skill_embeddings` - Vectores para clustering (vector(768))
- `esco_taxonomy` - Taxonomía ESCO (13,000+ skills)

**Docker**: `postgres:15` + Volume `postgres_data`

---

### **5. Redis - El Mensajero**

**Rol**: Message Broker + Result Backend + Pub/Sub

**Puerto**: 6379

**3 Bases de Datos Separadas**:

**DB 0 - Celery Broker (Task Queue)**:
```redis
# API publica tarea
LPUSH queue:celery '{"task": "extract_skills_llm", "args": [1]}'

# Worker consume tarea (bloqueante)
BRPOP queue:celery 0  → {"task": "extract_skills_llm", "args": [1]}
```

**DB 1 - Celery Result Backend**:
```redis
# Worker guarda resultado
SET result:task_abc123 '{"status": "SUCCESS", "result": {...}}'
EXPIRE result:task_abc123 86400  # 24 horas

# API consulta estado (polling desde frontend)
GET result:task_abc123 → {"status": "SUCCESS", "result": {...}}
```

**DB 2 - Pub/Sub Event Bus** (futuro):
```redis
# Para eventos en tiempo real (actualmente no usado intensivamente)
PUBLISH labor_observatory:jobs_scraped '{"count": 150}'
```

**Docker**: `redis:7-alpine` + Volume `redis_data`

---

### **6. Celery Workers - Los Trabajadores**

**Rol**: Procesadores distribuidos (workers)

**Funciones**:
- **Consumen** tareas de Redis Queue (BRPOP)
- **Ejecutan** procesamiento pesado:
  - Scraping (Scrapy)
  - Extracción (NER, Regex, ESCO)
  - Enhancement (LLM - Gemma 3B)
  - Clustering (UMAP + HDBSCAN)
- **Publican** resultados a Redis Result Backend

**Escalabilidad**:
```bash
# Escalar horizontalmente
docker-compose up -d --scale celery_worker=4

# 4 workers procesan en paralelo:
Worker 1: procesa job_id=1
Worker 2: procesa job_id=2
Worker 3: procesa job_id=3
Worker 4: procesa job_id=4
# Los siguientes jobs esperan en cola
```

**Tareas disponibles** (src/tasks/):
- `scraping_tasks.py`: `run_spider_task`
- `extraction_tasks.py`: `extract_skills_task`
- `enhancement_tasks.py`: `enhance_job_task`
- `clustering_tasks.py`: `run_clustering_task`
- `llm_tasks.py`: `extract_skills_llm` (Pipeline B con LLM)

**Patrón de Trabajo**:
```python
# Worker consume de Redis
task = redis.brpop("queue:celery")  # Bloqueante

# Worker ejecuta
def extract_skills_llm(job_id, pipeline="B"):
    # 1. SELECT de cleaned_jobs
    job = db.query(CleanedJob).filter_by(job_id=job_id).first()

    # 2. Llamada a LLM (Request/Response dentro del worker)
    response = llm.generate(prompt)
    skills = parse_json(response)

    # 3. INSERT en enhanced_skills
    db.bulk_insert(EnhancedSkill, skills)

    # 4. UPDATE raw_jobs
    db.query(RawJob).filter_by(job_id=job_id).update({
        "extraction_status": "completed"
    })

    # 5. Guarda resultado en Redis
    redis.set(f"result:{task_id}", {"status": "SUCCESS"})
```

**Docker**: Custom build (Dockerfile.worker), escalable con `--scale`

---

### **7. Celery Beat - El Despertador**

**Rol**: Scheduler de tareas automáticas (Cron jobs)

**Funciones**:
- Ejecuta tareas según schedule (cada 6 horas, diario, semanal)
- Publica tareas a Redis Queue (no las ejecuta, solo las programa)

**Schedule** (src/tasks/celery_app.py):
```python
celery_app.conf.beat_schedule = {
    # Scraping automático cada 6 horas
    'scraping-co-computrabajo': {
        'task': 'src.tasks.scraping_tasks.run_spider_task',
        'schedule': crontab(hour='*/6'),  # 0, 6, 12, 18
        'args': ('computrabajo', 'CO', 100, 5)
    },

    # Procesamiento batch diario a las 3 AM
    'daily-extraction': {
        'task': 'src.tasks.extraction_tasks.process_pending_batch',
        'schedule': crontab(hour=3, minute=0),
        'args': (500,)  # Procesar 500 jobs pendientes
    },

    # Clustering semanal (Domingo 3 AM)
    'weekly-clustering': {
        'task': 'src.tasks.clustering_tasks.run_clustering_task',
        'schedule': crontab(day_of_week=0, hour=3),
        'args': ('pipeline_b_300_post', 50, None)
    }
}
```

**Funcionamiento**:
```
Beat despierta según schedule
  ↓
Beat PUBLICA tarea a Redis Queue
  LPUSH queue:celery '{"task": "run_spider_task", "args": [...]}'
  ↓
Worker CONSUME y EJECUTA
  BRPOP queue:celery → ejecuta scraping
```

**Docker**: Custom build (Dockerfile.worker), comando `celery beat`

---

## 📊 Ciclo Completo de Datos

### **FASE 1: SCRAPING** ✅ Event-Driven (Pub/Sub)

**Trigger**: Automático (Celery Beat cada 6 horas) o Manual (API)

**Patrón**: **Pub/Sub** (Asíncrono)

**Flujo**:

```
1. TRIGGER AUTOMÁTICO
   Celery Beat (despierta según schedule cada 6h)
     ↓ PUBLICA tarea a Redis

2. REDIS QUEUE (DB 0)
   LPUSH queue:celery {
     "task": "run_spider_task",
     "args": ["computrabajo", "CO", 100, 5]
   }
     ↓ Worker ESCUCHA (Pub/Sub pattern)

3. CELERY WORKER (CONSUME de Redis)
   BRPOP queue:celery → obtiene tarea
     ↓

4. WORKER EJECUTA SCRAPING
   → GET https://computrabajo.com.co/empleos
   → Parsea HTML con Scrapy/BeautifulSoup
   → Extrae por cada job:
      • title, company, location
      • description, requirements
      • url, posted_date
   → Calcula content_hash = SHA256(title+company+description)
     ↓

5. WORKER GUARDA EN POSTGRESQL
   INSERT INTO raw_jobs (
     title, company, description, content_hash,
     is_processed = FALSE,           ← Importante!
     extraction_status = 'pending'   ← Importante!
   )
   ON CONFLICT (content_hash) DO NOTHING  ← Evita duplicados
     ↓

6. WORKER MARCA COMPLETADO
   SET result:task_123 '{"status": "SUCCESS", "jobs_scraped": 150}'
```

**¿Por qué Pub/Sub?**
- ✅ La tarea tarda mucho (5-30 minutos)
- ✅ No necesitas respuesta inmediata
- ✅ Quieres programar automáticamente (Celery Beat)
- ✅ Desacoplamiento: Beat no sabe quién ejecuta

---

### **FASE 2: DETECCIÓN DE NUEVOS JOBS** ❌ NO Pub/Sub

**Patrón**: **NINGUNO** (los datos esperan en DB)

**Estado actual**:
```sql
SELECT job_id, title, company, description
FROM raw_jobs
WHERE is_processed = FALSE
  AND extraction_status = 'pending'
ORDER BY scraped_at DESC;
-- Resultado: 150 jobs esperando ser procesados
```

**¿Por qué NO Pub/Sub?**
- ❌ Los jobs ya están en DB, no hay evento que disparar
- ❌ El usuario decide CUÁNDO procesarlos (no es automático)
- ❌ Es una simple consulta SQL

---

### **FASE 3: LIMPIEZA DE JOBS** ⚖️ Híbrido (Síncrono o Asíncrono)

#### **Opción A: Limpieza Manual** ❌ NO Pub/Sub (Request/Response)

**Uso**: <100 jobs, respuesta rápida (<5s)

**Patrón**: **Request/Response Síncrono**

**Flujo**:
```
Usuario hace clic "Limpiar jobs" en frontend
  ↓ HTTP POST

Frontend → API: POST /api/jobs/clean
  ↓ Consulta directa PostgreSQL

API ejecuta (SÍNCRONAMENTE):
  1. SELECT * FROM raw_jobs WHERE is_usable IS NULL
  2. Para cada job (en memoria):
     • Quita HTML tags (BeautifulSoup)
     • Valida word count > 50
     • Detecta idioma (es/en) con langdetect
     • Si válido: is_usable=TRUE
     • Si inválido: is_usable=FALSE, unusable_reason="too_short"
  3. INSERT INTO cleaned_jobs (
       job_id, title_cleaned, description_cleaned,
       combined_text, combined_word_count
     )
  ↓ Responde INMEDIATAMENTE

API → Frontend: {"cleaned": 95, "rejected": 5, "time_ms": 3200}

Frontend muestra: "✓ 95 jobs limpiados en 3.2s"
```

**¿Por qué NO Pub/Sub?**
- ❌ La tarea es rápida (<5 segundos)
- ❌ Frontend ESPERA la respuesta (muestra resultado inmediato)
- ❌ Pocos jobs (<100), no justifica complejidad de cola

---

#### **Opción B: Limpieza en Batch** ✅ SÍ Pub/Sub (Asíncrono)

**Uso**: >1000 jobs, procesamiento largo (>1 minuto)

**Patrón**: **Pub/Sub** (Asíncrono)

**Flujo**:
```
Usuario hace clic "Limpiar 10,000 jobs"
  ↓ HTTP POST

Frontend → API: POST /api/jobs/clean/batch {count: 10000}
  ↓ PUBLICA tarea a Redis (Pub/Sub!)

API ejecuta:
  task_id = celery.send_task("clean_jobs_batch", args=[job_ids])
  LPUSH queue:celery '{"task": "clean_jobs_batch", "args": [1,2,3...]}'
  ↓

API responde INMEDIATAMENTE (NO espera):
  {
    "task_id": "xyz789",
    "status": "PENDING",
    "total": 10000
  }
  ↓

Frontend muestra:
  "Procesando... 0/10,000"
    ↓ Polling cada 2 segundos
  GET /api/tasks/xyz789 → {"status": "PROGRESS", "completed": 2500}
  Frontend: "Procesando... 2,500/10,000 (25%)"
    ↓

Celery Worker (CONSUME de Redis):
  1. BRPOP queue:celery → obtiene tarea "clean_jobs_batch"
  2. SELECT * FROM raw_jobs WHERE job_id IN (1,2,3...,10000)
  3. Limpia 10,000 jobs (tarda 5 minutos)
     • Procesa en batches de 500
     • Actualiza progreso cada batch:
       redis.set("result:xyz789", {"status": "PROGRESS", "completed": 500})
  4. INSERT batch en cleaned_jobs
  5. Marca completado:
     redis.set("result:xyz789", {"status": "SUCCESS", "cleaned": 9500})
  ↓

Frontend detecta (polling):
  GET /api/tasks/xyz789 → {"status": "SUCCESS", "cleaned": 9500}

Frontend muestra: "✓ 9,500 jobs limpiados correctamente"
```

**¿Por qué SÍ Pub/Sub?**
- ✅ La tarea tarda mucho (5+ minutos)
- ✅ Frontend NO debe esperar (timeout)
- ✅ Procesamiento en background
- ✅ Permite monitorear progreso con polling

---

### **FASE 4: EXTRACCIÓN BATCH** ✅ SÍ Pub/Sub (AQUÍ ES CLAVE)

**Uso**: Procesamiento paralelo de 100+ jobs con LLM

**Patrón**: **Pub/Sub** (Asíncrono + Paralelo)

**Flujo**:

```
1. USUARIO SELECCIONA
   Usuario selecciona 100 jobs en interfaz
   Usuario hace clic "Extraer habilidades (Pipeline B con LLM)"
     ↓ HTTP POST

2. API RECIBE Y VALIDA
   Frontend → API: POST /api/extract/batch
   Body: {
     "job_ids": [1, 2, 3, ..., 100],
     "pipeline": "B"  ← LLM (Gemma 3B)
   }
     ↓
   API valida:
     • ¿Jobs existen? SELECT COUNT(*) FROM cleaned_jobs WHERE job_id IN (...)
     • ¿Ya procesados? extraction_status != 'completed'
     • ¿Usuario tiene permisos? (futuro)
     ↓

3. API PUBLICA 100 TAREAS (Pub/Sub!)
   for job_id in [1, 2, 3, ..., 100]:
       task_id = celery.send_task(
           "extract_skills_llm",
           args=[job_id],
           kwargs={"pipeline": "B"}
       )

   # Redis recibe 100 tareas:
   LPUSH queue:celery '{"task": "extract_skills_llm", "args": [1]}'
   LPUSH queue:celery '{"task": "extract_skills_llm", "args": [2]}'
   ...
   LPUSH queue:celery '{"task": "extract_skills_llm", "args": [100]}'
     ↓

4. API RESPONDE INMEDIATAMENTE
   {
     "batch_id": "batch_abc",
     "task_ids": ["task1", "task2", ..., "task100"],
     "status": "QUEUED",
     "total": 100
   }
     ↓

5. FRONTEND POLLING
   Frontend muestra: "Procesando 0/100 jobs..."
     ↓ Polling cada 3 segundos
   GET /api/batches/batch_abc
     → {"completed": 15, "pending": 85, "failed": 0}
   Frontend: "Procesando 15/100 jobs... (15%)"
     ↓

6. WORKERS PROCESAN EN PARALELO (Pub/Sub en acción!)

   [Mientras tanto, 4 workers trabajando PARALELAMENTE]

   Worker 1 (CONSUME de Redis):
     BRPOP queue:celery → {"task": "extract_skills_llm", "args": [1]}
     → Procesa job_id=1 (5 segundos)
     → Marca completado: SET result:task1 '{"status": "SUCCESS"}'
     → BRPOP queue:celery → {"task": "extract_skills_llm", "args": [5]}
     → Procesa job_id=5...

   Worker 2 (CONSUME de Redis):
     BRPOP queue:celery → {"task": "extract_skills_llm", "args": [2]}
     → Procesa job_id=2 (5 segundos)
     → Marca completado
     → BRPOP queue:celery → obtiene siguiente...

   Worker 3 (CONSUME de Redis):
     BRPOP queue:celery → {"task": "extract_skills_llm", "args": [3]}
     → Procesa job_id=3...

   Worker 4 (CONSUME de Redis):
     BRPOP queue:celery → {"task": "extract_skills_llm", "args": [4]}
     → Procesa job_id=4...

   # Los 4 workers consumen de la cola hasta vaciarla
   # Tiempo total: ~125 segundos (100 jobs / 4 workers = 25 jobs cada uno × 5s)
   # Si fuera síncrono: 500 segundos (100 jobs × 5s)
     ↓

7. FRONTEND DETECTA COMPLETADO
   [Polling detecta]
   GET /api/batches/batch_abc
     → {"completed": 100, "pending": 0, "failed": 0}

   Frontend muestra: "✓ 100 jobs procesados correctamente en 2 min 5 seg"
```

**¿Por qué SÍ Pub/Sub?**
- ✅ Procesamiento PARALELO (4 workers simultáneos)
- ✅ Tareas largas (5s cada una × 100 = 8+ minutos en total)
- ✅ Desacoplamiento: API no sabe quién procesa
- ✅ Load balancing: Redis distribuye entre workers disponibles
- ✅ Escalable: agregar más workers reduce tiempo linealmente

**Esto ES Pub/Sub porque**:
- **Publisher**: API publica 100 tareas
- **Message Broker**: Redis (cola intermedia)
- **Subscribers**: 4 Workers consumen lo que puedan
- **Desacoplamiento total**: API ↔ Workers no se conocen

---

### **FASE 5: EXTRACCIÓN CON LLM** ❌ NO Pub/Sub (Dentro del Worker)

**Patrón**: **Request/Response** (Worker → LLM → Worker)

**Flujo dentro del worker**:

```
Worker N recibe job_id=X de Redis
  ↓

1. SELECT de cleaned_jobs (Request/Response con PostgreSQL)
   combined_text = db.query(CleanedJob).filter_by(job_id=X).first()
   # "Se busca desarrollador Python con FastAPI, PostgreSQL..."
     ↓

2. Llamada a LLM (Request/Response con Gemma 3B)
   prompt = f"""
   Extrae habilidades técnicas del siguiente texto:
   {combined_text}

   Devuelve JSON:
   {{"skills": ["Python", "FastAPI", "PostgreSQL", ...]}}
   """

   response = llm.generate(prompt)  # Bloqueante, espera respuesta (5s)
   # {"skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "Git"]}

   skills = parse_json(response.text)
     ↓

3. Normalización y búsqueda ESCO (Request/Response con PostgreSQL)
   for skill in skills:
       # Normaliza: "python" → "Python"
       normalized = skill.title()

       # Busca en ESCO taxonomy
       esco_match = db.query(ESCOSkill).filter(
           func.similarity(ESCOSkill.preferred_label_es, normalized) > 0.8
       ).first()
       # Resultado: "http://data.europa.eu/esco/skill/python"
     ↓

4. INSERT en enhanced_skills (Request/Response con PostgreSQL)
   db.bulk_insert([
       EnhancedSkill(
           job_id=X,
           normalized_skill="Python",
           esco_concept_uri="http://esco.../python",
           llm_model="gemma-3-4b",
           processing_time_seconds=5.2,
           tokens_used=1523
       ),
       # ... más skills
   ])
     ↓

5. UPDATE raw_jobs (Request/Response con PostgreSQL)
   db.query(RawJob).filter_by(job_id=X).update({
       "extraction_status": "completed",
       "extraction_completed_at": datetime.now()
   })
     ↓

6. Marca en Redis (Set en Redis DB 1)
   redis.set(f"result:task_N", json.dumps({
       "status": "SUCCESS",
       "job_id": X,
       "skills_extracted": 5,
       "time_seconds": 5.2
   }))
```

**¿Por qué NO Pub/Sub?**
- ❌ Worker ejecuta SECUENCIALMENTE (no hay paralelismo aquí)
- ❌ Worker → LLM es Request/Response (espera respuesta)
- ❌ Worker → PostgreSQL es Request/Response (espera confirmación)
- ❌ No hay publicación de eventos, solo ejecución directa

**Esto es Request/Response porque**:
- Worker ESPERA respuesta del LLM antes de continuar
- Worker ESPERA confirmación de INSERT antes de continuar
- Flujo lineal: SELECT → LLM → INSERT → UPDATE → SET

---

### **FASE 6: MONITOREO DE PROGRESO** ❌ NO Pub/Sub (Polling)

**Patrón**: **Request/Response + Polling**

**Flujo**:

```
[Mientras workers procesan batch de 100 jobs]

Frontend (cada 3 segundos en loop):
  GET /api/batches/batch_abc
    ↓ HTTP Request

API consulta Redis (Request/Response):
  completed = 0
  failed = 0

  for task_id in batch.task_ids:  # 100 tareas
      result = redis.get(f"result:{task_id}")

      if result:
          data = json.loads(result)
          if data["status"] == "SUCCESS":
              completed += 1
          elif data["status"] == "FAILURE":
              failed += 1

  pending = 100 - completed - failed
    ↓ HTTP Response

API → Frontend:
  {
    "completed": 45,
    "pending": 55,
    "failed": 0,
    "progress_percent": 45
  }
    ↓

Frontend actualiza UI:
  <ProgressBar value={45} max={100} />
  "Procesando 45/100 jobs... (45%)"
    ↓
  [Espera 3 segundos]
    ↓
  GET /api/batches/batch_abc (repite)
```

**¿Por qué NO Pub/Sub?**
- ❌ Frontend ESPERA respuesta (Request/Response)
- ❌ No hay eventos, solo consultas periódicas (polling)
- ❌ API solo CONSULTA Redis, no publica nada

**Esto es Polling porque**:
- Frontend pregunta activamente cada N segundos
- No hay notificación push (Workers no notifican a Frontend)
- API actúa como intermediario de consulta

**Alternativa futura (SÍ Pub/Sub)**:
- WebSockets o Server-Sent Events (SSE)
- Workers publican eventos a Redis Pub/Sub
- API escucha y hace push a Frontend
- Frontend recibe updates en tiempo real sin polling

---

### **FASE 7: CLUSTERING** ✅ SÍ Pub/Sub

**Patrón**: **Pub/Sub** (Asíncrono)

**Flujo**:

```
Usuario hace clic "Generar clusters"
  ↓ HTTP POST

Frontend → API: POST /api/cluster
  Body: {
    "pipeline": "B",
    "n_clusters": 50,
    "country": "CO"
  }
  ↓

API publica tarea a Redis:
  task_id = celery.send_task("cluster_skills", args=[...])
  LPUSH queue:celery '{"task": "cluster_skills", ...}'
  ↓

API responde INMEDIATAMENTE:
  {"task_id": "cluster_xyz", "status": "PENDING"}
  ↓

Worker consume de Redis:
  BRPOP queue:celery → obtiene tarea

  1. SELECT embedding_vector FROM enhanced_skills
     WHERE country = 'CO' AND llm_model = 'gemma-3-4b'
     # Resultado: 3,542 embeddings de 768 dimensiones

  2. Aplica UMAP (reduce 768D → 2D)
     from umap import UMAP
     reducer = UMAP(n_neighbors=15, min_dist=0.1, n_components=2)
     coords_2d = reducer.fit_transform(embeddings)
     # Ahora: 3,542 puntos en 2D

  3. Aplica HDBSCAN (clustering)
     from hdbscan import HDBSCAN
     clusterer = HDBSCAN(min_cluster_size=5, min_samples=3)
     labels = clusterer.fit_predict(coords_2d)
     # Resultado: [0, 0, 1, 2, 0, 1, -1, 3, ...]

  4. Detecta clusters:
     Cluster 0 (89 skills): "Backend Development"
       Top skills: Python, FastAPI, PostgreSQL, Docker

     Cluster 1 (67 skills): "Data Science"
       Top skills: Pandas, NumPy, Scikit-learn, Matplotlib

     Cluster 2 (54 skills): "DevOps"
       Top skills: Docker, Kubernetes, AWS, Terraform

     Cluster -1 (15 skills): Noise (no cluster)

  5. Guarda resultados:
     INSERT INTO clustering_results (
       pipeline_name='pipeline_b_co',
       n_clusters=3,
       cluster_data=json({...}),
       created_at=NOW()
     )

  6. Marca completado:
     redis.set("result:cluster_xyz", {"status": "SUCCESS", "n_clusters": 3})
  ↓

Frontend detecta (polling):
  GET /api/tasks/cluster_xyz → {"status": "SUCCESS"}

Frontend muestra: "✓ 3 clusters generados con 3,527 habilidades"
```

**¿Por qué SÍ Pub/Sub?**
- ✅ Tarea MUY larga (3+ minutos para 3,542 embeddings)
- ✅ Procesamiento computacionalmente intensivo (UMAP + HDBSCAN)
- ✅ Frontend NO debe esperar
- ✅ Se ejecuta en background

---

## 🔌 Pub/Sub vs Request/Response

### **Tabla Resumen: Cuándo Usar Cada Patrón**

| Fase                      | Patrón              | ¿Pub/Sub? | Publisher      | Subscriber     | Razón                              |
|---------------------------|---------------------|-----------|----------------|----------------|------------------------------------|
| **Scraping**              | Event-Driven        | ✅ SÍ      | Celery Beat    | Celery Worker  | Automático cada 6h, tarda 5-30 min |
| **Detección nuevos jobs** | -                   | ❌ NO      | -              | -              | Jobs esperan en DB (is_processed=FALSE) |
| **Limpieza manual**       | Request/Response    | ❌ NO      | -              | -              | <100 jobs, <5 segundos, respuesta inmediata |
| **Limpieza batch**        | Event-Driven        | ✅ SÍ      | API            | Celery Worker  | >1000 jobs, tarda minutos          |
| **Extracción batch**      | Event-Driven        | ✅ SÍ      | API            | Celery Workers | 100+ jobs, procesamiento paralelo  |
| **LLM call (dentro worker)** | Request/Response | ❌ NO      | -              | -              | Worker espera respuesta de LLM     |
| **Monitoreo progreso**    | Request/Response + Polling | ❌ NO | -        | -              | Consulta estado cada 3s (polling)  |
| **Clustering**            | Event-Driven        | ✅ SÍ      | API            | Celery Worker  | Tarea pesada, 3+ minutos           |

---

### **Reglas para Elegir el Patrón**

#### **Usa Pub/Sub (Event-Driven) cuando:**

1. ✅ **La tarea tarda mucho** (>5 segundos)
   - Ejemplo: Scraping (5-30 min), Extracción batch (5s × 100 jobs)

2. ✅ **No necesitas respuesta inmediata**
   - Ejemplo: Scraping automático, clustering

3. ✅ **Quieres procesamiento en paralelo**
   - Ejemplo: 100 jobs procesados por 4 workers = 25 cada uno

4. ✅ **Quieres desacoplamiento**
   - Ejemplo: API no sabe ni le importa QUÉ worker procesa

5. ✅ **Quieres programar automáticamente**
   - Ejemplo: Celery Beat publica tareas cada 6 horas

**Ventajas Pub/Sub:**
- Escalabilidad horizontal (agregar más workers)
- Resiliencia (si un worker falla, otro toma la tarea)
- Load balancing automático (Redis distribuye)
- Frontend no se bloquea

---

#### **Usa Request/Response cuando:**

1. ✅ **Necesitas respuesta inmediata**
   - Ejemplo: GET /api/jobs?limit=10 (muestra en UI ahora)

2. ✅ **La operación es rápida** (<1 segundo)
   - Ejemplo: SELECT COUNT(*) FROM jobs

3. ✅ **Es una consulta simple**
   - Ejemplo: GET /api/stats (estadísticas)

4. ✅ **Dentro de un worker** (no hay publicación)
   - Ejemplo: Worker → LLM (espera respuesta)

5. ✅ **Polling de estado**
   - Ejemplo: GET /api/tasks/abc123 cada 3 segundos

**Ventajas Request/Response:**
- Simplicidad (no hay cola intermedia)
- Respuesta inmediata (UX mejor para consultas rápidas)
- Menos infraestructura (no requiere Celery)

---

### **Ejemplos Concretos**

**Request/Response (Rápido, Síncrono)**:
```python
# Frontend
response = await fetch("/api/jobs?country=CO&limit=10")
jobs = await response.json()
console.log(jobs)  // Inmediato, 200ms

# API (Síncrono)
@app.get("/api/jobs")
async def get_jobs(country: str, limit: int):
    jobs = db.query(RawJob).filter_by(country=country).limit(limit).all()
    return {"jobs": jobs}  # Responde en <1 segundo
```

**Pub/Sub (Lento, Asíncrono)**:
```python
# Frontend
response = await fetch("/api/extract/batch", {
    method: "POST",
    body: JSON.stringify({job_ids: [1,2,3,...,100]})
})
result = await response.json()
console.log(result)  // {"task_id": "xyz", "status": "PENDING"}

// Polling cada 3s
setInterval(async () => {
    const status = await fetch(`/api/tasks/${result.task_id}`)
    const data = await status.json()
    console.log(data)  // {"completed": 45, "pending": 55}
}, 3000)

# API (Asíncrono)
@app.post("/api/extract/batch")
async def extract_batch(job_ids: List[int]):
    # Publica 100 tareas a Redis (NO espera)
    task_ids = []
    for job_id in job_ids:
        task = extract_skills_llm.delay(job_id)
        task_ids.append(task.id)

    # Responde INMEDIATAMENTE (2ms)
    return {"task_id": "batch_xyz", "status": "QUEUED", "total": 100}

# Worker (procesa en background)
@celery_app.task
def extract_skills_llm(job_id):
    # ... procesamiento (5 segundos)
    redis.set(f"result:{task.id}", {"status": "SUCCESS"})
```

---

## 🗄️ Database Design

### **Tablas Principales y Flujo de Estados**

#### **1. raw_jobs** - Jobs Scrapeados

```sql
CREATE TABLE raw_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portal VARCHAR(50) NOT NULL,           -- 'computrabajo', 'linkedin', 'elempleo'
    country CHAR(2) NOT NULL,              -- 'CO', 'MX', 'AR'
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT NOT NULL,
    requirements TEXT,
    salary_raw TEXT,
    contract_type VARCHAR(50),
    remote_type VARCHAR(50),
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash VARCHAR(64) UNIQUE,       -- SHA256 para evitar duplicados
    raw_html TEXT,

    -- Estados de procesamiento
    is_processed BOOLEAN DEFAULT FALSE,    -- ¿Ya pasó por limpieza?
    extraction_status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed'
    extraction_completed_at TIMESTAMP,

    CONSTRAINT uk_content_hash UNIQUE (content_hash)
);

-- Índices de performance
CREATE INDEX idx_raw_jobs_country ON raw_jobs(country);
CREATE INDEX idx_raw_jobs_portal ON raw_jobs(portal);
CREATE INDEX idx_raw_jobs_processed ON raw_jobs(is_processed);
CREATE INDEX idx_raw_jobs_extraction_status ON raw_jobs(extraction_status);
CREATE INDEX idx_raw_jobs_scraped_at ON raw_jobs(scraped_at DESC);
```

**Flujo de estados**:
```
Scraping → is_processed=FALSE, extraction_status='pending'
Limpieza → is_processed=TRUE
Extracción → extraction_status='in_progress' → 'completed'
```

---

#### **2. cleaned_jobs** - Jobs Limpios

```sql
CREATE TABLE cleaned_jobs (
    cleaned_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,

    -- Textos limpios
    title_cleaned TEXT NOT NULL,
    description_cleaned TEXT NOT NULL,
    requirements_cleaned TEXT,
    combined_text TEXT NOT NULL,           -- title + description + requirements

    -- Métricas de calidad
    combined_word_count INTEGER,
    detected_language VARCHAR(5),          -- 'es', 'en', 'pt'
    is_usable BOOLEAN DEFAULT TRUE,
    unusable_reason VARCHAR(100),          -- 'too_short', 'wrong_language', 'spam'

    cleaned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_cleaned_job_id UNIQUE (job_id)
);

CREATE INDEX idx_cleaned_jobs_usable ON cleaned_jobs(is_usable);
CREATE INDEX idx_cleaned_jobs_language ON cleaned_jobs(detected_language);
```

**Criterios de limpieza**:
- `combined_word_count > 50` → Descripción suficientemente detallada
- `detected_language IN ('es', 'en')` → Idiomas soportados
- HTML tags removidos
- Espacios múltiples normalizados

---

#### **3. extracted_skills** - Skills Extraídas (NER/Regex/ESCO)

```sql
CREATE TABLE extracted_skills (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,

    skill_text TEXT NOT NULL,
    skill_type VARCHAR(50),                -- 'explicit', 'implicit'
    extraction_method VARCHAR(50),         -- 'ner', 'regex', 'esco'
    confidence_score FLOAT,                -- 0.0-1.0
    source_section VARCHAR(50),            -- 'title', 'description', 'requirements'
    span_start INTEGER,                    -- Posición en texto
    span_end INTEGER,
    esco_uri TEXT,                         -- URL de ESCO taxonomy

    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_extracted_skills_job_id ON extracted_skills(job_id);
CREATE INDEX idx_extracted_skills_text ON extracted_skills(skill_text);
CREATE INDEX idx_extracted_skills_method ON extracted_skills(extraction_method);
```

---

#### **4. enhanced_skills** - Skills Normalizadas con LLM

```sql
CREATE TABLE enhanced_skills (
    enhancement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id) ON DELETE CASCADE,

    original_skill_text TEXT,
    normalized_skill TEXT NOT NULL,        -- "python" → "Python"
    skill_type VARCHAR(50),                -- 'explicit', 'implicit'

    -- ESCO normalization
    esco_concept_uri TEXT,
    esco_preferred_label TEXT,

    -- LLM metadata
    llm_confidence FLOAT,                  -- 0.0-1.0
    llm_reasoning TEXT,                    -- Por qué se infirió (implicit skills)
    llm_model VARCHAR(100),                -- 'gemma-3-4b', 'openai-gpt-4'

    -- Deduplicación
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID,                  -- Apunta a la skill original

    -- Procesamiento
    processing_time_seconds FLOAT,
    tokens_used INTEGER,

    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_enhanced_skills_job_id ON enhanced_skills(job_id);
CREATE INDEX idx_enhanced_skills_normalized ON enhanced_skills(normalized_skill);
CREATE INDEX idx_enhanced_skills_duplicate ON enhanced_skills(is_duplicate);
CREATE INDEX idx_enhanced_skills_esco_uri ON enhanced_skills(esco_concept_uri);
```

**Ejemplos**:
```sql
-- Skill explícita
INSERT INTO enhanced_skills (
    job_id, original_skill_text, normalized_skill,
    skill_type, esco_concept_uri, llm_confidence, llm_model
) VALUES (
    'uuid-123', 'python', 'Python',
    'explicit', 'http://data.europa.eu/esco/skill/python', 0.95, 'gemma-3-4b'
);

-- Skill implícita (inferida por LLM)
INSERT INTO enhanced_skills (
    job_id, normalized_skill, skill_type,
    llm_confidence, llm_reasoning, llm_model
) VALUES (
    'uuid-123', 'JavaScript', 'implicit',
    0.88, 'React requires JavaScript knowledge', 'gemma-3-4b'
);
```

---

#### **5. skill_embeddings** - Vectores para Clustering

```sql
-- Requiere extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT UNIQUE NOT NULL,
    embedding vector(768) NOT NULL,        -- Embedding de 768 dimensiones
    model_name VARCHAR(100) NOT NULL,      -- 'intfloat/multilingual-e5-base'
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índice para búsqueda de similitud vectorial
CREATE INDEX ON skill_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX idx_skill_embeddings_text ON skill_embeddings(skill_text);
```

**Operaciones vectoriales**:
```sql
-- Buscar skills similares a "Python"
SELECT skill_text, 1 - (embedding <=> (
    SELECT embedding FROM skill_embeddings WHERE skill_text = 'Python'
)) AS similarity
FROM skill_embeddings
WHERE skill_text != 'Python'
ORDER BY embedding <=> (
    SELECT embedding FROM skill_embeddings WHERE skill_text = 'Python'
)
LIMIT 10;

-- Resultado:
-- skill_text   | similarity
-- -------------|----------
-- Django       | 0.87
-- FastAPI      | 0.84
-- Flask        | 0.82
-- Pandas       | 0.79
-- NumPy        | 0.76
```

---

#### **6. esco_taxonomy** - Taxonomía ESCO (13,000+ skills)

```sql
CREATE TABLE esco_taxonomy (
    concept_uri TEXT PRIMARY KEY,          -- 'http://data.europa.eu/esco/skill/...'
    preferred_label_en TEXT,
    preferred_label_es TEXT,
    alternative_labels TEXT[],             -- Sinónimos
    skill_type VARCHAR(50),                -- 'knowledge', 'skill', 'competence'
    description_en TEXT,
    description_es TEXT,
    broader_concept_uri TEXT,              -- Jerarquía (padre)
    narrower_concept_uris TEXT[],          -- Jerarquía (hijos)
    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_esco_preferred_label_es ON esco_taxonomy(preferred_label_es);
CREATE INDEX idx_esco_preferred_label_en ON esco_taxonomy(preferred_label_en);
CREATE INDEX idx_esco_skill_type ON esco_taxonomy(skill_type);

-- Índice para búsqueda por similitud de texto
CREATE INDEX idx_esco_label_es_trgm ON esco_taxonomy
USING gin (preferred_label_es gin_trgm_ops);
```

**Ejemplos**:
```sql
-- Buscar skill en ESCO
SELECT concept_uri, preferred_label_es, skill_type
FROM esco_taxonomy
WHERE similarity(preferred_label_es, 'Python') > 0.8
ORDER BY similarity(preferred_label_es, 'Python') DESC
LIMIT 5;

-- Resultado:
-- concept_uri                                    | preferred_label_es | skill_type
-- -----------------------------------------------|--------------------|-----------
-- http://data.europa.eu/esco/skill/python       | Python             | skill
-- http://data.europa.eu/esco/skill/python-django| Django (Python)    | skill
-- http://data.europa.eu/esco/skill/micropython  | MicroPython        | skill
```

---

#### **7. clustering_results** - Resultados de Clustering

```sql
CREATE TABLE clustering_results (
    cluster_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    pipeline_name VARCHAR(100) NOT NULL,   -- 'pipeline_b_300_post', 'pipeline_a_100_pre'
    country CHAR(2),                       -- NULL = todos los países

    cluster_number INTEGER NOT NULL,       -- 0, 1, 2, ..., -1 (noise)
    cluster_label VARCHAR(200),            -- "Backend Development", "Data Science"
    skill_texts TEXT[],                    -- Skills en este cluster
    size INTEGER,                          -- Cantidad de skills
    cohesion_score FLOAT,                  -- Qué tan compacto es el cluster

    -- Métricas globales
    n_clusters INTEGER,                    -- Total de clusters encontrados
    n_noise INTEGER,                       -- Skills sin cluster
    silhouette_score FLOAT,                -- Métrica de calidad
    davies_bouldin_index FLOAT,

    -- Metadata
    umap_params JSONB,                     -- {n_neighbors: 15, min_dist: 0.1, ...}
    hdbscan_params JSONB,                  -- {min_cluster_size: 5, ...}

    analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_clustering_pipeline ON clustering_results(pipeline_name);
CREATE INDEX idx_clustering_country ON clustering_results(country);
CREATE INDEX idx_clustering_analyzed_at ON clustering_results(analyzed_at DESC);
```

**Ejemplo**:
```sql
-- Resultados de clustering
INSERT INTO clustering_results (
    pipeline_name, country, cluster_number, cluster_label,
    skill_texts, size, cohesion_score,
    n_clusters, silhouette_score, umap_params, hdbscan_params
) VALUES (
    'pipeline_b_300_post', 'CO', 0, 'Backend Development',
    ARRAY['Python', 'FastAPI', 'PostgreSQL', 'Docker', 'Git'], 89, 0.78,
    12, 0.68, '{"n_neighbors": 15, "min_dist": 0.1}', '{"min_cluster_size": 5}'
);
```

---

### **Vistas de Consulta Rápida**

```sql
-- Vista: Frecuencia de skills por país
CREATE VIEW skill_frequency_by_country AS
SELECT
    rj.country,
    es.normalized_skill,
    COUNT(DISTINCT es.job_id) AS job_count,
    COUNT(*) AS total_mentions,
    ROUND(AVG(es.llm_confidence), 2) AS avg_confidence
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
WHERE es.is_duplicate = FALSE
  AND rj.extraction_status = 'completed'
GROUP BY rj.country, es.normalized_skill
ORDER BY rj.country, job_count DESC;

-- Uso:
SELECT * FROM skill_frequency_by_country
WHERE country = 'CO' LIMIT 10;

-- Resultado:
-- country | normalized_skill | job_count | total_mentions | avg_confidence
-- --------|------------------|-----------|----------------|---------------
-- CO      | Python           | 1250      | 1523           | 0.94
-- CO      | JavaScript       | 980       | 1204           | 0.92
-- CO      | SQL              | 875       | 1050           | 0.91
```

---

## 🚀 Performance & Scalability

### **1. Horizontal Scaling - Celery Workers**

```bash
# Escalar workers dinámicamente
docker-compose up -d --scale celery_worker=8

# Resultado:
# - 8 workers procesando en paralelo
# - Load balancing automático por Redis
# - Tiempo de procesamiento reducido 8x (idealmente)

# Ejemplo real:
# 100 jobs × 5 segundos cada uno:
# - 1 worker: 500 segundos (8 min 20 seg)
# - 4 workers: 125 segundos (2 min 5 seg)
# - 8 workers: 62.5 segundos (1 min 2 seg)
```

**Ventajas**:
- ✅ Sin cambios de código
- ✅ Load balancing automático
- ✅ Resiliencia (un worker falla, otros continúan)

---

### **2. Optimización de Base de Datos**

**Índices estratégicos**:
```sql
-- Consultas frecuentes optimizadas
CREATE INDEX idx_raw_jobs_pending_extraction ON raw_jobs(country)
WHERE extraction_status = 'pending';  -- Índice parcial

CREATE INDEX idx_enhanced_skills_active ON enhanced_skills(normalized_skill)
WHERE is_duplicate = FALSE;  -- Solo skills activas

-- Búsqueda de texto (trigram)
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_skill_text_trgm ON enhanced_skills
USING gin (normalized_skill gin_trgm_ops);
```

**Connection Pooling** (SQLAlchemy):
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # 20 conexiones persistentes
    max_overflow=0,         # No crear conexiones extra
    pool_timeout=30,        # Timeout de 30s
    pool_recycle=3600,      # Reciclar conexiones cada hora
    pool_pre_ping=True      # Verificar conexión antes de usar
)
```

---

### **3. Caching con Redis**

```python
# Cache de queries frecuentes
@app.get("/api/stats")
async def get_stats(country: str):
    cache_key = f"stats:{country}"

    # Intenta cache primero
    cached = redis.get(cache_key)
    if cached:
        return json.loads(cached)

    # Si no hay cache, consulta DB
    stats = db.query(...).all()

    # Guarda en cache (TTL 5 minutos)
    redis.setex(cache_key, 300, json.dumps(stats))

    return stats
```

---

### **4. Batch Processing Optimizado**

```python
# Procesamiento en batches para evitar memory overflow
def process_large_batch(job_ids: List[int], batch_size=500):
    for i in range(0, len(job_ids), batch_size):
        batch = job_ids[i:i + batch_size]

        # Procesa 500 jobs a la vez
        for job_id in batch:
            extract_skills_llm.delay(job_id)

        # Pequeña pausa entre batches
        time.sleep(1)
```

---

## 🔒 Security & Compliance

### **1. Variables de Entorno (Secrets Management)**

```bash
# .env (NO en version control)
DATABASE_URL=postgresql://user:***@localhost:5432/labor_observatory
REDIS_URL=redis://localhost:6379
OPENAI_API_KEY=sk-***
GEMMA_MODEL_PATH=/models/gemma-3-4b
SECRET_KEY=***
```

### **2. SQL Injection Prevention**

```python
# ❌ MALO (vulnerable)
query = f"SELECT * FROM jobs WHERE country = '{country}'"
db.execute(query)

# ✅ BUENO (parametrizado)
query = "SELECT * FROM jobs WHERE country = %s"
db.execute(query, (country,))

# ✅ MEJOR (ORM)
jobs = db.query(RawJob).filter_by(country=country).all()
```

### **3. CORS Configuration**

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",     # Frontend dev
        "https://yourdomain.com"     # Frontend prod
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],   # Explícito
    allow_headers=["*"],
)
```

### **4. Rate Limiting**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/extract/batch")
@limiter.limit("10/minute")  # Máximo 10 requests por minuto
async def extract_batch(request: Request, job_ids: List[int]):
    # ... procesamiento
    pass
```

---

## 🎯 Conclusión: Arquitectura Híbrida en Acción

Tu sistema combina inteligentemente tres patrones:

1. **API Gateway (Nginx)**: Punto único de entrada
2. **Microservicios en Capas**: Request/Response para consultas rápidas
3. **Event-Driven (Pub/Sub)**: Procesamiento asíncrono para tareas largas

**Uso estratégico**:
- ✅ **Request/Response**: GET /jobs, /stats (rápido, <1s)
- ✅ **Pub/Sub**: POST /extract/batch, scraping (lento, paralelo)
- ✅ **CRISP-DM**: Pipeline modular (Scraping → Extraction → Clustering)

**Resultado**: Sistema escalable, eficiente y robusto para analizar demanda laboral en Latinoamérica.

---

**Esta arquitectura híbrida proporciona lo mejor de ambos mundos: la simplicidad de Request/Response para operaciones rápidas y la potencia de Event-Driven para procesamiento distribuido a gran escala.** 🚀
