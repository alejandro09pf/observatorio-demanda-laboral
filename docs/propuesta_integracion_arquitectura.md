# Propuesta de Integración: Arquitectura del Sistema
## Reestructuración de la Sección 6.3 del Documento Principal

---

## 📋 Estructura Propuesta

### **Sección 6.3: Arquitectura del Sistema** (Reemplazar completamente)

```
6.3 Arquitectura del Sistema .................................................. XX
    6.3.1 Modelo de Vistas Arquitectónicas .................................. XX
    6.3.2 Vista Lógica: Componentes y Patrones Arquitectónicos ............. XX
          6.3.2.1 Patrón Híbrido Implementado .............................. XX
          6.3.2.2 Los Siete Servicios del Sistema .......................... XX
          6.3.2.3 Patrones de Comunicación: Request/Response y Pub/Sub .... XX
    6.3.3 Vista Física: Infraestructura y Despliegue ....................... XX
          6.3.3.1 Especificaciones del Servidor ............................ XX
          6.3.3.2 Contenedores Docker y Orquestación ....................... XX
          6.3.3.3 Configuración de Red y Volúmenes ......................... XX
    6.3.4 Vista de Procesos: Ejecución y Concurrencia ..................... XX
          6.3.4.1 Pipeline CRISP-DM y Flujo de Procesamiento ............... XX
          6.3.4.2 Escalabilidad Horizontal de Workers ...................... XX
          6.3.4.3 Gestión de Tareas Asíncronas ............................. XX
    6.3.5 Integración de Vistas: Arquitectura Completa ..................... XX
    6.3.6 Diseño de la Base de Datos ....................................... XX
```

---

## 📝 Texto Propuesto para Cada Subsección

### **6.3 Arquitectura del Sistema**

El diseño arquitectónico del Observatorio de Demanda Laboral requiere una documentación multinivel que capture tanto la estructura lógica del sistema como su despliegue físico y comportamiento en tiempo de ejecución. Para lograr una especificación completa y no ambigua, se adoptó el **Modelo 4+1 de Vistas Arquitectónicas** propuesto por Kruchten (1995), el cual permite describir la arquitectura desde múltiples perspectivas complementarias, cada una enfocada en las preocupaciones de diferentes stakeholders del proyecto.

Este modelo organiza la arquitectura en cuatro vistas principales más una vista de escenarios:

1. **Vista Lógica**: Describe la funcionalidad que el sistema proporciona a los usuarios finales mediante la descomposición en componentes y sus relaciones
2. **Vista de Procesos**: Aborda aspectos de concurrencia, distribución, integración, rendimiento y escalabilidad del sistema
3. **Vista Física** (Deployment): Mapea el software sobre el hardware y muestra la distribución física de los componentes
4. **Vista de Desarrollo**: Describe la organización estática del software en su ambiente de desarrollo
5. **Vista de Escenarios** (+1): Ilustra el comportamiento del sistema mediante casos de uso concretos

Para el presente proyecto, se documentan tres de estas vistas: **Lógica, Física y de Procesos**, que en conjunto proporcionan una especificación completa de la arquitectura implementada. La Vista de Desarrollo se omite por estar fuera del alcance de este documento académico, mientras que los escenarios de uso se abordan en el Capítulo 8 (Resultados) mediante casos de estudio específicos.

Las siguientes subsecciones presentan cada vista arquitectónica, comenzando con la estructura lógica del sistema, seguida de su despliegue físico, y culminando con los aspectos dinámicos de ejecución y procesamiento distribuido.

---

### **6.3.1 Modelo de Vistas Arquitectónicas**

#### Justificación del Modelo de Vistas

La complejidad inherente del sistema — que combina procesamiento síncrono de baja latencia para consultas de usuarios con procesamiento asíncrono distribuido de tareas computacionalmente intensivas — requiere múltiples perspectivas para su documentación completa. Una sola vista arquitectónica resultaría insuficiente para capturar simultáneamente:

- La descomposición funcional del sistema en servicios especializados
- El mapeo de estos servicios sobre contenedores Docker e infraestructura física
- Los flujos de ejecución y procesamiento paralelo de datos
- Las decisiones de escalabilidad y tolerancia a fallos

El Modelo 4+1 de Kruchten proporciona un marco probado industrialmente para organizar estas perspectivas de forma coherente y sistemática.

#### Vistas Documentadas

**Vista Lógica** (Sección 6.3.2):
- Enfoque: Funcionalidad y responsabilidades de cada componente
- Audiencia: Arquitectos de software, desarrolladores
- Artefactos: Diagramas de componentes, patrones arquitectónicos
- Notación: C4 Model - Container Level + diagramas UML de componentes

**Vista Física** (Sección 6.3.3):
- Enfoque: Topología de despliegue, infraestructura, configuración de red
- Audiencia: DevOps, administradores de sistemas, ingenieros de infraestructura
- Artefactos: Diagramas de despliegue, especificaciones de hardware
- Notación: UML Deployment Diagrams

**Vista de Procesos** (Sección 6.3.4):
- Enfoque: Comportamiento en tiempo de ejecución, concurrencia, throughput
- Audiencia: Arquitectos de rendimiento, ingenieros de escalabilidad
- Artefactos: Diagramas de flujo de datos, diagramas de secuencia
- Notación: Diagramas de actividad, BPMN adaptado

Cada vista se complementa con las demás para formar una especificación arquitectónica completa. La Sección 6.3.5 sintetiza estas perspectivas y muestra cómo se integran para formar el sistema completo.

---

### **6.3.2 Vista Lógica: Componentes y Patrones Arquitectónicos**

La vista lógica describe la descomposición funcional del sistema en servicios especializados y los patrones arquitectónicos que gobiernan sus interacciones. Esta sección presenta la arquitectura híbrida implementada, detalla cada uno de los siete servicios que componen el sistema, y especifica los dos patrones de comunicación fundamentales que coordinan sus operaciones.

#### **6.3.2.1 Patrón Híbrido Implementado**

El sistema implementa una **arquitectura híbrida** que combina tres patrones arquitectónicos complementarios para satisfacer requisitos duales de latencia: operaciones síncronas de baja latencia (<1 segundo) para consultas de usuarios, y procesamiento asíncrono distribuido de tareas computacionalmente intensivas que pueden requerir minutos u horas.

La Figura 6.X presenta la arquitectura híbrida completa, destacando los tres patrones integrados:

**[INSERTAR AQUÍ: architecture_diagram.png]**
*Figura 6.X: Arquitectura Híbrida del Observatorio de Demanda Laboral. El sistema integra tres patrones: (1) API Gateway (Nginx) como punto único de entrada, (2) Microservicios en Capas (Frontend + API + PostgreSQL) para operaciones síncronas Request/Response, y (3) Event-Driven Architecture (Redis + Celery) para procesamiento asíncrono distribuido mediante patrón Pub/Sub.*

**Patrón 1: API Gateway**

El patrón API Gateway se implementa mediante Nginx, que actúa como punto único de entrada para todas las peticiones HTTP/HTTPS externas. Este patrón proporciona:

- **Routing inteligente**: Enruta `/` hacia el servicio Frontend (puerto 3000) y `/api/*` hacia el servicio API (puerto 8000)
- **SSL/TLS termination**: Centraliza el manejo de certificados HTTPS, desencriptando tráfico antes de enrutarlo a servicios internos
- **Load balancing**: Distribuye carga entre múltiples instancias de servicios (configuración futura)
- **Rate limiting**: Protege contra abuso y ataques de denegación de servicio
- **Compresión gzip**: Reduce tamaño de respuestas HTTP
- **Logging centralizado**: Registra todas las peticiones para auditoría y debugging

**Patrón 2: Microservicios en Capas (Request/Response)**

Para operaciones que requieren respuesta inmediata, se implementa una arquitectura de microservicios en tres capas:

- **Capa de Presentación**: Frontend (Next.js) - Renderizado Server-Side (SSR) y gestión de interfaz de usuario
- **Capa de Lógica de Negocio**: API (FastAPI) - Endpoints REST, validación, coordinación de servicios
- **Capa de Persistencia**: PostgreSQL - Almacenamiento ACID de datos estructurados

Este patrón se emplea para casos de uso que requieren latencias <1 segundo:
- Consultas de ofertas laborales filtradas por país/fecha
- Estadísticas agregadas (skills más demandadas, tendencias)
- Consulta de estado de tareas asíncronas (polling)
- Operaciones CRUD de administración

**Patrón 3: Event-Driven Architecture (Pub/Sub)**

Para operaciones computacionalmente intensivas que no requieren respuesta inmediata, se implementa arquitectura orientada a eventos mediante el patrón Publisher/Subscriber:

- **Publishers**: API publica tareas a queue cuando recibe peticiones de procesamiento batch; Celery Beat publica tareas programadas (scraping cada 6 horas)
- **Message Queue**: Redis actúa como broker de mensajes, almacenando tareas pendientes y resultados
- **Subscribers**: Celery Workers consumen tareas de la queue, ejecutan procesamiento, y persisten resultados en PostgreSQL

Este patrón se emplea para casos de uso que requieren minutos/horas de procesamiento:
- Scraping automático de 8 portales de empleo (10-60 minutos)
- Extracción de habilidades con LLM en batch (5 segundos × N jobs)
- Limpieza masiva de datos (10,000+ registros)
- Clustering de habilidades con UMAP + HDBSCAN (2-5 minutos para 10,000 skills)

**Justificación de la Arquitectura Híbrida**

La selección de una arquitectura híbrida se fundamentó en cinco razones principales:

1. **Dualidad de requisitos de latencia**: Consultas de usuarios requieren <1s, procesamiento de datos requiere minutos/horas
2. **Escalabilidad horizontal selectiva**: Workers pueden escalarse dinámicamente (1→N) sin modificar código
3. **Simplicidad operativa con potencia de procesamiento**: Mantiene trazabilidad de sistemas modulares mientras obtiene paralelismo de sistemas distribuidos
4. **Optimización de recursos**: Request/Response evita overhead para operaciones simples; Event-Driven maximiza CPU/GPU para procesamiento intensivo
5. **Madurez del ecosistema**: Celery + Redis es combinación probada industrialmente con amplia documentación

**Comparación con Alternativas Arquitectónicas**

La Tabla 6.X presenta la evaluación de tres estilos arquitectónicos considerados:

**[INSERTAR AQUÍ: Tabla comparativa - puedes crearla basada en la que ya tenemos]**

| Criterio | Pipeline Lineal | Microservicios Puros | Arquitectura Híbrida (Seleccionada) |
|----------|----------------|---------------------|-------------------------------------|
| Complejidad implementación | Baja | Alta | Media |
| Escalabilidad horizontal | Limitada | Excelente | Excelente (workers) |
| Latencia consultas | Alta (bloqueante) | Baja | Baja (<1s) |
| Throughput procesamiento | Bajo (secuencial) | Medio | Alto (paralelo) |
| Trazabilidad | Excelente | Media | Alta |
| Tolerancia a fallos | Baja | Alta | Alta |
| Time to market | Rápido | Lento | Medio |

*Tabla 6.X: Comparación de estilos arquitectónicos evaluados. La arquitectura híbrida combina ventajas de microservicios (escalabilidad, tolerancia a fallos) con eficiencia operativa de sistemas más simples.*

El pipeline lineal fue descartado por impedir paralelismo y limitar throughput. Los microservicios puros fueron descartados por introducir complejidad innecesaria para un proyecto académico con equipo de 2 desarrolladores. La arquitectura híbrida proporciona el balance óptimo entre capacidades técnicas y viabilidad operativa.

#### **6.3.2.2 Los Siete Servicios del Sistema**

La arquitectura se descompone en siete servicios especializados, cada uno con responsabilidades claramente delimitadas. La Figura 6.Y presenta la vista de contenedores (C4 Model) que detalla cada servicio con sus tecnologías específicas:

**[INSERTAR AQUÍ: architecture_c4_container.png]**
*Figura 6.Y: Vista de Contenedores (C4 Model - Container Level). Cada contenedor representa un servicio independiente con tecnología específica, puerto de comunicación, y conexiones con otros servicios.*

Los siete servicios se describen a continuación:

**1. NGINX - API Gateway**

**Responsabilidades**:
- Punto único de entrada HTTP/HTTPS
- Routing de peticiones a servicios apropiados
- Terminación SSL/TLS
- Compresión y caching de respuestas

**Tecnología**: nginx:alpine (imagen Docker oficial)
**Puerto**: 80 (HTTP), 443 (HTTPS)

**Configuración de routing**:
```nginx
server {
    listen 80;
    server_name observatorio-laboral.com;
    
    # Redirigir HTTP a HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name observatorio-laboral.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    
    # Frontend - Interfaz de usuario
    location / {
        proxy_pass http://frontend:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    # API - Endpoints REST
    location /api/ {
        proxy_pass http://api:8000;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # Compresión gzip
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
}
```

**2. Frontend - Interfaz de Usuario**

**Responsabilidades**:
- Renderizado de páginas web (Server-Side Rendering)
- Gestión de estado de aplicación (React)
- Visualización de dashboards y estadísticas
- Polling para monitoreo de tareas asíncronas

**Tecnología**: Next.js 14, React 18, TypeScript, Tailwind CSS
**Puerto**: 3000 (interno, accesible vía Nginx en `/`)

**Patrón de comunicación con API**:

*Request/Response síncrono* (consultas rápidas):
```typescript
// Consulta de ofertas laborales
const response = await fetch('/api/jobs?country=CO&limit=10');
const data = await response.json();
// Respuesta en <1 segundo
```

*Request/Response asíncrono con polling* (procesamiento batch):
```typescript
// 1. Solicitar procesamiento de 100 jobs
const response = await fetch('/api/extract/batch', {
    method: 'POST',
    body: JSON.stringify({ job_ids: Array.from({length:100}, (_, i) => i+1) })
});
const { task_id } = await response.json(); // Respuesta inmediata con task_id

// 2. Polling cada 3 segundos para monitorear progreso
const interval = setInterval(async () => {
    const statusResponse = await fetch(`/api/tasks/${task_id}`);
    const { state, progress } = await statusResponse.json();
    
    if (state === 'SUCCESS') {
        clearInterval(interval);
        // Mostrar resultados
    } else {
        // Actualizar barra de progreso: progress%
    }
}, 3000);
```

**3. API - Lógica de Negocio**

**Responsabilidades**:
- Exponer endpoints REST para operaciones CRUD
- Validar datos de entrada (Pydantic)
- Coordinar servicios (Publisher de tareas asíncronas)
- Consultar estado de tareas en Redis
- Implementar lógica de negocio

**Tecnología**: FastAPI 0.104+, Python 3.11+, Pydantic v2, SQLAlchemy
**Puerto**: 8000 (interno, accesible vía Nginx en `/api/*`)

**Funcionalidad dual**:

El servicio API implementa dos patrones de comunicación según el tipo de operación:

*Patrón Request/Response síncrono*:
```python
@app.get("/api/jobs")
async def get_jobs(country: str = Query(...), limit: int = 10):
    """Consulta rápida de ofertas laborales (<1s)."""
    jobs = db.query(RawJob)\
             .filter_by(country=country)\
             .limit(limit)\
             .all()
    
    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs)
    }
```

*Patrón Pub/Sub asíncrono*:
```python
@app.post("/api/extract/batch")
async def extract_batch(job_ids: List[int], pipeline: str):
    """
    Procesamiento asíncrono de extracción de habilidades.
    Responde INMEDIATAMENTE con task_ids, procesamiento ocurre en background.
    """
    task_ids = []
    
    for job_id in job_ids:
        # Publica tarea a Redis queue (NO espera resultado)
        task = extract_skills_task.delay(job_id, pipeline)
        task_ids.append(task.id)
    
    # Respuesta inmediata (<100ms)
    return {
        "batch_id": f"batch_{uuid.uuid4()}",
        "task_ids": task_ids,
        "status": "QUEUED",
        "total": len(job_ids)
    }

@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Consulta estado de tarea asíncrona (polling desde Frontend)."""
    result = AsyncResult(task_id, app=celery_app)
    
    return {
        "task_id": task_id,
        "state": result.state,  # PENDING, STARTED, SUCCESS, FAILURE
        "progress": result.info.get('progress', 0) if result.info else 0,
        "result": result.result if result.successful() else None,
        "error": str(result.info) if result.failed() else None
    }
```

**Endpoints principales**:
- `GET /api/jobs` - Lista ofertas laborales (filtros: país, fecha, estado)
- `GET /api/stats` - Estadísticas agregadas (skills por país, tendencias temporales)
- `GET /api/skills` - Habilidades extraídas (con normalización ESCO)
- `GET /api/clusters` - Resultados de clustering (métricas, etiquetas)
- `POST /api/admin/scrape` - Trigger manual de scraping
- `POST /api/extract/batch` - Extracción batch con LLM (asíncrono)
- `POST /api/jobs/clean/batch` - Limpieza masiva (asíncrono)
- `GET /api/tasks/{task_id}` - Estado de tarea asíncrona

**4. PostgreSQL - Base de Datos**

**Responsabilidades**:
- Persistencia ACID de datos estructurados
- Almacenamiento de embeddings 768D (extensión pgvector)
- Garantizar trazabilidad mediante relaciones foreign key
- Optimización de consultas mediante índices

**Tecnología**: PostgreSQL 15+, extensión pgvector 0.5+
**Puerto**: 5433 (host) → 5432 (contenedor)

El diseño de base de datos se detalla en la Sección 6.3.6.

**5. Redis - Message Queue y Cache**

**Responsabilidades**:
- Cola de mensajes para patrón Pub/Sub (Celery broker)
- Almacenamiento de resultados de tareas (Celery result backend)
- Cache de queries frecuentes (TTL configurable)
- Gestión de estado de tareas

**Tecnología**: Redis 7.x (imagen Docker oficial)
**Puerto**: 6379

**Configuración como broker de Celery**:
```python
# settings.py
CELERY_BROKER_URL = 'redis://redis:6379/0'
CELERY_RESULT_BACKEND = 'redis://redis:6379/1'
CELERY_RESULT_EXPIRES = 86400  # 24 horas
```

**Uso como cache**:
```python
import redis
import json

redis_client = redis.Redis(host='redis', port=6379, db=2)

@app.get("/api/stats")
async def get_stats(country: str):
    cache_key = f"stats:{country}"
    
    # Intenta obtener de cache
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    
    # Si no existe, consulta DB
    stats = compute_stats(country)  # Consulta costosa a PostgreSQL
    
    # Almacena en cache (TTL 5 minutos)
    redis_client.setex(cache_key, 300, json.dumps(stats))
    
    return stats
```

**6. Celery Beat - Programador de Tareas**

**Responsabilidades**:
- Programar tareas periódicas (cron-like)
- Publicar tareas programadas a Redis queue
- Gestionar schedules de scraping automático

**Tecnología**: Celery 5.x, Python 3.11+
**Puerto**: N/A (no expone puertos)

**Configuración de tareas periódicas**:
```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    # Scraping cada 6 horas
    'scrape-all-portals': {
        'task': 'tasks.scrape_all_portals',
        'schedule': crontab(hour='*/6'),
    },
    # Limpieza de datos antiguos (diaria a las 3 AM)
    'clean-old-data': {
        'task': 'tasks.clean_old_jobs',
        'schedule': crontab(hour=3, minute=0),
    },
    # Recalculo de estadísticas (semanal, lunes 8 AM)
    'update-statistics': {
        'task': 'tasks.update_statistics',
        'schedule': crontab(hour=8, minute=0, day_of_week=1),
    },
}
```

**7. Celery Workers - Procesadores Distribuidos**

**Responsabilidades**:
- Consumir tareas de Redis queue
- Ejecutar pipeline CRISP-DM de procesamiento de datos
- Procesar tareas en paralelo (múltiples workers)
- Persistir resultados en PostgreSQL
- Reportar progreso de tareas

**Tecnología**: Celery 5.x, Python 3.11+, con soporte GPU (CUDA) si disponible
**Puerto**: N/A (no expone puertos)

**Escalabilidad horizontal**:

Los workers pueden escalarse dinámicamente sin cambios de código:

```bash
# Iniciar con 1 worker
docker-compose up -d celery_worker

# Escalar a 8 workers (8x throughput teórico)
docker-compose up -d --scale celery_worker=8

# Sin cambios de código, sin reconfiguración
# Load balancing automático por Redis
```

**Ejemplo de throughput**:
- 1 worker: 100 jobs × 5s = 500 segundos (8 min 20 seg)
- 4 workers: 100 jobs ÷ 4 = 125 segundos (2 min 5 seg)
- 8 workers: 100 jobs ÷ 8 = 62.5 segundos (1 min 2 seg)

**Tareas procesadas por workers**:
1. Scraping de portales (Scrapy + Selenium): 5-10 min por portal
2. Extracción NER+Regex (spaCy): 100-200ms por job
3. Procesamiento LLM (Gemma 3 4B): 2-5s por job
4. Normalización ESCO (fuzzy matching): 50-100ms por skill
5. Generación embeddings (E5 multilingual): 100ms/batch de 32
6. Clustering (UMAP + HDBSCAN): 2-5 min para 10K skills

#### **6.3.2.3 Patrones de Comunicación: Request/Response y Pub/Sub**

El sistema emplea dos patrones fundamentales de comunicación según requisitos de latencia:

**Patrón Request/Response (Síncrono)**

```
Usuario → Frontend → API → PostgreSQL → API → Frontend → Usuario
Tiempo: <1 segundo
```

**Casos de uso**:
- Consultas de datos ya procesados
- Estadísticas agregadas
- Operaciones CRUD de administración
- Polling de estado de tareas

**Ventajas**:
- Latencia predecible y baja
- Simplicidad de implementación
- Fácil debugging y trazabilidad

**Patrón Pub/Sub (Asíncrono)**

```
API/Beat → Redis Queue → Workers (1...N) → PostgreSQL
Frontend → API: Polling GET /api/tasks/{id} cada 3s
Tiempo: Variable (procesamiento en background)
```

**Casos de uso**:
- Scraping automático programado
- Extracción batch con LLM (100+ jobs)
- Limpieza masiva de datos (10K+ registros)
- Clustering de habilidades

**Ventajas**:
- No bloquea al usuario (respuesta inmediata)
- Procesamiento paralelo distribuido
- Escalabilidad horizontal
- Tolerancia a fallos (reintentos automáticos)

**Decisión de qué patrón usar**:

La decisión se basa en tiempo estimado de procesamiento:

- Operación estimada <5 segundos → Request/Response síncrono
- Operación estimada >5 segundos → Pub/Sub asíncrono con polling

---

### **6.3.3 Vista Física: Infraestructura y Despliegue**

La vista física describe el mapeo de componentes lógicos sobre infraestructura física, especificando hardware, contenedores Docker, configuración de red, y estrategia de despliegue. Esta sección detalla la topología de deployment que materializa la arquitectura lógica presentada en la sección anterior.

**[INSERTAR AQUÍ: architecture_physical_view.png]**
*Figura 6.Z: Vista Física / Deployment View. El diagrama muestra el servidor de producción con especificaciones de hardware, los 10 contenedores Docker orquestados por Docker Compose, mapeo de puertos, red bridge interna, y volúmenes persistentes.*

#### **6.3.3.1 Especificaciones del Servidor**

El sistema se despliega en un servidor único que ejecuta todos los servicios mediante contenedores Docker. Las especificaciones mínimas recomendadas son:

**Hardware / Virtual Machine**:
- **Sistema Operativo**: Ubuntu Server 24.04 LTS
- **CPU**: 8 cores @ 2.4 GHz (Intel Xeon o AMD EPYC)
- **RAM**: 16 GB DDR4
- **Storage**: 500 GB SSD (NVMe recomendado)
- **Network**: 1 Gbps
- **GPU** (opcional): NVIDIA con 8GB VRAM para aceleración de LLM inference

**Software Base**:
- Docker Engine 24.0+
- Docker Compose v2
- NVIDIA Container Toolkit (si se usa GPU)

**Firewall**:
- Puertos abiertos: 80 (HTTP), 443 (HTTPS)
- Todos los demás puertos bloqueados externamente
- Comunicación interna entre contenedores vía red Docker

#### **6.3.3.2 Contenedores Docker y Orquestación**

El sistema se compone de 10 contenedores Docker orquestados mediante Docker Compose:

**Contenedores de Servicios Principales** (5):

| Servicio | Imagen | Puerto Host→Container | CPU | RAM | Volumen |
|----------|--------|----------------------|-----|-----|---------|
| nginx | nginx:alpine | 80→80, 443→443 | 1 | 1 GB | - |
| frontend | frontend:latest | 3000→3000 | 1 | 1 GB | - |
| api | api:latest | 8000→8000 | 1 | 1 GB | - |
| postgres | postgres:15 | 5433→5432 | 2 | 4 GB | postgres_data (100GB) |
| redis | redis:7-alpine | 6379→6379 | 1 | 2 GB | redis_data (10GB) |

**Contenedores de Procesamiento** (5):

| Servicio | Imagen | Puerto | CPU | RAM | GPU | Escalable |
|----------|--------|--------|-----|-----|-----|-----------|
| celery_beat | celery:latest | N/A | 0.5 | 512 MB | No | No |
| celery_worker | celery:latest | N/A | 2 | 4 GB | Sí (opcional) | **Sí (1→N)** |

**Nota**: `celery_worker` puede replicarse dinámicamente (1, 2, 4, 8, ... N instancias) sin cambios de código mediante el comando:
```bash
docker-compose up -d --scale celery_worker=N
```

**Configuración Docker Compose**:

El archivo `docker-compose.yml` orquesta todos los servicios:

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    networks:
      - labor_observatory_network
    depends_on:
      - frontend
      - api
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: frontend:latest
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=http://api:8000
    networks:
      - labor_observatory_network
    restart: unless-stopped

  api:
    build:
      context: ./api
      dockerfile: Dockerfile.api
    image: api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/labor_observatory
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    networks:
      - labor_observatory_network
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  postgres:
    image: postgres:15
    ports:
      - "5433:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=labor_observatory
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    networks:
      - labor_observatory_network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - labor_observatory_network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 2G
    restart: unless-stopped

  celery_beat:
    build:
      context: ./api
      dockerfile: Dockerfile.api
    image: celery:latest
    command: celery -A tasks beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/labor_observatory
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
    networks:
      - labor_observatory_network
    depends_on:
      - redis
      - postgres
    restart: unless-stopped

  celery_worker:
    build:
      context: ./api
      dockerfile: Dockerfile.api
    image: celery:latest
    command: celery -A tasks worker --loglevel=info --concurrency=2
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/labor_observatory
      - REDIS_URL=redis://redis:6379
      - CELERY_BROKER_URL=redis://redis:6379/0
      - CELERY_RESULT_BACKEND=redis://redis:6379/1
    networks:
      - labor_observatory_network
    depends_on:
      - redis
      - postgres
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
    restart: unless-stopped

networks:
  labor_observatory_network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.18.0.0/16
          gateway: 172.18.0.1

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  logs_data:
    driver: local
```

#### **6.3.3.3 Configuración de Red y Volúmenes**

**Red Docker (Bridge)**:

Todos los contenedores se conectan a una red bridge interna que proporciona:

- **Subnet**: 172.18.0.0/16 (65,536 direcciones IP disponibles)
- **Gateway**: 172.18.0.1
- **DNS interno**: Resolución automática por nombre de servicio
  - Ejemplo: `postgres` resuelve automáticamente a IP del contenedor PostgreSQL
  - Ejemplo: `http://api:8000` es accesible desde frontend sin conocer IP

**Aislamiento de red**:
- Contenedores solo pueden comunicarse entre sí dentro de la red
- Solo nginx expone puertos externamente (80, 443)
- PostgreSQL y Redis no son accesibles desde fuera del servidor

**Volúmenes Persistentes**:

Los datos que deben persistir entre reinicios de contenedores se almacenan en volúmenes Docker:

| Volumen | Mount Point | Tamaño | Contenido |
|---------|------------|--------|-----------|
| postgres_data | /var/lib/postgresql/data | 100 GB | Base de datos completa |
| redis_data | /data | 10 GB | Dumps de Redis, snapshots |
| logs_data | /var/log | 20 GB | Logs de todos los servicios |

**Estrategia de backup**:
- Backup diario de `postgres_data` mediante pg_dump
- Snapshots de volúmenes Docker semanalmente
- Logs rotados cada 7 días, comprimidos y archivados

---

### **6.3.4 Vista de Procesos: Ejecución y Concurrencia**

La vista de procesos describe el comportamiento dinámico del sistema en tiempo de ejecución, abordando aspectos de concurrencia, distribución de procesamiento, throughput, y escalabilidad. Esta sección presenta el pipeline CRISP-DM que ejecutan los workers, la estrategia de escalamiento horizontal, y la gestión de tareas asíncronas.

#### **6.3.4.1 Pipeline CRISP-DM y Flujo de Procesamiento**

El procesamiento de datos sigue la metodología CRISP-DM (Cross-Industry Standard Process for Data Mining) adaptada al dominio de análisis de mercado laboral. El pipeline se compone de 7 etapas secuenciales ejecutadas por los Celery Workers:

**[INSERTAR AQUÍ: Diagrama del pipeline CRISP-DM si lo tienes, o la parte inferior de architecture_diagram.png]**

**Etapa 1: Scraping**
- **Entrada**: URLs de portales de empleo (8 portales × 3 países)
- **Proceso**: Scrapy + Selenium para recolección automatizada
- **Salida**: Raw jobs almacenados en tabla `raw_jobs`
- **Tiempo**: 5-10 minutos por portal
- **Deduplicación**: Hash SHA-256 de (título + empresa + ubicación + fecha)

**Etapa 2: Cleaning**
- **Entrada**: Raw jobs de tabla `raw_jobs`
- **Proceso**: Normalización de texto, eliminación de HTML, detección de idioma
- **Salida**: Cleaned jobs en tabla `cleaned_jobs` con campo `is_usable`
- **Tiempo**: 50-100ms por job

**Etapa 3: Extraction**
- **Entrada**: Cleaned jobs
- **Proceso**: **Aquí se usan los Pipelines A o B** (NER+Regex vs LLM)
- **Salida**: Extracted skills en tabla `extracted_skills`
- **Tiempo**: 100-200ms (Pipeline A) o 2-5s (Pipeline B) por job

**Nota importante**: Los Pipelines A y B son **variantes experimentales de esta etapa**. No son arquitecturas separadas, sino métodos alternativos de extracción comparados en el Capítulo 8 (Resultados).

**Etapa 4: Enhancement**
- **Entrada**: Extracted skills
- **Proceso**: Normalización con LLM, inferencia de skills implícitas, mapeo a ESCO
- **Salida**: Enhanced skills en tabla `enhanced_skills`
- **Tiempo**: 1-3s por job

**Etapa 5: Embedding**
- **Entrada**: Enhanced skills (texto normalizado)
- **Proceso**: Generación de embeddings 768D con modelo E5-multilingual
- **Salida**: Vectores en tabla `skill_embeddings` (pgvector)
- **Tiempo**: 100ms por batch de 32 skills

**Etapa 6: Clustering**
- **Entrada**: Skill embeddings (10,000+ vectores 768D)
- **Proceso**: Reducción UMAP (768D → 2D/3D), clustering HDBSCAN
- **Salida**: Clusters con etiquetas en tabla `clustering_results`
- **Tiempo**: 2-5 minutos para 10K skills

**Etapa 7: Visualization**
- **Entrada**: Clustering results
- **Proceso**: Generación de gráficos (scatter plots, heatmaps, tendencias temporales)
- **Salida**: Imágenes PNG, datos JSON para frontend
- **Tiempo**: 10-30 segundos

**Ejecución del pipeline completo**:

```python
@celery_app.task(bind=True)
def process_job_complete_pipeline(self, job_id: int):
    """
    Ejecuta pipeline CRISP-DM completo para un job.
    Reporta progreso a través de self.update_state().
    """
    # Etapa 1-2: Ya realizadas (Scraping + Cleaning)
    job = db.query(RawJob).filter_by(id=job_id).first()
    
    # Etapa 3: Extraction (usa Pipeline A o B según configuración)
    self.update_state(state='STARTED', meta={'stage': 'extraction', 'progress': 20})
    skills = extract_skills(job, pipeline=settings.EXTRACTION_PIPELINE)
    
    # Etapa 4: Enhancement
    self.update_state(state='STARTED', meta={'stage': 'enhancement', 'progress': 40})
    enhanced_skills = enhance_skills(skills)
    
    # Etapa 5: Embedding
    self.update_state(state='STARTED', meta={'stage': 'embedding', 'progress': 60})
    embeddings = generate_embeddings(enhanced_skills)
    
    # Etapa 6: Clustering (solo si es el último job del batch)
    if is_last_job_in_batch(job_id):
        self.update_state(state='STARTED', meta={'stage': 'clustering', 'progress': 80})
        clusters = perform_clustering(embeddings)
        
        # Etapa 7: Visualization
        self.update_state(state='STARTED', meta={'stage': 'visualization', 'progress': 90})
        visualizations = create_visualizations(clusters)
    
    return {
        'job_id': job_id,
        'skills_extracted': len(skills),
        'skills_enhanced': len(enhanced_skills),
        'status': 'completed'
    }
```

#### **6.3.4.2 Escalabilidad Horizontal de Workers**

La arquitectura permite escalamiento horizontal dinámico de workers sin modificar código ni reconfigurar servicios:

**Comando de escalamiento**:
```bash
docker-compose up -d --scale celery_worker=N
```

**Ejemplo de escalamiento 1→8 workers**:

```bash
# Estado inicial: 1 worker
$ docker-compose ps
NAME                  IMAGE            STATUS
celery_worker_1       celery:latest    Up

# Escalar a 8 workers
$ docker-compose up -d --scale celery_worker=8

# Nuevo estado: 8 workers en paralelo
$ docker-compose ps
NAME                  IMAGE            STATUS
celery_worker_1       celery:latest    Up
celery_worker_2       celery:latest    Up
celery_worker_3       celery:latest    Up
celery_worker_4       celery:latest    Up
celery_worker_5       celery:latest    Up
celery_worker_6       celery:latest    Up
celery_worker_7       celery:latest    Up
celery_worker_8       celery:latest    Up
```

**Load balancing automático**:

Redis distribuye tareas equitativamente entre workers disponibles:

```
Redis Queue (100 tareas pendientes)
    ├── Worker 1: Procesa tareas [1, 9, 17, 25, ...]   (~12 tareas)
    ├── Worker 2: Procesa tareas [2, 10, 18, 26, ...]  (~12 tareas)
    ├── Worker 3: Procesa tareas [3, 11, 19, 27, ...]  (~12 tareas)
    ├── Worker 4: Procesa tareas [4, 12, 20, 28, ...]  (~12 tareas)
    ├── Worker 5: Procesa tareas [5, 13, 21, 29, ...]  (~13 tareas)
    ├── Worker 6: Procesa tareas [6, 14, 22, 30, ...]  (~13 tareas)
    ├── Worker 7: Procesa tareas [7, 15, 23, 31, ...]  (~13 tareas)
    └── Worker 8: Procesa tareas [8, 16, 24, 32, ...]  (~13 tareas)
```

**Impacto en throughput**:

| Workers | Tareas Totales | Tiempo Promedio por Tarea | Tiempo Total | Speedup |
|---------|----------------|---------------------------|--------------|---------|
| 1 | 100 | 5s | 500s (8 min 20s) | 1x |
| 2 | 100 | 5s | 250s (4 min 10s) | 2x |
| 4 | 100 | 5s | 125s (2 min 5s) | 4x |
| 8 | 100 | 5s | 62.5s (1 min 2s) | 8x |

*Nota*: Speedup teórico asume tareas independientes sin contención de recursos (CPU, DB, Redis). En práctica, speedup real es ~0.7×N debido a overhead de comunicación y contención.

**Tolerancia a fallos**:

Si un worker falla, los demás continúan procesando:

```bash
# Worker 3 falla (simulación)
$ docker stop labor_observatory_celery_worker_3

# Redis redistribuye tareas pendientes a workers restantes
# Workers 1, 2, 4, 5, 6, 7, 8 continúan procesando
# Tarea que estaba ejecutando Worker 3 se reintenta en otro worker
```

**Reintentos automáticos**:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_skills_task(self, job_id: int):
    try:
        # Procesamiento
        result = extract_skills(job_id)
        return result
    except Exception as exc:
        # Reintenta hasta 3 veces con delay de 60s
        raise self.retry(exc=exc, countdown=60)
```

#### **6.3.4.3 Gestión de Tareas Asíncronas**

**Ciclo de vida de una tarea**:

```
1. QUEUED    → Tarea publicada a Redis queue
2. PENDING   → Tarea en queue, esperando worker disponible
3. STARTED   → Worker tomó la tarea, comenzó procesamiento
4. PROGRESS  → Worker reporta progreso (20%, 40%, 60%, ...)
5. SUCCESS   → Tarea completada exitosamente, resultado disponible
   o
   FAILURE   → Tarea falló, error almacenado
```

**Monitoreo desde Frontend**:

```typescript
interface TaskStatus {
    task_id: string;
    state: 'PENDING' | 'STARTED' | 'SUCCESS' | 'FAILURE';
    progress: number;  // 0-100
    result: any;
    error: string | null;
}

async function monitorTask(taskId: string): Promise<void> {
    const interval = setInterval(async () => {
        const response = await fetch(`/api/tasks/${taskId}`);
        const status: TaskStatus = await response.json();
        
        // Actualizar UI con progreso
        updateProgressBar(status.progress);
        updateStatusText(status.state);
        
        // Si completó (éxito o fallo), detener polling
        if (status.state === 'SUCCESS') {
            clearInterval(interval);
            showResults(status.result);
        } else if (status.state === 'FAILURE') {
            clearInterval(interval);
            showError(status.error);
        }
    }, 3000);  // Polling cada 3 segundos
}
```

**Métricas de rendimiento**:

El sistema registra métricas para cada tarea:
- Tiempo de espera en queue (QUEUED → STARTED)
- Tiempo de ejecución (STARTED → SUCCESS/FAILURE)
- Tasa de éxito/fallo
- Throughput (tareas/minuto)

Estas métricas permiten optimizar número de workers y detectar cuellos de botella.

---

### **6.3.5 Integración de Vistas: Arquitectura Completa**

Las tres vistas arquitectónicas se integran para formar una especificación completa del sistema:

**Vista Lógica** proporciona la descomposición funcional en 7 servicios especializados que implementan tres patrones arquitectónicos (API Gateway, Microservicios en Capas, Event-Driven).

**Vista Física** mapea estos servicios lógicos sobre 10 contenedores Docker ejecutándose en un servidor con especificaciones definidas, conectados por red bridge interna y persistiendo datos en volúmenes Docker.

**Vista de Procesos** describe el comportamiento dinámico mediante el pipeline CRISP-DM de 7 etapas ejecutado por workers escalables horizontalmente, con gestión de tareas asíncronas y métricas de rendimiento.

**Mapeo entre vistas**:

| Vista Lógica (Servicio) | Vista Física (Container) | Vista de Procesos (Ejecución) |
|------------------------|-------------------------|------------------------------|
| NGINX | nginx:alpine en puerto 80/443 | Enruta requests HTTP/HTTPS |
| Frontend | frontend:latest en puerto 3000 | Renderiza UI + Polling asíncrono |
| API | api:latest en puerto 8000 | Publisher de tareas + Request/Response |
| PostgreSQL | postgres:15 con volumen 100GB | Persistencia ACID de datos |
| Redis | redis:7 con volumen 10GB | Message queue + Cache |
| Celery Beat | celery:latest sin puerto | Scheduler de tareas periódicas |
| Celery Workers | celery:latest × N (escalable) | Ejecuta pipeline CRISP-DM en paralelo |

**Flujo end-to-end completo**:

```
Usuario solicita procesamiento de 100 jobs:

[Vista Lógica]
  Usuario → Frontend → API → Redis (publica 100 tareas)
  
[Vista Física]
  HTTPS:443 → nginx:80 → frontend:3000 → api:8000 → redis:6379
  
[Vista de Procesos]
  Workers (1-8) consumen tareas de Redis queue
  Cada worker ejecuta pipeline CRISP-DM (7 etapas)
  Resultados se persisten en PostgreSQL
  Frontend hace polling cada 3s para monitorear progreso
  
[Resultado]
  100 jobs procesados en 62-500s (según N workers)
  Usuario ve resultados en dashboard
```

Esta integración de vistas proporciona una especificación arquitectónica completa, no ambigua, y reproducible del sistema.

---

### **6.3.6 Diseño de la Base de Datos**

[MANTENER EL CONTENIDO EXISTENTE DE LA SECCIÓN 6.3.3 "Diseño de la Base de Datos" DEL DOCUMENTO ORIGINAL]

[Aquí va el diagrama ER, las 6 tablas, las relaciones foreign key, etc. que ya tienes en tu documento]

---

## 📊 Resumen de Cambios

### ❌ Eliminar del documento actual:
- Sección 6.3.1 "Selección del Estilo Arquitectónico" (descripción de pipeline lineal)
- Referencias a "arquitectura de pipeline lineal"
- Tabla 6.3 con comparación incorrecta de arquitecturas
- Figura 6.1 si muestra pipeline lineal

### ✅ Agregar al documento:
- Nueva sección 6.3.1 "Modelo de Vistas Arquitectónicas"
- Nueva sección 6.3.2 "Vista Lógica" con subsecciones
- Nueva sección 6.3.3 "Vista Física" con subsecciones
- Nueva sección 6.3.4 "Vista de Procesos" con subsecciones
- Nueva sección 6.3.5 "Integración de Vistas"
- Mantener sección 6.3.6 "Diseño de Base de Datos" (ya existente)

### 📐 Diagramas a insertar:
1. **Figura 6.X**: architecture_diagram.png (Vista Lógica general)
2. **Figura 6.Y**: architecture_c4_container.png (Vista Lógica detallada)
3. **Figura 6.Z**: architecture_physical_view.png (Vista Física)
4. **Figura 6.W** (opcional): niveles_sistema_explicacion.png (Explicación de niveles)

### 📏 Tablas a crear:
1. **Tabla 6.X**: Comparación de arquitecturas (con columna "Arquitectura Híbrida")
2. **Tabla 6.Y**: Especificaciones de contenedores Docker
3. **Tabla 6.Z**: Distribución de recursos (CPU/RAM)
4. **Tabla 6.W**: Ciclo de vida de tareas asíncronas

---

## 🎯 Instrucciones de Implementación

1. **Backup**: Hacer copia de seguridad del documento main.pdf actual

2. **Reemplazar Sección 6.3 completa**: Usar el texto propuesto arriba

3. **Insertar diagramas** en las ubicaciones marcadas con [INSERTAR AQUÍ]

4. **Crear tablas** según especificaciones (usar datos de los documentos MD)

5. **Actualizar índice** con nueva numeración de subsecciones

6. **Revisar referencias cruzadas**: Si hay menciones a "pipeline lineal" en otros capítulos, actualizarlas a "arquitectura híbrida"

7. **Actualizar Abstract/Resumen**: Mencionar arquitectura híbrida en lugar de pipeline lineal

---

## 📋 Checklist de Revisión

Antes de finalizar, verificar:

- [ ] Todas las figuras están insertadas y numeradas correctamente
- [ ] Todas las tablas están creadas y numeradas
- [ ] No quedan referencias a "pipeline lineal" como arquitectura
- [ ] Se explica claramente que Pipelines A/B son variantes de etapa "Extraction"
- [ ] Índice actualizado con nueva estructura
- [ ] Referencias cruzadas funcionan correctamente
- [ ] Formato consistente (fonts, tamaños, espaciado)
- [ ] Pie de página de figuras es descriptivo
- [ ] Código fuente tiene syntax highlighting si es posible

---

**Esta propuesta reemplaza completamente la sección 6.3 con documentación arquitectónica profesional siguiendo el modelo 4+1 de vistas, corrigiendo todos los errores identificados en el documento original.**
