# Decisiones de Diseño - Gold Standard Dataset

Este documento registra todas las decisiones tomadas en el proceso de creación del gold standard de 300 job ads para evaluación de pipelines de extracción.

## Fecha: 2025-11-03

## Contexto

**Objetivo:** Crear un dataset de 300 ofertas laborales anotadas manualmente para:
1. Evaluar Pipeline A (NER + Regex + ESCO)
2. Evaluar Pipeline B (LLMs: Gemma 3 4B vs Llama 3 3B)
3. Calcular métricas de precision, recall, F1
4. Identificar failure modes y optimizar thresholds
5. Reportar resultados en tesis (Capítulo 7)

**Dataset disponible al inicio:** 56,555 job ads
- 23,352 jobs originales
- 33,203 jobs importados de CSV de Alejandro

## Decisión 1: Distribución por Idioma

**Criterio:** Representar la realidad de LATAM donde la mayoría de ofertas tech son en español, pero hay significativa presencia de inglés.

**Decisión Final:**
- **250 jobs en Español (83%)**
- **50 jobs en Inglés (17%)**

**Justificación:**
- Refleja distribución real del mercado
- Permite evaluar performance de modelos multilingües
- Da suficientes muestras de inglés para análisis estadístico (n=50)
- Posibilita comparar extracción en ambos idiomas

**Jobs "mixed" (español+inglés):** Excluidos del gold standard para mantener categorías claras. Total descartados: 286 jobs.

## Decisión 2: Distribución Geográfica

**Criterio:** Balance entre los 3 países principales de estudio.

**Distribución Target:**
```
País    Español  Inglés  Total
CO      100      17      117
MX      100      17      117
AR      50       16      66
Total   250      50      300
```

**Justificación:**
- CO y MX tienen mayor volumen de datos → 100 jobs cada uno en español
- AR tiene menos datos disponibles → 50 jobs en español
- Proporción similar de inglés para los 3 países (~15-17%)
- Permite análisis por país Y análisis agregado

**Candidatos disponibles por país/idioma:**
```
País  Idioma  Disponibles  Target  Ratio
AR    EN      1,013        16      63x ✅
AR    ES      141          50      2.8x ⚠️ (justo)
CO    EN      1,593        17      94x ✅
CO    ES      566          100     5.7x ✅
MX    EN      3,135        17      184x ✅
MX    ES      368          100     3.7x ✅
```

## Decisión 3: Tipos de Roles (Pure Tech Only)

**Criterio:** Solo incluir roles PURAMENTE tecnológicos para garantizar alta densidad de skills técnicas.

**Roles incluidos:**
- Backend Developer / Backend Engineer
- Frontend Developer / Frontend Engineer
- Full-stack Developer
- Mobile Developer (iOS, Android, React Native, Flutter)
- Data Scientist / ML Engineer / Data Analyst
- DevOps Engineer / SRE / Platform Engineer / Cloud Engineer
- QA Engineer / Test Automation Engineer
- Security Engineer / Cybersecurity Engineer

**Roles EXCLUIDOS (tech-adjacent pero no pure tech):**
- ERP Specialist
- BI Analyst (a menos que requiera skills de Data Science)
- IT Support / Help Desk
- Project Manager (a menos que sea Technical PM con skills específicas)
- Product Manager
- Scrum Master / Agile Coach
- Business Analyst

**Distribución de roles (target):**
```
Backend:        80 jobs (27%)
Fullstack:      60 jobs (20%)
Frontend:       50 jobs (17%)
Data Science:   40 jobs (13%)
DevOps:         40 jobs (13%)
Mobile:         15 jobs (5%)
QA:             10 jobs (3%)
Security:       5 jobs (2%)
Total:          300 jobs
```

**Justificación:**
- Backend, Fullstack, Frontend = núcleo del desarrollo de software
- Data Science y DevOps = áreas de rápido crecimiento
- Mobile, QA, Security = representación de especialidades
- Variedad permite evaluar extracción en múltiples contextos

## Decisión 4: Distribución por Seniority

**Criterio Inicial:** 30% junior, 30% mid, 40% senior

**Decisión Final (Flexible):**
- **Target sugerido:** Junior 90, Mid 90, Senior 120
- **Implementación:** Flexible según disponibilidad
- **Prioridad:** NO forzar distribución exacta de seniority si compromete calidad o volumen total

**Justificación:**
- Senior roles tienden a tener descripciones más completas y técnicas
- Mercado real tiene más ofertas senior que junior (sesgo de portales)
- Es más importante llegar a 300 jobs de calidad que forzar seniority exacto

**Clasificación de seniority:**
- **Junior:** keywords como "junior", "jr.", "trainee", "entry", "graduate"
- **Mid:** ningún keyword específico (por defecto)
- **Senior:** keywords como "senior", "sr.", "lead", "staff", "principal", "architect"

## Decisión 5: Filtros de Calidad

**Longitud mínima:**
- Initial: >1000 caracteres (description + requirements)
- Justificación: Garantiza suficiente contenido para extraer skills

**Quality Score (0-100):**
- Base: 50 puntos
- Longitud >3000 chars: +20 pts
- Longitud >2000 chars: +15 pts
- Longitud >1000 chars: +10 pts
- Has requirements section (>100 chars): +10 pts
- Tech keywords in title: +10 pts
- Mentions 1+ technical skills: +10 pts (max)
- Penalty for HTML/JS noise: -10 pts (max)

**Tech keywords para título:**
```python
['developer', 'engineer', 'desarrollador', 'ingeniero',
 'programador', 'devops', 'data', 'scientist', 'analyst']
```

**Skills buscadas para scoring:**
```python
['python', 'java', 'javascript', 'react', 'angular', 'node',
 'aws', 'azure', 'docker', 'kubernetes', 'sql', 'mongodb']
```

## Decisión 6: Algoritmo de Selección

**Problema identificado:** Primera versión intentó llenar celdas específicas `(país × idioma × rol × seniority)` = 144 celdas. Muchas celdas vacías → solo 80 jobs seleccionados.

**Solución (Algoritmo Revisado):**

**Prioridad 1 - Idioma:**
- Separar todos los candidatos en ES vs EN
- Garantizar 250 ES, 50 EN

**Prioridad 2 - País:**
- Dentro de cada idioma, distribuir por país:
  - Español: 100 CO, 100 MX, 50 AR
  - Inglés: 17 CO, 17 MX, 16 AR

**Prioridad 3 - Rol:**
- Dentro de cada (país, idioma), intentar llenar cuotas de rol
- Seleccionar los de mayor quality score disponibles
- Si no hay suficientes de un rol, compensar con otros roles

**Prioridad 4 - Seniority (Flexible):**
- Intentar balancear junior/mid/senior dentro de cada (país, idioma, rol)
- NO bloquear selección si no hay suficientes de un seniority específico
- Preferir quality score sobre seniority exacta

**Orden de selección:**
1. Clasificar todos los candidatos por quality_score (descendente)
2. Crear grupos por (país, idioma, rol)
3. Iterar sobre targets de país/idioma
4. Dentro de cada target, llenar roles seleccionando los mejores
5. Tratar de balancear seniority, pero aceptar lo disponible

## Decisión 7: Metadata en Base de Datos

**Nuevas columnas en raw_jobs:**
```sql
language VARCHAR(10)                    -- 'es', 'en', 'mixed'
is_gold_standard BOOLEAN                -- TRUE para los 300 seleccionados
gold_standard_role_type VARCHAR(50)     -- 'backend', 'frontend', etc.
gold_standard_seniority VARCHAR(20)     -- 'junior', 'mid', 'senior'
```

**Justificación:**
- Permite filtrar fácilmente los 300 gold standard jobs
- Facilita análisis por rol y seniority
- Mantiene metadatos junto a los datos originales
- No requiere joins adicionales en queries

## Decisión 8: Language Detection

**Método:** Regex pattern matching (no usar modelos externos)

**Spanish patterns:**
```python
r'\b(experiencia|años|requisitos|habilidades|conocimientos|desarrollo|ingeniero|empresa)\b'
r'\b(buscamos|ofrecemos|ubicación|necesario|deseables|técnicas)\b'
```

**English patterns:**
```python
r'\b(experience|years|requirements|skills|knowledge|development|engineer|company)\b'
r'\b(looking|offer|location|required|desirable|technical|responsibilities)\b'
```

**Clasificación:**
- Español: si spanish_matches > english_matches × 2
- Inglés: si english_matches > spanish_matches × 2
- Mixed: en otro caso

**Justificación:**
- Simple, rápido, reproducible
- No requiere modelos de ML
- Suficientemente preciso para ofertas laborales (vocabulario específico)
- Factor 2× evita falsos positivos por palabras internacionales

## Decisión 9: Role Classification

**Método:** Pattern matching con prioridad ordenada

**Orden de prioridad (importa):**
1. Mobile (keywords específicos evitan confusión)
2. QA / Testing
3. Security / Architect
4. Data Science
5. DevOps / SRE
6. Frontend (solo si no menciona backend)
7. Backend
8. Fullstack
9. Other (catch-all)

**Keywords por rol:**
- **Mobile:** 'mobile', 'ios', 'android', 'flutter', 'react native'
- **QA:** 'qa', 'test', 'quality assurance', 'automation test'
- **Security:** 'security', 'cybersecurity', 'infosec', 'architect'
- **Data Science:** 'data scien', 'machine learning', 'ml engineer', 'data analyst', 'big data'
- **DevOps:** 'devops', 'sre', 'site reliability', 'platform engineer', 'cloud engineer', 'infrastructure'
- **Frontend:** 'frontend', 'front-end', 'front end', OR ('react', 'angular', 'vue' AND NOT 'backend')
- **Backend:** 'backend', 'back-end', 'back end', 'api', 'microservices', 'server'
- **Fullstack:** 'full stack', 'fullstack', 'full-stack'

**Justificación:**
- Prioridad evita ambigüedad (ej: "Full-stack React" se clasifica como fullstack, no frontend)
- Keywords basados en vocabulario real de ofertas tech
- Captura variaciones (full-stack, full stack, fullstack)

## Decisión 10: Output y Trazabilidad

**Archivo de salida:** `data/gold_standard/selected_jobs.json`

**Formato:**
```json
[
  {
    "job_id": "uuid",
    "country": "CO",
    "language": "es",
    "role": "backend",
    "seniority": "senior",
    "quality_score": 95,
    "title": "Senior Backend Developer",
    "portal": "elempleo",
    "desc_len": 2500,
    "req_len": 800
  }
]
```

**Base de datos:**
- UPDATE raw_jobs SET is_gold_standard = TRUE WHERE job_id IN (...)
- UPDATE gold_standard_role_type, gold_standard_seniority

**Justificación:**
- JSON para portabilidad y versionado en git
- Flags en BD para queries rápidas
- Quality score guardado para análisis post-selección
- Metadata completa para reproducibilidad

## Decisión 11: Validación y Next Steps

**Antes de anotar:**
1. Revisar muestras de los 300 seleccionados (10 por categoría)
2. Verificar calidad visual (no HTML corrupto, no ruido)
3. Confirmar que son pure tech roles
4. Ajustar si necesario

**Durante anotación:**
- Anotar manualmente skills presentes
- Marcar tipo (hard/soft)
- Mapear a ESCO cuando sea posible
- Registrar confidence level
- Documentar casos edge

**Después de anotar:**
- Correr Pipeline A sobre los 300 jobs
- Correr Pipeline B (Gemma 3 4B y Llama 3 3B)
- Comparar contra ground truth
- Calcular métricas (P, R, F1)
- Identificar failure modes

## Resumen de Cambios del Algoritmo

**Versión 1 (Fallida):**
- Intentó llenar 144 celdas específicas: (país × idioma × rol × seniority)
- Resultado: Solo 80 jobs (27% del target)
- Problema: Demasiado estricto, muchas celdas sin candidatos

**Versión 2 (Implementada):**
- Prioridad jerárquica: idioma > país > rol > seniority (flexible)
- Selecciona los mejores N de cada (país, idioma)
- Dentro de esos, intenta llenar roles
- Seniority se acepta como esté disponible
- Resultado esperado: 300 jobs de alta calidad

## Referencias

- Tesis original: `docs/latex/chapters/04-analisis-problema.tex` (RD-3: mínimo 100K ofertas)
- Gold Standard README: `data/gold_standard/README.md`
- Script de selección: `scripts/select_gold_standard_jobs.py`
- Database schema: `src/database/migrations/005_add_gold_standard_columns.sql`

## Decisiones Pendientes

- [ ] ¿Incluir jobs "mixed" (ES+EN) en alguna categoría?
- [ ] ¿Ajustar distribución de roles si ciertos roles tienen muy pocos candidatos?
- [ ] ¿Definir threshold mínimo de quality score? (actualmente acepta todos)
- [ ] ¿Crear gold standard secundario con 100 jobs adicionales para validación cruzada?

---

**Última actualización:** 2025-11-03
**Autor:** Nico Camacho + Claude Code
**Estado:** Algoritmo v2 en implementación
