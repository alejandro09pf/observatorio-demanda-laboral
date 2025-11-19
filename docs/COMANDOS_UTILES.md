# Comandos Útiles del Observatorio de Demanda Laboral

## Activación del Entorno Virtual

```bash
# Activar el entorno virtual de Python
source venv/bin/activate

# Desactivar el entorno virtual
deactivate
```

## Comandos Básicos del Orquestador

El orquestador se ejecuta con el comando `python -m src.orchestrator` (o `python3 -m src.orchestrator` si estás en un sistema que lo requiere).

### 1. Ver ayuda y comandos disponibles

```bash
# Ver todos los comandos disponibles
python -m src.orchestrator --help

# Ver ayuda de un comando específico
python -m src.orchestrator [comando] --help
```

### 2. Scraping de Ofertas Laborales

```bash
# Ejecutar un scraper específico para un país
python -m src.orchestrator run-single-spider computrabajo CO --limit 100

# Ejecutar todos los scrapers para un país
python -m src.orchestrator run CO --limit 500

# Ejecutar scrapers para múltiples países
python -m src.orchestrator run CO,MX,AR --limit 1000

# Ver lista de scrapers disponibles
python -m src.orchestrator list-spiders

# Ver estado actual de los scrapers
python -m src.orchestrator status
```

### 3. Procesamiento de Ofertas (Limpieza y Extracción)

```bash
# Procesar ofertas pendientes (limpieza + extracción de skills)
python -m src.orchestrator process-jobs --limit 100

# Procesar con límite de jobs
python -m src.orchestrator process-jobs --limit 500 --batch-size 50

# Ejecutar Pipeline A.1 (TF-IDF + N-grams) en Gold Standard
python -m src.orchestrator process-pipeline-a
```

### 4. Pipeline B - LLM (Extracción con LLMs)

```bash
# Descargar modelos LLM necesarios
python -m src.orchestrator llm-download-models --models gemma-3-4b-instruct

# Ver modelos disponibles
python -m src.orchestrator llm-list-models

# Procesar ofertas con LLM (Pipeline B)
python -m src.orchestrator llm-process-jobs --limit 100 --model gemma-3-4b-instruct

# Procesar Gold Standard con LLM
python -m src.orchestrator process-gold-standard --model gemma-3-4b-instruct

# Comparar múltiples modelos LLM
python -m src.orchestrator llm-compare-models --models gemma-3-4b-instruct,phi-3.5-mini --limit 50

# Probar un modelo específico
python -m src.orchestrator llm-test --model gemma-3-4b-instruct
```

### 5. Embeddings y Clustering

```bash
# Generar embeddings para skills extraídas
python -m src.orchestrator generate-embeddings --limit 1000

# Construir índice FAISS para búsqueda de similaridad
python -m src.orchestrator build-faiss-index

# Probar embeddings con una skill de ejemplo
python -m src.orchestrator test-embeddings --query "Python"

# Ejecutar clustering de skills (HDBSCAN)
python -m src.orchestrator cluster --config-name pipeline_a_300_post

# Ejecutar clustering en todas las configuraciones finales
python -m src.orchestrator cluster-all-final
```

### 6. Gestión de Jobs y Salud del Sistema

```bash
# Ver lista de jobs recientes
python -m src.orchestrator list-jobs --limit 20

# Forzar procesamiento de un job específico
python -m src.orchestrator force-job JOB_ID

# Ver salud del sistema (conexiones DB, servicios)
python -m src.orchestrator health
```

### 7. Automatización

```bash
# Iniciar automatización de scraping programado
python -m src.orchestrator start-automation

# Ver estado de la automatización
python -m src.orchestrator automation-status
```

### 8. Limpieza y Mantenimiento

```bash
# Limpiar archivos temporales y logs antiguos
python -m src.orchestrator clean --days 30
```

## Comandos de Base de Datos (PostgreSQL)

### Conexión a la Base de Datos

```bash
# Conectar a la base de datos
PGPASSWORD=123456 psql -h localhost -p 5433 -U labor_user -d labor_observatory

# O alternativamente:
export PGPASSWORD=123456
psql -h localhost -p 5433 -U labor_user -d labor_observatory
```

### Comandos útiles en psql

```sql
-- Ver todas las tablas
\dt

-- Ver estructura de una tabla
\d raw_jobs

-- Ver tamaño de las tablas
\dt+

-- Salir de psql
\q
```

### Backup y Restore

```bash
# Crear backup de la base de datos
pg_dump -h localhost -p 5433 -U labor_user -d labor_observatory > backup_$(date +%Y%m%d).sql

# Restaurar desde backup
PGPASSWORD=123456 psql -h localhost -p 5433 -U labor_user -d labor_observatory < backup.sql

# Backup con formato custom (más compacto)
pg_dump -h localhost -p 5433 -U labor_user -d labor_observatory -Fc > backup_$(date +%Y%m%d).dump

# Restore desde dump custom
pg_restore -h localhost -p 5433 -U labor_user -d labor_observatory backup.dump
```

## Flujos de Trabajo Comunes

### Flujo Completo: Scraping → Procesamiento → Análisis

```bash
# 1. Activar entorno virtual
source venv/bin/activate

# 2. Ejecutar scraping
python -m src.orchestrator run CO --limit 1000

# 3. Procesar ofertas (limpieza + extracción básica)
python -m src.orchestrator process-jobs --limit 1000

# 4. Procesar con LLM (Pipeline B)
python -m src.orchestrator llm-process-jobs --limit 300 --model gemma-3-4b-instruct

# 5. Generar embeddings
python -m src.orchestrator generate-embeddings --limit 1000

# 6. Ejecutar clustering
python -m src.orchestrator cluster --config-name pipeline_b_300_post
```

### Análisis del Gold Standard

```bash
# 1. Procesar con Pipeline A.1
python -m src.orchestrator process-pipeline-a

# 2. Procesar con Pipeline B (LLM)
python -m src.orchestrator process-gold-standard --model gemma-3-4b-instruct

# 3. Ejecutar queries SQL para comparar resultados
PGPASSWORD=123456 psql -h localhost -p 5433 -U labor_user -d labor_observatory -f useful_queries.sql
```

### Comparación de Modelos LLM

```bash
# Comparar varios modelos en un subset de ofertas
python -m src.orchestrator llm-compare-models \
  --models gemma-3-4b-instruct,phi-3.5-mini,qwen2.5-3b-instruct \
  --limit 100

# Ver resultados en la base de datos
PGPASSWORD=123456 psql -h localhost -p 5433 -U labor_user -d labor_observatory -c "
SELECT llm_model, COUNT(*) as jobs, AVG(llm_confidence) as avg_conf
FROM enhanced_skills
WHERE is_duplicate = false
GROUP BY llm_model;"
```

## Variables de Entorno Importantes

Estas variables deben estar configuradas en el archivo `.env` en la raíz del proyecto:

```bash
# Base de datos
DATABASE_URL=postgresql://labor_user:123456@localhost:5433/labor_observatory

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
LLM_DEFAULT_MODEL=gemma-3-4b-instruct
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2000

# OpenAI (si usas modelos de OpenAI)
OPENAI_API_KEY=tu_api_key_aqui

# Paths
DATA_DIR=./data
OUTPUTS_DIR=./outputs
LOGS_DIR=./logs
```

## Troubleshooting

### Problema: Error de conexión a la base de datos

```bash
# Verificar que PostgreSQL esté corriendo
pg_isready -h localhost -p 5433

# Ver logs de PostgreSQL (depende de tu instalación)
tail -f /usr/local/var/log/postgres.log  # macOS con Homebrew
```

### Problema: Ollama no responde

```bash
# Verificar que Ollama esté corriendo
curl http://localhost:11434/api/tags

# Iniciar Ollama si no está corriendo
ollama serve

# Ver modelos disponibles
ollama list
```

### Problema: Módulos de Python no encontrados

```bash
# Asegurarse de que el entorno virtual esté activado
source venv/bin/activate

# Reinstalar dependencias
pip install -r requirements.txt

# Verificar que PYTHONPATH esté configurado (si es necesario)
export PYTHONPATH=src
```

### Problema: Permisos insuficientes

```bash
# Dar permisos de ejecución a scripts
chmod +x src/orchestrator.py

# Verificar permisos de directorios de datos
ls -la data/ outputs/ logs/
```

## Monitoreo y Logs

### Ver logs en tiempo real

```bash
# Ver logs del orquestador
tail -f logs/orchestrator.log

# Ver logs de scraping
tail -f logs/scrapy.log

# Ver logs de procesamiento
tail -f logs/processing.log
```

### Buscar errores en logs

```bash
# Buscar errores en todos los logs
grep -r "ERROR" logs/

# Buscar warnings
grep -r "WARNING" logs/

# Ver últimos errores
grep "ERROR" logs/*.log | tail -20
```

## Recursos Adicionales

- Documentación del proyecto: `docs/`
- Manual del sistema: `docs/SISTEMA_COMPLETO_MANUAL.md`
- Queries SQL útiles: `useful_queries.sql`
- Análisis del dataset: `docs/DATASET_ANALYSIS.md`
- Resultados de evaluación: `docs/EVALUATION_MASTER_RESULTS.md`

## Notas Importantes

1. **Siempre activa el entorno virtual** antes de ejecutar cualquier comando de Python
2. **Verifica la conexión a la base de datos** con `python -m src.orchestrator health`
3. **Los logs son tu amigo**: revisa los logs cuando algo no funcione
4. **Usa límites pequeños primero** cuando pruebes nuevas configuraciones
5. **Haz backups regularmente** de la base de datos, especialmente del gold standard
