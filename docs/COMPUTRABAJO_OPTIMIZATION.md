# Computrabajo Spider Optimization Guide

## 🎯 Resumen

El spider de Computrabajo ha sido completamente optimizado con una **estrategia dual** que ofrece dos opciones según tu caso de uso:

- **OPCIÓN A (Scrapy Optimizado)**: Conservador, para scraping continuo y de bajo riesgo
- **OPCIÓN B (Requests Masivo)**: Agresivo, para scraping masivo inicial o catch-up

---

## 📊 Comparación de Opciones

| Característica | OPCIÓN A: Scrapy | OPCIÓN B: Requests |
|---|---|---|
| **Throughput** | ~500-1,000 jobs/hora | ~2,000-5,000 jobs/hora |
| **Riesgo de Ban** | MUY BAJO | MEDIO (controlado) |
| **Uso recomendado** | Scraping diario, mantenimiento | Scraping masivo inicial, catch-up |
| **Complejidad** | Media | Alta |
| **Concurrencia** | Secuencial (1 request) | 4-8 workers paralelos |
| **Anti-bot evasion** | ✅ Avanzado | ✅ Avanzado |
| **Proxies** | ✅ Soportado | ⚠️ Requiere implementación manual |
| **Delays** | Inteligentes (3s base + 10-15s entre páginas) | Distribuido por worker (3-5s) |
| **Paginación** | Ilimitada | Hasta max_pages configurado |
| **Fingerprinting** | ✅ Dinámico (60+ UAs, headers variables) | ✅ Dinámico (60+ UAs, headers variables) |
| **Auto-stop en ban** | ✅ Sí | ✅ Sí |
| **Deduplicación** | Content hash en DB | Content hash en DB |

---

## 🚀 OPCIÓN A: Scrapy Optimizado (Conservador)

### Mejoras Implementadas

#### 1. **Pool de User-Agents Extendido (60+)**
```
config/user_agents.txt ahora contiene:
- Chrome (Windows, macOS, Linux)
- Firefox (Windows, macOS, Linux)
- Safari (macOS)
- Edge (Windows, macOS)
- Opera, Brave, Vivaldi
- Múltiples versiones (117-122)
```

#### 2. **Browser Fingerprinting Avanzado**
- **Accept-Language** dinámico (10 variantes para LATAM)
- **Sec-CH-UA headers** modernos (Client Hints)
- **Sec-Fetch headers** realistas
- **Referer tracking** inteligente:
  - 30% chance de venir de Google
  - Detail pages usan listing como referer
- **DNT header** aleatorio (75% sin DNT, 25% con DNT)
- **Cache-Control** variable

#### 3. **Delays Inteligentes**
```python
DOWNLOAD_DELAY = 3s (base)
+ 10-15s entre páginas (como HiringCafe)
+ AutoThrottle habilitado
```

#### 4. **Paginación Ilimitada**
- **Removido el límite de 5 páginas**
- Detección de 3 páginas vacías consecutivas → stop
- Detección de alto porcentaje de duplicados (>80%) → advertencia

#### 5. **Configuración Anti-Ban**
```python
CONCURRENT_REQUESTS = 1  # Secuencial
HTTPCACHE_ENABLED = False  # No cache de errores 429
RETRY_HTTP_CODES = [429, 403, 500, 502, 503, 504, 408]
AUTOTHROTTLE_ENABLED = True
```

### Uso

#### Vía Orchestrator (Recomendado)
```bash
python -m src.orchestrator run-once computrabajo -c CO -l 1000 -v
```

#### Directamente con Scrapy
```bash
cd src/scraper
scrapy crawl computrabajo -a country=CO -a keyword=sistemas -a city=bogota-dc -s SETTINGS_MODULE=scraper.settings
```

### Throughput Esperado
- **~500-1,000 jobs/hora** (dependiendo de conexión y latencia)
- **Riesgo de ban**: MUY BAJO
- **Recomendado para**: Scraping diario, ejecutar cada 24-48 horas

---

## ⚡ OPCIÓN B: Requests Masivo (Agresivo)

### Características

#### 1. **Threading con Workers Independientes**
- 4-8 workers paralelos (configurable)
- Cada worker tiene:
  - Sesión HTTP independiente
  - User-Agent único
  - Accept-Language único
  - Rate limiting individual

#### 2. **Rate Limiting Distribuido**
```python
# Por worker:
- 3-5 segundos entre requests
- Tracking de tiempo por sesión
- Auto-stop global en errores 429/403
```

#### 3. **Scraping Completo**
- Extrae listing page + detail page
- Content hash deduplication en DB
- Parsea descripción, requirements, metadata

#### 4. **Auto-Stop en Bans**
```python
if response.status_code in [429, 403]:
    stop_scraping.set()  # Detiene TODOS los workers
```

### Uso

#### Básico (4 workers, 50 páginas)
```bash
python scripts/scrape_computrabajo_requests.py CO bogota-dc sistemas
```

#### Con configuración custom
```bash
# 6 workers, 100 páginas
python scripts/scrape_computrabajo_requests.py CO bogota-dc desarrollador --workers 6 --max-pages 100

# México
python scripts/scrape_computrabajo_requests.py MX distrito-federal ingeniero --workers 4 --max-pages 50

# Argentina
python scripts/scrape_computrabajo_requests.py AR capital-federal programador --workers 4 --max-pages 50
```

### Throughput Esperado
- **~2,000-5,000 jobs/hora** (con 4-6 workers)
- **Riesgo de ban**: MEDIO (auto-stop en detección)
- **Recomendado para**:
  - Scraping masivo inicial
  - Catch-up después de downtime
  - Colección rápida de datos históricos

### ⚠️ Precauciones

1. **No ejecutar 24/7**: Usar solo para catch-up o scraping inicial
2. **Monitorear logs**: Si ves errores 429/403, detener y esperar
3. **Empezar con pocos workers**: Probar con 2-3 workers primero
4. **Aumentar gradualmente**: Si funciona bien, subir a 4-6 workers

---

## 🔧 Configuración Avanzada

### Fingerprints Configuration
Editar `config/fingerprints.yaml` para ajustar:

```yaml
portal_configs:
  computrabajo:
    use_sec_fetch: true
    use_sec_ch_ua: true
    use_referer: true
    use_dnt: true
    randomize_accept_language: true
    session_cookies: true
```

### User-Agents
Editar `config/user_agents.txt` para agregar más UAs:
```
# Chrome - Windows
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36...
```

### Proxies (Opcional)
Editar `config/proxies.yaml`:

```yaml
portal_config:
  computrabajo:
    pool: 'residential'  # Usar proxies residenciales
    rotation_strategy: 'per_request'
    timeout: 20
    max_retries: 3

proxy_pools:
  residential:
    proxies:
      - http://user:pass@proxy1.com:8080
      - http://user:pass@proxy2.com:8080
```

---

## 📈 Métricas de Éxito

### Monitorear
- **Duplicate rate por página**: Si >80%, casi todos los jobs ya están en DB
- **Empty pages consecutivas**: 3 = fin natural del scraping
- **HTTP status codes**: 200 = OK, 429/403 = rate limited
- **Jobs scraped vs found**: Alta conversión = buen scraping

### Logs a Buscar
```bash
✅ New job found       # Job nuevo detectado
⏭️ Skipping duplicate  # Job duplicado (ya en DB)
⚠️ High duplicate rate # >80% duplicados en página
🚫 Rate limited        # Bloqueado (detener scraping)
```

---

## 🎓 Recomendaciones

### Para Uso Diario (Mantenimiento)
```bash
# OPCIÓN A: Scrapy conservador
python -m src.orchestrator run-once computrabajo -c CO -l 500 -v

# Ejecutar cada 24-48 horas
# Baja carga, bajo riesgo
```

### Para Catch-Up Masivo (Inicial o Post-Downtime)
```bash
# OPCIÓN B: Requests agresivo
python scripts/scrape_computrabajo_requests.py CO bogota-dc sistemas --workers 4 --max-pages 100

# Ejecutar una vez, esperar 24 horas antes de repetir
# Alta carga, riesgo medio pero controlado
```

### Para Múltiples Países/Ciudades
```bash
# Script para ejecutar secuencialmente
python scripts/scrape_computrabajo_requests.py CO bogota-dc sistemas --workers 3 --max-pages 50
sleep 3600  # Esperar 1 hora
python scripts/scrape_computrabajo_requests.py CO medellin sistemas --workers 3 --max-pages 50
sleep 3600
python scripts/scrape_computrabajo_requests.py MX distrito-federal desarrollador --workers 3 --max-pages 50
```

---

## 🔍 Troubleshooting

### Problema: Rate Limited (HTTP 429)
**Solución**:
1. Detener el scraping inmediatamente
2. Esperar 2-4 horas
3. Reiniciar con OPCIÓN A (Scrapy conservador)
4. Si persiste, reducir workers o agregar proxies

### Problema: Forbidden (HTTP 403)
**Solución**:
1. Verificar que fingerprint middleware está activo
2. Revisar logs para ver qué headers están siendo enviados
3. Probar con proxies residenciales
4. Esperar 24 horas antes de reintentar

### Problema: No encuentra jobs
**Solución**:
1. Verificar el selector CSS: `response.css("article")`
2. Abrir la URL en navegador y verificar estructura HTML
3. Puede que Computrabajo haya cambiado su diseño
4. Actualizar selectores en el spider

### Problema: Alto porcentaje de duplicados
**No es un problema**:
- Es normal después de scraping inicial
- Significa que la mayoría de jobs ya están en DB
- Sistema funcionando correctamente

---

## 📚 Archivos Modificados/Creados

```
✅ config/user_agents.txt              # 60+ user agents
✅ config/fingerprints.yaml            # Configuración de fingerprinting
✅ src/scraper/middlewares.py          # BrowserFingerprintMiddleware (nuevo)
✅ src/scraper/spiders/computrabajo_spider.py  # Optimizaciones
✅ src/scraper/settings.py             # Habilitar fingerprinting
✅ scripts/scrape_computrabajo_requests.py     # Script masivo (nuevo)
✅ docs/COMPUTRABAJO_OPTIMIZATION.md   # Esta documentación
```

---

## 🎉 Resultados Esperados

### Antes (Spider Original)
- Max 5 páginas = ~100-150 jobs
- Delays de 1.5s (muy agresivo)
- 8 User-Agents básicos
- Headers estáticos
- Alto riesgo de ban

### Después (Optimizado)
- **OPCIÓN A**: Paginación ilimitada, ~500-1,000 jobs/hora, riesgo MUY BAJO
- **OPCIÓN B**: Hasta max_pages configurado, ~2,000-5,000 jobs/hora, riesgo MEDIO
- 60+ User-Agents variados
- Headers dinámicos y realistas
- Fingerprinting avanzado
- Auto-stop inteligente
- Deduplicación en DB

### Comparado con HiringCafe
- **HiringCafe**: API REST directa, 100 jobs/request, throughput ~3,000 jobs/hora
- **Computrabajo OPCIÓN A**: HTML scraping, ~30 jobs/page + detail, throughput ~500-1,000 jobs/hora
- **Computrabajo OPCIÓN B**: HTML scraping paralelo, throughput ~2,000-5,000 jobs/hora

**Conclusión**: Computrabajo nunca será tan rápido como HiringCafe (API vs HTML), pero ahora es **10-50x más eficiente** que antes.

---

## 🤝 Contribuciones

Si encuentras formas de optimizar aún más:
1. Agregar más User-Agents a `config/user_agents.txt`
2. Mejorar selectores CSS si cambian
3. Implementar proxies automáticos
4. Optimizar parseo para extraer más del listing (menos detail requests)

---

**Autores**: Nicolás Francisco Camacho Alarcón y Alejandro Pinzón
**Fecha**: Octubre 2025
**Versión**: 1.0
