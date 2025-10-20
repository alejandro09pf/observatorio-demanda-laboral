# Guía de Scraping - Observatorio Demanda Laboral

## 📋 Tabla de Contenidos
- [Inicio Rápido](#inicio-rápido)
- [Scrapers Disponibles](#scrapers-disponibles)
- [Comandos Principales](#comandos-principales)
- [Configuración Avanzada](#configuración-avanzada)
- [Datos Actuales](#datos-actuales)

---

## 🚀 Inicio Rápido

### Prerequisitos
```bash
# 1. Iniciar PostgreSQL
docker-compose up -d

# 2. Verificar que esté corriendo
docker-compose ps
```

### Ejecutar Scraper (Modo Simple)
```bash
# Computrabajo Colombia - 5 páginas (default)
python -m src.orchestrator run-once computrabajo -c CO

# Con más páginas
python -m src.orchestrator run-once computrabajo -c CO -p 50

# Con output verbose
python -m src.orchestrator run-once computrabajo -c CO -p 50 -v
```

---

## 📊 Scrapers Disponibles

### Computrabajo (Optimizado ✨)
Spider mejorado con:
- ✅ Batch inserts (100 jobs/batch)
- ✅ Deduplicación SHA256
- ✅ Empty page detection
- ✅ Modo listing-only para máxima velocidad
- ✅ Configuración de concurrencia adaptativa

**Países soportados:** Colombia (CO), México (MX), Argentina (AR)

### Otros Scrapers
- `elempleo` - El Empleo (Colombia)
- `bumeran` - Bumeran (Argentina, Chile, Panamá)
- `zonajobs` - ZonaJobs (Argentina)
- `occmundial` - OCC Mundial (México)
- `magneto` - Magneto (varios países)

Ver lista completa:
```bash
python -m src.orchestrator list-spiders
```

---

## ⚡ Comandos Principales

### 1. Scraping Básico (Modo Detallado)
```bash
# Colombia - Modo FULL-DETAIL (completo pero lento)
python -m src.orchestrator run-once computrabajo -c CO -p 10
```

Este modo:
- Scrape páginas de listado + páginas de detalle
- Extrae descripción completa y requirements
- ~3s delay entre requests
- 1 concurrent request (anti-bot)

### 2. Scraping Rápido (Modo Listing-Only) 🚀
Para usar el modo listing-only (2x más rápido), necesitas ejecutar directamente con Scrapy:

```bash
# Modo LISTING-ONLY (rápido)
scrapy crawl computrabajo \
  -a country=CO \
  -a listing_only=true \
  -a concurrent_requests=16 \
  -a download_delay=1.5
```

Este modo:
- Solo scrape páginas de listado (sin detail pages)
- Extrae datos básicos (título, empresa, location, preview)
- ~1.5s delay entre requests
- 16 concurrent requests
- **2x más rápido** que modo detallado

### 3. Scraping Masivo (Múltiples Ciudades/Keywords)
Para scraping masivo, usa el archivo de configuración:

```python
# Crear archivo de configuración
# scripts/colombia_massive_config.py
from src.orchestrator import run_scraper

cities = ['bogota-dc', 'medellin', 'cali', 'barranquilla']
keywords = ['sistemas', 'desarrollador', 'ingeniero']

for city in cities:
    for keyword in keywords:
        run_scraper('computrabajo', country='CO', city=city, keyword=keyword, max_pages=100)
```

---

## 🔧 Configuración Avanzada

### Configurar Concurrencia

**Opción 1: Variables de entorno**
```bash
# Editar .env
SCRAPY_CONCURRENT_REQUESTS=16
SCRAPY_DOWNLOAD_DELAY=1.5
BATCH_INSERT_SIZE=100
```

**Opción 2: Custom settings en spider**
El spider de Computrabajo ajusta automáticamente:
- **Listing-only mode:** 16 concurrent, 1.5s delay
- **Full-detail mode:** 1 concurrent, 3s delay

### Configurar Base de Datos
```bash
# Editar .env (si es necesario)
DB_HOST=127.0.0.1
DB_PORT=5433
DB_NAME=labor_observatory
DB_USER=labor_user
DB_PASSWORD=123456
```

### Parámetros del Spider Computrabajo

```bash
scrapy crawl computrabajo \
  -a country=CO \              # País (CO, MX, AR)
  -a city=bogota-dc \          # Ciudad
  -a keyword=sistemas \        # Keyword de búsqueda
  -a listing_only=true \       # Modo rápido (true/false)
  -a concurrent_requests=16 \  # Concurrent requests
  -a download_delay=1.5        # Delay entre requests (s)
```

---

## 📈 Datos Actuales

### Base de Datos
```sql
-- Verificar datos
SELECT portal, country, COUNT(*) as total_jobs
FROM raw_jobs
GROUP BY portal, country
ORDER BY total_jobs DESC;
```

**Estado actual (2025-10-19):**
- **25,063 jobs** totales
- **Computrabajo CO:** 23,729 jobs
- **Computrabajo MX:** 1,140 jobs
- **Elempleo CO:** 194 jobs

### Verificar Última Extracción
```bash
# PostgreSQL
docker-compose exec -T postgres psql -U labor_user -d labor_observatory -c "
SELECT
    portal,
    country,
    COUNT(*) as total_jobs,
    MAX(scraped_at) as last_scrape
FROM raw_jobs
GROUP BY portal, country
ORDER BY last_scrape DESC;"
```

---

## ⚠️ Rate Limiting

**Computrabajo detecta scraping masivo:**
- Si recibes **403 Forbidden**, espera 12-24 horas
- Reduce concurrencia (8 en vez de 16)
- Aumenta delay (2s en vez de 1.5s)
- Considera proxies (ver configuración avanzada)

### Soluciones para Rate Limiting

1. **Esperar:** 12-24 horas entre runs masivos
2. **Reducir agresividad:**
   ```bash
   # Más conservador
   scrapy crawl computrabajo -a country=CO -a concurrent_requests=4 -a download_delay=3
   ```
3. **Usar Proxies:** Editar `src/scraper/middlewares.py` para configurar proxy rotation

---

## 📝 Logs

```bash
# Ver logs en tiempo real
tail -f logs/scrapy.log

# Ver logs de orchestrator
tail -f logs/mass_scraping.log
```

---

## 🎯 Ejemplos de Uso

### Ejemplo 1: Extracción Diaria (Incremental)
```bash
# Scraping ligero diario (primeras 5 páginas, nuevos jobs)
python -m src.orchestrator run-once computrabajo -c CO -p 5
```

### Ejemplo 2: Extracción Semanal (Exhaustiva)
```bash
# Scraping profundo semanal (50 páginas)
python -m src.orchestrator run-once computrabajo -c CO -p 50 -v
```

### Ejemplo 3: Máxima Velocidad (Listing-Only)
```bash
# Para análisis rápido o testing
scrapy crawl computrabajo -a country=CO -a listing_only=true -a concurrent_requests=16
```

---

## 🛠️ Troubleshooting

### Error: "Database error: value too long for type character varying(50)"
**Solución:** Bug arreglado en última versión. Si persiste, pull latest changes.

### Error: "403 Forbidden"
**Solución:** Rate limiting activo. Esperar 12-24 horas o usar proxies.

### Error: "No jobs found"
**Causas posibles:**
- Keyword/ciudad sin resultados
- Website cambió estructura HTML
- Rate limiting silencioso

### Pipeline no guarda datos
**Verificar:**
```bash
# Check DB connection
docker-compose ps
docker-compose exec postgres psql -U labor_user -d labor_observatory -c "\dt"
```

---

## 📚 Recursos Adicionales

- **Documentación Scrapy:** https://docs.scrapy.org/
- **Orchestrator:** Ejecutar `python -m src.orchestrator --help`
- **Logs:** `logs/scrapy.log`, `logs/mass_scraping.log`

---

**Última actualización:** 2025-10-19
**Versión:** 2.0 (Arquitectura optimizada)
