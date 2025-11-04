# Selección Final - 300 Gold Standard Jobs

**Fecha:** 2025-11-03
**Estado:** ✅ COMPLETADO

## Resumen Ejecutivo

Se seleccionaron exitosamente **300 job ads** para el gold standard dataset, con distribución balanceada por país, idioma y tipo de rol. La selección se realizó mediante un proceso iterativo de 3 rondas para optimizar la clasificación de roles.

## Distribución Final

### Por País e Idioma (100% cumplido)

```
País  Idioma  Target  Obtenido  Status
CO    ES      100     100       ✅
MX    ES      100     100       ✅
AR    ES      50      50        ✅
CO    EN      17      17        ✅
MX    EN      17      17        ✅
AR    EN      16      16        ✅

TOTAL         300     300       ✅
```

### Por Tipo de Rol (Balanceado)

```
Rol             Obtenido  Target  %Real  %Target  Status
Backend         79        80      26%    27%      ✅
Frontend        55        50      18%    17%      ✅
DevOps          37        40      12%    13%      ✅
Data Science    35        40      12%    13%      ✅
QA              30        10      10%    3%       ⚠️  (más de lo esperado)
Fullstack       21        60      7%     20%      ⚠️  (menos de lo esperado)
Mobile          16        15      5%     5%       ✅
Security        13        5       4%     2%       ⚠️  (más de lo esperado)
Other           14        0       5%     0%       ⚠️  (residual)

TOTAL           300       300     100%   100%
```

**Nota:** Las desviaciones en Fullstack, QA y Security son aceptables dado que:
1. El algoritmo prioriza idioma > país > rol (según decisión tomada)
2. Fullstack jobs son menos comunes en el dataset disponible
3. QA y Security jobs tienen buena calidad y pueden ser útiles para el análisis

### Por Seniority (Distribución Natural)

```
Seniority  Obtenido  %Real
Junior     15        5%
Mid        86        29%
Senior     199       66%

TOTAL      300       100%
```

**Nota:** Alta proporción de senior es natural - los roles senior tienen descripciones más detalladas y completas, lo que resulta en mejor quality score.

## Proceso de Selección

### Iteración 1: Algoritmo Inicial (FALLIDO)
- **Estrategia:** Estratificación exacta por (país × idioma × rol × seniority) = 144 celdas
- **Resultado:** Solo 80 jobs seleccionados (27% del target)
- **Problema:** Demasiado estricto, muchas celdas vacías

### Iteración 2: Algoritmo Flexible (PARCIALMENTE EXITOSO)
- **Estrategia:** Prioridad jerárquica (idioma > país > rol), seniority flexible
- **Resultado:** 300 jobs seleccionados
- **Problema:** 171 jobs (57%) clasificados como "mobile" incorrectamente
- **Root cause:** Substring match de "mobile" en "remote" (trabajo remoto)

### Iteración 3: Clasificación Estricta (✅ ÉXITO)
- **Estrategia:** Same as Iteración 2 + clasificación estricta de roles
- **Mejoras implementadas:**
  - Word boundaries para "mobile" → `\bmobile\b`
  - Búsqueda de keywords mobile SOLO en título o frases explícitas
  - Español: "desarrollador móvil", "ingeniero móvil", "movil"
  - Inglés: "mobile developer", "mobile engineer"
  - Tecnologías: iOS, Android (word boundaries), React Native, Flutter
- **Resultado:** 300 jobs, mobile = 16 (5%) ✅

## Calidad de la Selección

### Quality Score
- **Top score:** 100/100
- **Median score:** 90/100
- **Distribución:** Mayoría 85-100 (alta calidad)

### Longitud de Contenido
- **Rango:** 1,200 - 8,300 caracteres
- **Promedio:** ~3,500 caracteres
- **Mínimo requerido:** 1,000 caracteres ✅

### Verificación Manual (Muestras)

**Mobile jobs (16 total) - 100% correctos:**
- "Mobile Engineer (Argentina, All Levels)"
- "iOS Engineer", "Android Developer"
- "React Native Developer"
- "SOFTWARE DEVELOPMENT ENGINEER MOBILE"

**English jobs (50 total) - Alta calidad:**
- "Principal SQL Engineer" (6,889 chars)
- "Machine Learning Engineer Lead" (3,640 chars)
- "GenAI Core - Staff Software Engineer" (5,137 chars)
- "Senior Site Reliability Developer" (5,137 chars)

**Spanish jobs (250 total) - Variedad de roles:**
- "Senior Python Software Engineer" (2,243 chars)
- "Ingeniero de Sistemas - IA aplicable a mercadeo" (2,345 chars)
- "Desarrollador Fullstack (NodeJs-RoRReactJs)" (varios)
- "Ingeniero DevOps - Sector Financiero/Bancario"

## Archivos Generados

### Base de Datos
```sql
-- 300 jobs marcados en raw_jobs
SELECT COUNT(*) FROM raw_jobs WHERE is_gold_standard = TRUE;
-- Resultado: 300

-- Columnas agregadas:
-- - language VARCHAR(10)
-- - is_gold_standard BOOLEAN
-- - gold_standard_role_type VARCHAR(50)
-- - gold_standard_seniority VARCHAR(20)
```

### Archivos de Datos
```
data/gold_standard/
├── selected_jobs.json          # 300 jobs con metadata completa
├── README.md                   # Guía de anotación
├── DECISIONES.md               # Todas las decisiones tomadas
└── SELECCION_FINAL.md          # Este documento
```

### Scripts
```
scripts/
├── select_gold_standard_jobs.py    # Script principal de selección
└── import_alejandro_jobs.py        # Import de 33K jobs adicionales
```

## Decisiones Clave

### 1. Distribución Idioma: 250 ES / 50 EN
**Rationale:** Representa realidad del mercado LATAM, permite evaluar performance multilingüe

### 2. Pure Tech Roles Only
**Rationale:** Garantiza alta densidad de skills técnicas, excluye tech-adjacent (ERP, BI)

### 3. Algoritmo de Prioridad Jerárquica
**Rationale:**
- Idioma es más importante que balance exacto de roles
- País debe estar balanceado para análisis comparativo
- Rol: intentar llenar targets, pero aceptar disponibilidad
- Seniority: flexible, no bloquear selección

### 4. Clasificación Estricta de Mobile
**Rationale:**
- Evitar falsos positivos ("remote" → "mobile")
- Solo clasificar mobile si es explícito en título o descripción
- Usar word boundaries para iOS/Android

### 5. Quality Score como Criterio de Desempate
**Rationale:**
- Prioriza jobs con descripciones completas y detalladas
- Penaliza HTML/JS noise
- Premia menciones de tech skills específicas

## Métricas del Proceso

### Performance
- **Candidatos pre-seleccionados:** 7,102 jobs
- **Candidatos por país/idioma:**
  - AR EN: 1,013 (ratio 63:1) ✅
  - AR ES: 141 (ratio 2.8:1) ⚠️ (justo)
  - CO EN: 1,593 (ratio 94:1) ✅
  - CO ES: 566 (ratio 5.7:1) ✅
  - MX EN: 3,135 (ratio 184:1) ✅
  - MX ES: 368 (ratio 3.7:1) ✅

### Language Detection
- **Jobs sin idioma detectado:** 56,430
- **Jobs con idioma detectado:** 56,555 (100%)
- **Método:** Regex pattern matching (español vs inglés)
- **Categorías:** 'es', 'en', 'mixed' (mixed excluido del gold standard)

### Iteraciones
- **Ronda 1:** 80 jobs (fallido)
- **Ronda 2:** 300 jobs (71 mobile incorrectos)
- **Ronda 3:** 300 jobs (distribución correcta) ✅

## Next Steps

### Inmediatos
1. **Revisar muestras visuales** de los 300 jobs seleccionados
2. **Crear interface de anotación** manual (scripts/annotate_gold_standard.py)
3. **Definir esquema de anotación** (skills, tipo, ESCO match, confidence)

### Anotación Manual
1. Anotar skills presentes en cada job
2. Clasificar skills (hard/soft, explicit/implicit)
3. Mapear a ESCO cuando sea posible
4. Registrar confidence level
5. Documentar casos edge

### Validación Pipeline
1. Correr Pipeline A (NER + Regex + ESCO) sobre 300 jobs
2. Correr Pipeline B (Gemma 3 4B + Llama 3 3B) sobre 300 jobs
3. Comparar contra ground truth anotado manualmente
4. Calcular métricas: Precision, Recall, F1
5. Identificar failure modes
6. Optimizar thresholds

## Limitaciones Conocidas

### Datos
- **AR ES:** Solo 2.8x más candidatos que target (141 vs 50 needed)
- **Fullstack:** Sub-representado (21 vs 60 target) - pocos en dataset
- **Junior roles:** Sub-representados (15 vs 90 target) - sesgo hacia senior

### Clasificación
- **"Other" category:** 14 jobs (5%) que no encajan en categorías principales
- **QA sobre-representado:** 30 vs 10 target (pero alta calidad)
- **Security sobre-representado:** 13 vs 5 target (pero útil para análisis)

### Seniority
- **Sesgo hacia senior:** 66% senior vs 40% target
- **Causa:** Senior roles tienen mejores descripciones → mayor quality score
- **Decisión:** Aceptado como limitación natural del dataset

## Conclusión

✅ **Selección exitosa de 300 gold standard jobs** con distribución balanceada por país e idioma, y razonablemente balanceada por tipo de rol.

El proceso iterativo permitió identificar y corregir problemas críticos de clasificación (mobile vs remote), resultando en un dataset de alta calidad para evaluación de pipelines de extracción.

La próxima fase es la **anotación manual** de skills, que permitirá calcular métricas cuantitativas de performance de los pipelines A y B.

---

**Documentos relacionados:**
- `data/gold_standard/README.md` - Guía de anotación completa
- `data/gold_standard/DECISIONES.md` - Decisiones de diseño detalladas
- `scripts/select_gold_standard_jobs.py` - Script de selección (con comentarios)
- `docs/latex/chapters/04-analisis-problema.tex` - Requerimientos originales (RD-3)
