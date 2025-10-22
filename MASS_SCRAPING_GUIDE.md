# Guía de Scraping Masivo - Observatorio Demanda Laboral

## Objetivo
Obtener ~600,000 job ads de portales laborales en Latinoamérica.

**Estado Actual**: 29,872 jobs
**Objetivo**: 600,000 jobs
**Faltante**: ~570,000 jobs

---

## Paso a Paso - Ejecución Desde VS Code

### 1. Levantar Docker (PostgreSQL + Redis)

```bash
# Navegar al directorio del proyecto
cd C:\Users\PcMaster\Documents\GitHub\observatorio-demanda-laboral

# Levantar todos los servicios
docker-compose up -d

# Verificar que los contenedores están corriendo
docker ps

# Verificar logs de PostgreSQL (opcional)
docker logs observatorio-demanda-laboral-postgres-1 --tail 50
```

**Verificación**: Debes ver 4 contenedores corriendo:
- `observatorio-demanda-laboral-postgres-1` (Puerto 5433)
- `observatorio-demanda-laboral-redis-1` (Puerto 6379)
- `observatorio-demanda-laboral-app-1`
- `observatorio-demanda-laboral-pgadmin-1` (Puerto 8081)

---

### 2. Verificar Estado del Sistema

```bash
# Ver estado de la base de datos y conteo de jobs
python -m src.orchestrator status

# Ver scrapers disponibles
python -m src.orchestrator list-spiders
```

---

### 3. Estrategia de Scraping Masivo

#### Prioridad 1: Portales Rápidos (Scrapy - Sin Selenium)
Estos son los más eficientes (~2 segundos por job):

```bash
# OccMundial - México (MUY RÁPIDO, ya optimizado con TLS)
# Estimado: 50,000-100,000 jobs disponibles
python -m src.orchestrator run-once occmundial -c MX -p 500 -v

# Computrabajo - Colombia (ya tiene 25k, agotar paginación)
# Estimado: 100,000+ jobs disponibles
python -m src.orchestrator run-once computrabajo -c CO -p 1000 -v

# Computrabajo - México
python -m src.orchestrator run-once computrabajo -c MX -p 1000 -v

# Computrabajo - Argentina
python -m src.orchestrator run-once computrabajo -c AR -p 1000 -v

# Computrabajo - Chile
python -m src.orchestrator run-once computrabajo -c CL -p 500 -v

# Elempleo - Colombia (ya tiene 1.2k, agotar)
python -m src.orchestrator run-once elempleo -c CO -p 500 -v

# InfoJobs - España/Brasil (si está configurado)
python -m src.orchestrator run-once infojobs -c ES -p 500 -v
```

#### Prioridad 2: Portales con Selenium (Más Lentos pero Confiables)
Estos toman ~5-8 segundos por job:

```bash
# Bumeran - Argentina (mayor volumen)
python -m src.orchestrator run-once bumeran -c AR -p 500 -v

# Bumeran - México
python -m src.orchestrator run-once bumeran -c MX -p 500 -v

# Bumeran - Chile
python -m src.orchestrator run-once bumeran -c CL -p 300 -v

# ZonaJobs - Argentina (ya tiene 100, agotar)
python -m src.orchestrator run-once zonajobs -c AR -p 500 -v

# Magneto - Colombia (ya tiene 60, agotar)
python -m src.orchestrator run-once magneto -c CO -p 300 -v

# Magneto - Argentina
python -m src.orchestrator run-once magneto -c AR -p 300 -v
```

---

### 4. Ejecución en Paralelo (Recomendado)

Para maximizar velocidad, ejecuta múltiples scrapers en paralelo en diferentes terminales:

**Terminal 1 - Portales Rápidos (Scrapy)**:
```bash
python -m src.orchestrator run-once occmundial -c MX -p 500 -v
```

**Terminal 2 - Computrabajo Colombia**:
```bash
python -m src.orchestrator run-once computrabajo -c CO -p 1000 -v
```

**Terminal 3 - Bumeran Argentina**:
```bash
python -m src.orchestrator run-once bumeran -c AR -p 500 -v
```

**Terminal 4 - Computrabajo México**:
```bash
python -m src.orchestrator run-once computrabajo -c MX -p 1000 -v
```

---

### 5. Monitoreo en Tiempo Real

#### Opción A: Terminal (cada 30 segundos)
```bash
# Ver progreso cada 30 segundos
watch -n 30 "python -m src.orchestrator status"
```

#### Opción B: pgAdmin (Web UI)
```
1. Abrir navegador: http://localhost:8081
2. Login: admin@admin.com / admin (o las credenciales configuradas)
3. Conectar a PostgreSQL:
   - Host: postgres (en Docker) o localhost (fuera Docker)
   - Port: 5432 (interno) o 5433 (externo)
   - Database: labor_observatory
   - Username: labor_user
   - Password: 123456

4. Query para ver conteo:
   SELECT portal, COUNT(*) as total
   FROM raw_jobs
   GROUP BY portal
   ORDER BY total DESC;
```

#### Opción C: Query Manual en PostgreSQL
```bash
# Desde terminal
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory

# Dentro de psql:
SELECT portal, COUNT(*) as total, MAX(scraped_at) as last_scraped
FROM raw_jobs
GROUP BY portal
ORDER BY total DESC;

# Salir
\q
```

---

### 6. Estimación de Tiempo y Capacidad

#### Portales Rápidos (Scrapy - ~2s por job):
- **OccMundial**: 50,000 jobs × 2s = ~28 horas
- **Computrabajo** (3 países): 300,000 jobs × 2s = ~167 horas
- **Elempleo**: 30,000 jobs × 2s = ~17 horas

#### Portales con Selenium (~7s por job):
- **Bumeran** (3 países): 150,000 jobs × 7s = ~292 horas
- **ZonaJobs**: 30,000 jobs × 7s = ~58 horas
- **Magneto** (2 países): 20,000 jobs × 7s = ~39 horas

**Total Estimado en Serial**: ~600 horas (25 días)
**Total Estimado en Paralelo (4 scrapers)**: ~150 horas (6-7 días)

---

### 7. Optimización para 600k Jobs

#### Estrategia Recomendada (7 días):

**Día 1-2**: Portales Scrapy (rápidos)
```bash
# Terminal 1
python -m src.orchestrator run-once occmundial -c MX -p 500 -v

# Terminal 2
python -m src.orchestrator run-once computrabajo -c CO -p 1000 -v

# Terminal 3
python -m src.orchestrator run-once computrabajo -c MX -p 1000 -v

# Terminal 4
python -m src.orchestrator run-once elempleo -c CO -p 500 -v
```

**Día 3-5**: Bumeran y Computrabajo Argentina
```bash
# Terminal 1
python -m src.orchestrator run-once bumeran -c AR -p 500 -v

# Terminal 2
python -m src.orchestrator run-once computrabajo -c AR -p 1000 -v

# Terminal 3
python -m src.orchestrator run-once bumeran -c MX -p 500 -v
```

**Día 6-7**: ZonaJobs, Magneto, otros
```bash
# Terminal 1
python -m src.orchestrator run-once zonajobs -c AR -p 500 -v

# Terminal 2
python -m src.orchestrator run-once magneto -c CO -p 300 -v

# Terminal 3
python -m src.orchestrator run-once magneto -c AR -p 300 -v
```

---

### 8. Comandos de Utilidad

#### Detener Docker
```bash
docker-compose down
```

#### Reiniciar Docker (si hay problemas)
```bash
docker-compose down
docker-compose up -d
```

#### Ver logs en tiempo real
```bash
# Logs de PostgreSQL
docker logs -f observatorio-demanda-laboral-postgres-1

# Logs de todos los contenedores
docker-compose logs -f
```

#### Limpiar caché de Scrapy (si hay errores)
```bash
# Eliminar archivos de caché
rm -rf .scrapy/
```

#### Backup de base de datos (recomendado antes de scraping masivo)
```bash
# Crear backup
docker exec observatorio-demanda-laboral-postgres-1 pg_dump -U labor_user labor_observatory > backup_$(date +%Y%m%d_%H%M%S).sql

# Restaurar backup (si es necesario)
cat backup_YYYYMMDD_HHMMSS.sql | docker exec -i observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory
```

---

### 9. Problemas Comunes

#### Error: "Connection refused" PostgreSQL
```bash
# Verificar que PostgreSQL está corriendo
docker ps | grep postgres

# Si no está corriendo, levantarlo
docker-compose up -d postgres
```

#### Error: "ChromeDriver not found" (Selenium spiders)
```bash
# Instalar webdriver-manager
pip install webdriver-manager

# El spider lo descargará automáticamente
```

#### Error: HTTP 403 (OccMundial)
```bash
# Verificar que curl-cffi está instalado
pip install curl-cffi

# El middleware TLS debería manejarlo automáticamente
```

#### Scraper se detiene sin error
- Verificar memoria RAM disponible (Selenium consume mucho)
- Reducir `CONCURRENT_REQUESTS` en settings si es necesario
- Usar `-p` menor (ej: 100 páginas a la vez, luego reiniciar)

---

### 10. Métricas de Éxito

Al finalizar el scraping masivo, verifica:

```bash
# Total de jobs
python -m src.orchestrator status

# Distribución por portal
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory -c "SELECT portal, COUNT(*) FROM raw_jobs GROUP BY portal ORDER BY COUNT(*) DESC;"

# Distribución por país
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory -c "SELECT country, COUNT(*) FROM raw_jobs GROUP BY country ORDER BY COUNT(*) DESC;"

# Jobs con campos completos
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory -c "SELECT COUNT(*) FROM raw_jobs WHERE description IS NOT NULL AND requirements IS NOT NULL;"
```

**Objetivo Cumplido**: ≥600,000 jobs en `raw_jobs` con campos completos.

---

## Notas Importantes

1. **No ejecutar `indeed`** - Tiene problemas de Cloudflare sin resolver
2. **Selenium consume RAM** - Si tienes <16GB RAM, ejecuta max 2 scrapers Selenium en paralelo
3. **Duplicados** - El sistema detecta duplicados por `content_hash`, no te preocupes
4. **Interrupciones** - Puedes detener (`Ctrl+C`) y reiniciar sin perder progreso
5. **Backups** - Haz backup cada 100k jobs como precaución

---

## Comando de Inicio Rápido (Todo en Uno)

```bash
# 1. Levantar Docker
docker-compose up -d

# 2. Verificar estado
python -m src.orchestrator status

# 3. Iniciar scraping masivo (ejemplo: OccMundial)
python -m src.orchestrator run-once occmundial -c MX -p 500 -v
```

¡Listo para scrapear! 🚀
