# Quick Start - Scraping Masivo desde VS Code

## Inicio Rápido (5 minutos)

### 1. Levantar Docker

```bash
# Abrir terminal en VS Code (Ctrl + `)
cd C:\Users\PcMaster\Documents\GitHub\observatorio-demanda-laboral

# Levantar PostgreSQL, Redis y servicios
docker-compose up -d

# Verificar que están corriendo (debes ver 4 contenedores)
docker ps
```

**Esperado:**
```
CONTAINER ID   IMAGE                PORTS                       NAMES
xxxxx          postgres:15          0.0.0.0:5433->5432/tcp     observatorio-...-postgres-1
xxxxx          redis:7-alpine       0.0.0.0:6379->6379/tcp     observatorio-...-redis-1
xxxxx          dpage/pgadmin4       0.0.0.0:8081->80/tcp       observatorio-...-pgadmin-1
xxxxx          observatorio-...                                observatorio-...-app-1
```

---

### 2. Verificar Estado Inicial

```bash
# Ver cuántos jobs tienes actualmente
python -m src.orchestrator status

# Ver scrapers disponibles
python -m src.orchestrator list-spiders
```

---

### 3. Ejecutar Scraping Masivo (Opción Simple)

#### Opción A: Un scraper a la vez (más estable)

```bash
# OccMundial - MX (el más rápido - ~2s por job)
python -m src.orchestrator run-once occmundial -c MX -v

# Computrabajo - CO (grande, ~50k+ jobs disponibles)
python -m src.orchestrator run-once computrabajo -c CO -v

# Computrabajo - MX
python -m src.orchestrator run-once computrabajo -c MX -v
```

#### Opción B: Múltiples scrapers en paralelo (más rápido)

**Terminal 1:**
```bash
python -m src.orchestrator run-once occmundial -c MX -v
```

**Terminal 2 (nueva terminal en VS Code: `Ctrl+Shift+` ` ):**
```bash
python -m src.orchestrator run-once computrabajo -c CO -v
```

**Terminal 3:**
```bash
python -m src.orchestrator run-once computrabajo -c MX -v
```

**Terminal 4:**
```bash
python -m src.orchestrator run-once elempleo -c CO -v
```

---

### 4. Monitorear Progreso

#### Opción A: En otra terminal (actualiza cada 30 seg)
```bash
# Nueva terminal
while ($true) {
    Clear-Host
    python -m src.orchestrator status
    Start-Sleep -Seconds 30
}
```

#### Opción B: Query directo en PostgreSQL
```bash
# Conectar a PostgreSQL
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory

# Query para ver conteo actualizado
SELECT portal, COUNT(*) as total, MAX(scraped_at) as last_update
FROM raw_jobs
GROUP BY portal
ORDER BY total DESC;

# Salir
\q
```

#### Opción C: pgAdmin Web (más visual)
1. Abrir navegador: `http://localhost:8081`
2. Login: `admin@admin.com` / `admin`
3. Conectar a servidor:
   - Host: `postgres`
   - Port: `5432`
   - Database: `labor_observatory`
   - Username: `labor_user`
   - Password: `123456`

---

### 5. Detener y Apagar

#### Detener un scraper (si está corriendo)
```
Ctrl + C
```

#### Apagar Docker (al terminar el día)
```bash
docker-compose down
```

#### Mantener Docker corriendo (para continuar después)
Los contenedores seguirán corriendo, solo cierra VS Code normalmente.

---

## Comandos Útiles para Otro Día

### Ver cuántos jobs tienes
```bash
python -m src.orchestrator status
```

### Backup de base de datos (antes de scraping masivo)
```bash
docker exec observatorio-demanda-laboral-postgres-1 pg_dump -U labor_user labor_observatory > backup_$(Get-Date -Format "yyyyMMdd_HHmmss").sql
```

### Reiniciar Docker (si hay problemas)
```bash
docker-compose restart
```

### Ver logs de errores
```bash
# Logs de PostgreSQL
docker logs observatorio-demanda-laboral-postgres-1 --tail 50

# Logs de todos los servicios
docker-compose logs --tail 50
```

---

## Plan Recomendado para 600k Jobs

### Semana 1: Portales Rápidos (Scrapy)
- **Día 1-2**: OccMundial MX (50k jobs)
- **Día 2-4**: Computrabajo CO + MX + AR (300k jobs)
- **Día 4-5**: Elempleo CO (30k jobs)

### Semana 2: Portales Selenium
- **Día 6-8**: Bumeran AR + MX (150k jobs)
- **Día 9**: ZonaJobs AR (30k jobs)
- **Día 10**: Magneto CO + AR (20k jobs)

**Total Estimado**: ~580k jobs en 10 días (ejecutando 8 horas/día)

---

## Problemas Comunes

### "Connection refused" a PostgreSQL
```bash
# Verificar que Docker está corriendo
docker ps

# Si no hay contenedores, levantar Docker
docker-compose up -d
```

### Scraper muy lento o se detiene
```bash
# Reducir páginas por sesión
python -m src.orchestrator run-once occmundial -c MX -p 50 -v

# Luego ejecutar de nuevo para continuar
```

### Muchos duplicados
Es normal. El sistema detecta automáticamente duplicados por `content_hash`.

### Error "ChromeDriver not found"
```bash
# Ya debería estar instalado, pero si falta:
pip install webdriver-manager
```

---

## Verificación Final

Al terminar, verifica que llegaste al objetivo:

```bash
# Total de jobs
python -m src.orchestrator status

# Jobs por país
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory -c "SELECT country, COUNT(*) FROM raw_jobs GROUP BY country;"

# Jobs con datos completos
docker exec -it observatorio-demanda-laboral-postgres-1 psql -U labor_user -d labor_observatory -c "SELECT COUNT(*) FROM raw_jobs WHERE description IS NOT NULL AND requirements IS NOT NULL;"
```

**Objetivo**: ≥600,000 jobs en total

---

## Ejemplo: Sesión Completa de 1 Hora

```bash
# 1. Levantar Docker (30 segundos)
docker-compose up -d

# 2. Verificar estado (5 segundos)
python -m src.orchestrator status

# 3. Ejecutar OccMundial (1 hora)
python -m src.orchestrator run-once occmundial -c MX -v

# Resultado esperado: ~7,200 jobs en 1 hora (2 jobs/segundo)
```

¡Listo para scrapear! 🚀
