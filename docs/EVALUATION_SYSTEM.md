# Sistema de Evaluación de Pipelines

**Última actualización:** 2025-11-05

---

## 📦 QUÉ SE IMPLEMENTÓ

### Módulo Core: `src/evaluation/`

**1. `normalizer.py` (368 líneas)**
- Normalización unificada de skills
- Diccionario canónico con 200+ tecnologías
- Maneja variantes: `postgres`→`PostgreSQL`, `js`→`JavaScript`, `k8s`→`Kubernetes`
- Blacklist de términos no-skills
- Singleton pattern para performance

**2. `metrics.py` (260 líneas)**
- Cálculo de métricas: Precision, Recall, F1-Score, Accuracy
- Confusion Matrix: TP, FP, TN, FN
- Micro/Macro averaging
- Listas detalladas de errores (TP, FP, FN)

**3. `dual_comparator.py` (630 líneas)**
- **Modo 1:** Comparación vs Gold Standard
  - Texto normalizado (sin bias ESCO)
  - Post-mapeo ESCO (fairness - mismo código)
  - Análisis de impacto ESCO
- **Modo 2:** Comparación head-to-head de LLMs
  - Overlap (Jaccard similarity)
  - Estadísticas agregadas
- **Modo 3:** Análisis descriptivo sin gold standard
  - Stats básicas + cobertura ESCO

### Script: `scripts/evaluate_pipelines.py`

UN SOLO script que soporta 3 modos de evaluación.

---

## 🚀 CÓMO USAR

### **MODO 1: Gold Standard** (Evaluación Completa)

Compara pipelines contra el gold standard de 300 jobs anotados.

```bash
# Evaluar Pipeline A + múltiples LLMs (todas las skills)
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct gemma-3-4b-instruct qwen2.5-3b-instruct

# Solo Pipeline A
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a

# Solo LLMs
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines llama-3.2-3b-instruct gemma-3-4b-instruct

# Evaluar solo hard skills
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type hard

# Evaluar hard y soft por separado (genera 2 reportes)
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type both
```

**Output:**
- `EVALUATION_REPORT_<timestamp>.md` - Reporte ejecutivo
- `comparison_pure_<timestamp>.csv` - Métricas sin ESCO
- `comparison_esco_<timestamp>.csv` - Métricas post-ESCO
- `evaluation_<timestamp>.json` - Datos completos

**Incluye:**
1. Comparación 1: Texto normalizado (sin mapeo ESCO)
2. Comparación 2: Post-mapeo ESCO (mismo código para todos)
3. Análisis de impacto ESCO (Δ F1, skills perdidas)
4. Skills emergentes identificadas (no en ESCO)

---

### **MODO 2: LLM Comparison** (Head-to-Head)

Compara múltiples LLMs entre sí sin gold standard.

```bash
python scripts/evaluate_pipelines.py \
  --mode llm-comparison \
  --llm-models llama-3.2-3b gemma-3-4b qwen2.5-3b mistral-7b phi-3.5
```

**Output:**
- `LLM_COMPARISON_<timestamp>.md` - Reporte de comparación
- `llm_comparison_<timestamp>.json` - Datos completos

**Incluye:**
- Stats por modelo: total skills, unique skills, avg/job
- Overlap entre modelos (Jaccard similarity)
- Skills en común vs únicos

---

### **MODO 3: Descriptive** (Análisis sin Gold Standard)

Analiza un pipeline sin comparación.

```bash
# Analizar Pipeline A
python scripts/evaluate_pipelines.py \
  --mode descriptive \
  --pipeline pipeline-a

# Analizar un LLM
python scripts/evaluate_pipelines.py \
  --mode descriptive \
  --pipeline llama-3.2-3b-instruct
```

**Output:**
- `DESCRIPTIVE_<pipeline>_<timestamp>.md` - Reporte descriptivo
- `descriptive_<pipeline>_<timestamp>.json` - Datos

**Incluye:**
- Total jobs, skills extraídos, unique skills
- Avg skills/job
- Cobertura ESCO (% mapeados)
- Skills no mapeados (sample)

---

## 📊 ESTRUCTURA DE LOS REPORTES

### Reporte Gold Standard

```markdown
# Evaluación de Pipelines vs Gold Standard

## 1. Extracción Pura (Sin Mapeo ESCO)
| Pipeline           | Precision | Recall | F1-Score |
|--------------------|-----------|--------|----------|
| Pipeline A         | 0.85      | 0.78   | 0.81     |
| Pipeline B (Llama) | 0.88      | 0.82   | 0.85     |

**Ganador:** Pipeline B (F1=0.85)

## 2. Post-Mapeo ESCO
| Pipeline           | Precision | Recall | F1-Score | Cobertura ESCO |
|--------------------|-----------|--------|----------|----------------|
| Pipeline A         | 0.82      | 0.71   | 0.76     | 85%            |
| Pipeline B (Llama) | 0.85      | 0.75   | 0.80     | 89%            |

**Ganador:** Pipeline B (F1=0.80)

## 3. Impacto del Mapeo a ESCO
| Pipeline           | Δ F1     | Δ F1 (%) | Skills Perdidas |
|--------------------|----------|----------|-----------------|
| Pipeline A         | -0.0500  | -6.17%   | 4               |
| Pipeline B (Llama) | -0.0500  | -5.88%   | 3               |

## 4. Skills Emergentes (No en ESCO)
**Total:** 15

- Next.js
- Tailwind CSS
- FastAPI
- ...
```

---

## 🎯 CASOS DE USO

### Caso 1: Evaluar Pipeline A vs múltiples LLMs

**Objetivo:** Determinar si LLMs son mejores que NER+Regex

```bash
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b gemma-3-4b qwen2.5-3b qwen3-4b
```

**Resultado esperado:**
- Comparación P/R/F1 para cada pipeline
- Identificar cuál extrae mejor
- Ver impacto de ESCO en cada uno

---

### Caso 2: Comparar LLMs entre sí (sin gold standard)

**Objetivo:** Ver qué LLMs extraen más/menos skills, overlap

```bash
python scripts/evaluate_pipelines.py \
  --mode llm-comparison \
  --llm-models llama-3.2-3b gemma-3-4b qwen2.5-3b mistral-7b
```

**Resultado esperado:**
- Stats por LLM
- Overlap (¿extraen las mismas skills?)
- Identificar outliers

---

### Caso 3: Análisis descriptivo de Pipeline A

**Objetivo:** Ver stats generales sin comparación

```bash
python scripts/evaluate_pipelines.py \
  --mode descriptive \
  --pipeline pipeline-a
```

**Resultado esperado:**
- Total skills, unique, avg/job
- Cobertura ESCO
- Skills emergentes

---

## 🔧 REQUISITOS

### Base de Datos

**Para Modo Gold Standard:**
- Tabla `gold_standard_annotations` con 300 jobs anotados ✅
  - 7,848 skills totales (6,174 hard + 1,674 soft)
- Tabla `extracted_skills` con resultados de Pipeline A
- Tabla `enhanced_skills` con resultados de Pipeline B (por LLM)

**Para otros modos:**
- Solo `extracted_skills` o `enhanced_skills` según corresponda

### Ejecución de Pipelines

Este sistema **NO ejecuta los pipelines**, solo los evalúa.

Debes ejecutar los pipelines usando tu método habitual (orchestrator, scripts, etc.)

---

## 📐 METODOLOGÍA DE EVALUACIÓN DETALLADA

### Proceso de Evaluación en 3 Pasos

El sistema implementa un proceso de evaluación dual que permite responder tanto a la pregunta de **capacidad de extracción** como de **estandarización**:

```
┌─────────────────────────────────────────────────────────────────┐
│                  PASO 1: COMPARACIÓN PRE-ESCO                   │
│          (Validación de capacidad de extracción pura)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Gold Standard (texto)  ←→  Pipeline (texto)
                              ↓
              Normalización + Text Matching
                              ↓
         Métricas: Precision, Recall, F1-Score
         ✅ Captura skills emergentes (Next.js, Tailwind)


┌─────────────────────────────────────────────────────────────────┐
│                  PASO 2: MAPEO A ESCO (FAIRNESS)                │
│           (Todos los pipelines con MISMO código)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Re-mapear: Gold Standard → ESCO URIs
         Re-mapear: Pipeline → ESCO URIs
                              ↓
              ESCOMatcher3Layers (mismo para todos)
                              ↓
         ⚠️  Skills emergentes se pierden (no mapean)


┌─────────────────────────────────────────────────────────────────┐
│                 PASO 3: COMPARACIÓN POST-ESCO                   │
│             (Validación de estandarización)                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Gold ESCO URIs  ←→  Pipeline ESCO URIs
                              ↓
                    URI Matching Exacto
                              ↓
         Métricas: Precision, Recall, F1-Score
         + Cobertura ESCO (% mapeado)


┌─────────────────────────────────────────────────────────────────┐
│                  PASO 4: ANÁLISIS DE IMPACTO                    │
│          (Trade-off: Flexibilidad vs Estandarización)           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
         Δ F1 = F1_post_esco - F1_pre_esco
         Skills Perdidas = Emergentes no mapeadas
         Skills Emergentes (listado completo)
```

---

### ¿Cómo funciona la validación PRE-ESCO?

**Pregunta común:** *"Estamos contrastando texto aleatorio con texto aleatorio?"*

**Respuesta:** No. Usamos normalización inteligente + text matching:

#### 1. Normalización Canónica (`normalizer.py`)

Diccionario con **200+ tecnologías** en forma canónica:

```python
CANONICAL_FORMS = {
    'python': 'Python',
    'javascript': 'JavaScript',
    'js': 'JavaScript',
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'k8s': 'Kubernetes',
    'kubernetes': 'Kubernetes',
    # ... 200+ mappings
}
```

**Proceso:**
1. Gold Standard skill: `"postgres"` → Normalizado: `"PostgreSQL"`
2. Pipeline extrae: `"PostgreSQL"` → Normalizado: `"PostgreSQL"`
3. **Match exacto** ✅

#### 2. Validez del Approach

**¿Es válido comparar texto normalizado sin ESCO?**

✅ **SÍ, en el contexto de tech jobs:**

**Pros:**
- Tecnologías tienen nombres estándar (Python, React, Docker)
- Ambigüedad es rara en avisos tech
- Captura skills emergentes que ESCO no tiene
- No sesga por coverage de ESCO

**Contras:**
- Sinónimos raros pueden no matchear (ej: `Machine Learning` vs `ML`)
- Solución: diccionario canónico cubre casos comunes

**Justificación para tesis:**
- Evalúa **capacidad de extracción** sin penalizar innovación
- Complementado por validación post-ESCO para estandarización
- Permite identificar skills emergentes para actualizar ESCO

#### 3. Algoritmo de Normalización (5 Pasos)

**Código:** `normalizer.py` líneas 265-300

```python
def normalize(skill_text: str) -> str:
    """
    Normaliza un skill a su forma canónica.

    Pasos:
    1. Limpieza básica
    2. Remover acentos + lowercase (para lookup)
    3. Verificar blacklist
    4. Buscar en diccionario canónico
    5. Fallback: title case
    """
```

**PASO 1: Limpieza Básica**
```python
normalized = skill_text.strip()
# "  python  " → "python"
# "React.js " → "React.js"
```

**PASO 2: Remover Acentos + Lowercase (para lookup)**
```python
normalized_for_lookup = remove_accents(normalized).lower()
# "Comunicación" → "comunicacion"
# "PYTHON" → "python"
# "K8s" → "k8s"
```

**PASO 3: Verificar Blacklist** (descarta palabras que NO son skills)
```python
if normalized_for_lookup in BLACKLIST:
    return ""  # Descartada

# Blacklist = {"experiencia", "años", "año", "year", "meses", ...}
# "3 años de experiencia" → "" (descartada) ❌
# "experiencia en Python" → "" (descartada) ❌
```

**PASO 4: Buscar en Diccionario Canónico** (193 mappings)
```python
if normalized_for_lookup in CANONICAL_NAMES:
    return CANONICAL_NAMES[normalized_for_lookup]

# Ejemplos:
# "python" → "Python" ✅
# "js" → "JavaScript" ✅
# "k8s" → "Kubernetes" ✅
# "postgres" → "PostgreSQL" ✅
# "react.js" → "React" ✅
# "nodejs" → "Node.js" ✅
# "liderazgo" → "Liderazgo" ✅
# "leadership" → "Liderazgo" ✅ (mapea a español)
```

**PASO 5: Fallback - Title Case** (si no está en diccionario)
```python
return to_title_case(clean_text(normalized))

# "machine learning" → "Machine Learning"
# "data analysis" → "Data Analysis"
# "resolución de problemas" → "Resolución De Problemas"
```

**⚠️ Limitación del Fallback:**

Si una variante NO está en el diccionario canónico, puede NO matchear:

```python
# Ejemplo problemático:
Gold: "postgre sql" → NO en diccionario → Fallback: "Postgre Sql"
Pipeline: "postgres" → En diccionario → "PostgreSQL"

# Resultado: "Postgre Sql" ≠ "PostgreSQL" ❌ NO MATCH

# Solución: Agregar variante al diccionario
CANONICAL_NAMES = {
    'postgres': 'PostgreSQL',
    'postgresql': 'PostgreSQL',
    'postgre sql': 'PostgreSQL',  # ← Agregar
    'postgre': 'PostgreSQL',       # ← Agregar
}
```

---

### Cálculo de Métricas (Operaciones de Conjuntos)

**Código:** `metrics.py` líneas 94-174

Una vez normalizadas las skills, se calculan las métricas usando **operaciones de conjuntos**:

#### Paso 1: Operaciones de Conjuntos

```python
# Entrada:
gold_standard_skills = {"Python", "React", "PostgreSQL", "Docker"}
predicted_skills = {"Python", "React", "SQL", "Kubernetes"}

# Operación 1: Intersección (∩)
TP = gold_standard_skills & predicted_skills
   = {"Python", "React"}  # Skills correctamente identificadas

# Operación 2: Diferencia (-)
FP = predicted_skills - gold_standard_skills
   = {"SQL", "Kubernetes"}  # Skills extraídas pero NO en gold

FN = gold_standard_skills - predicted_skills
   = {"PostgreSQL", "Docker"}  # Skills del gold NO extraídas

# Counts
tp = len(TP) = 2
fp = len(FP) = 2
fn = len(FN) = 2
```

#### Paso 2: Fórmulas de Métricas

```python
# Precision: ¿Qué % de lo predicho es correcto?
Precision = TP / (TP + FP)
          = 2 / (2 + 2)
          = 2 / 4
          = 0.5000 (50%)

# Recall: ¿Qué % del gold se detectó?
Recall = TP / (TP + FN)
       = 2 / (2 + 2)
       = 2 / 4
       = 0.5000 (50%)

# F1-Score: Media armónica de Precision y Recall
F1 = 2 * (Precision * Recall) / (Precision + Recall)
   = 2 * (0.5 * 0.5) / (0.5 + 0.5)
   = 2 * 0.25 / 1.0
   = 0.5000 (50%)
```

#### Paso 3: Interpretación

```python
Support = len(gold_standard_skills) = 4  # Total en gold
Predicted = len(predicted_skills) = 4     # Total predicho

# Análisis:
# - Precision 50% → De 4 skills extraídas, solo 2 son correctas
# - Recall 50% → De 4 skills del gold, solo se detectaron 2
# - F1 50% → Balance entre Precision y Recall
```

---

### Proceso Completo: De BD a Métricas

**Flujo end-to-end de evaluación PRE-ESCO:**

```
PASO 1: CARGA DESDE BASE DE DATOS
───────────────────────────────────
Gold Standard:
  SELECT job_id, skill_text FROM gold_standard_annotations
  → {job_1: ["python", "REACT", "postgres"]}

Pipeline A:
  SELECT job_id, skill_text FROM extracted_skills
  WHERE extraction_method IN ('ner', 'regex')
  → {job_1: ["Python", "react.js", "SQL"]}


PASO 2: NORMALIZACIÓN POR JOB
───────────────────────────────────
for job_id in common_jobs:
    # Gold
    raw_gold = ["python", "REACT", "postgres"]
    normalized_gold = normalize_list(raw_gold)
                    = ["Python", "React", "PostgreSQL"]

    # Pipeline
    raw_pipeline = ["Python", "react.js", "SQL"]
    normalized_pipeline = normalize_list(raw_pipeline)
                        = ["Python", "React", "SQL"]


PASO 3: AGREGACIÓN (todos los jobs)
───────────────────────────────────
all_gold = set().union(*[normalized_gold_by_job[j] for j in jobs])
         = {"Python", "React", "PostgreSQL", ...}  # De todos los jobs

all_pipeline = set().union(*[normalized_pipeline_by_job[j] for j in jobs])
             = {"Python", "React", "SQL", ...}  # De todos los jobs


PASO 4: COMPARACIÓN (set operations)
───────────────────────────────────
TP = all_gold & all_pipeline        # Intersección
FP = all_pipeline - all_gold        # Solo en pipeline
FN = all_gold - all_pipeline        # Solo en gold


PASO 5: CÁLCULO DE MÉTRICAS
───────────────────────────────────
Precision = TP / (TP + FP)
Recall = TP / (TP + FN)
F1 = 2 * (P * R) / (P + R)
```

**Ejemplo con 2 jobs:**

```
Job 1:
  Gold: ["Python", "React", "PostgreSQL"]
  Pipeline: ["Python", "React", "SQL"]

Job 2:
  Gold: ["JavaScript", "Docker", "Git"]
  Pipeline: ["JavaScript", "Docker", "Kubernetes"]

Agregado:
  all_gold = {"Python", "React", "PostgreSQL", "JavaScript", "Docker", "Git"}
  all_pipeline = {"Python", "React", "SQL", "JavaScript", "Docker", "Kubernetes"}

Comparación:
  TP = {"Python", "React", "JavaScript", "Docker"}  ← 4 correctos
  FP = {"SQL", "Kubernetes"}  ← 2 falsos positivos
  FN = {"PostgreSQL", "Git"}  ← 2 falsos negativos

Métricas:
  Precision = 4 / (4 + 2) = 4/6 = 0.6667 (66.67%)
  Recall = 4 / (4 + 2) = 4/6 = 0.6667 (66.67%)
  F1 = 0.6667 (66.67%)
```

---

### ¿Cómo se manejan las Skills Emergentes?

**Skills emergentes** = Skills NO en taxonomía ESCO (14,174 skills)

Ejemplos: `Next.js`, `Tailwind CSS`, `FastAPI`, `Svelte`, `Vite`

#### Flujo Completo:

**En PRE-ESCO:**
```
Gold Standard: ["Python", "Next.js", "PostgreSQL"]
Pipeline extrae: ["Python", "Next.js", "React"]

→ Normalización:
  Gold: {"Python", "Next.js", "PostgreSQL"}
  Pipeline: {"Python", "Next.js", "React"}

→ Matching:
  TP: {"Python", "Next.js"}  ← Next.js cuenta como TP ✅
  FN: {"PostgreSQL"}
  FP: {"React"}

→ Precision = 2/3 = 0.67
→ Recall = 2/3 = 0.67
```

**En MAPEO A ESCO:**
```
Gold: ["Python", "Next.js", "PostgreSQL"]
→ ESCO Mapper:
  "Python" → http://data.europa.eu/esco/skill/abc123
  "Next.js" → None (no existe en ESCO) ❌
  "PostgreSQL" → http://data.europa.eu/esco/skill/def456

Gold ESCO: {abc123, def456}  ← Next.js desaparece


Pipeline: ["Python", "Next.js", "React"]
→ ESCO Mapper:
  "Python" → http://data.europa.eu/esco/skill/abc123
  "Next.js" → None ❌
  "React" → http://data.europa.eu/esco/skill/ghi789

Pipeline ESCO: {abc123, ghi789}  ← Next.js desaparece
```

**En POST-ESCO:**
```
Gold ESCO: {abc123, def456}
Pipeline ESCO: {abc123, ghi789}

→ TP: {abc123} (Python)
→ FN: {def456} (PostgreSQL)
→ FP: {ghi789} (React)

→ Precision = 1/2 = 0.50
→ Recall = 1/2 = 0.50

⚠️ Next.js ya no afecta las métricas (eliminado de ambos)
```

**En ANÁLISIS DE IMPACTO:**
```
Δ F1 = 0.50 - 0.67 = -0.17 (-25%)
Skills Perdidas = 1 (Next.js)
Skills Emergentes: ["Next.js"]
```

#### Reporte Final

```markdown
## 3. Impacto del Mapeo a ESCO
| Pipeline | Δ F1    | Skills Perdidas |
|----------|---------|-----------------|
| Pipeline | -0.17   | 1               |

## 4. Skills Emergentes (No en ESCO)
**Total:** 1

- Next.js
```

**Interpretación:**
- Pre-ESCO: F1=0.67 → Pipeline extrae bien, incluyendo skills modernas
- Post-ESCO: F1=0.50 → Estandarización tiene costo (pierde Next.js)
- Trade-off: Flexibilidad vs Estandarización explícito

---

### Evaluación por Tipo de Skill (Hard vs Soft)

El sistema soporta evaluar **hard skills** y **soft skills** por separado:

#### Uso:

```bash
# Evaluar todas las skills juntas (default)
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type all

# Evaluar solo hard skills
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type hard

# Evaluar solo soft skills
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type soft

# Evaluar ambas por separado (genera 2 reportes)
python scripts/evaluate_pipelines.py \
  --mode gold-standard \
  --pipelines pipeline-a llama-3.2-3b-instruct \
  --skill-type both
```

#### Output con `--skill-type both`:

Genera **2 reportes separados**:
- `EVALUATION_REPORT_hard_<timestamp>.md` - Solo hard skills
- `EVALUATION_REPORT_soft_<timestamp>.md` - Solo soft skills

Cada reporte incluye:
- Comparación Pre-ESCO (solo skills del tipo filtrado)
- Comparación Post-ESCO (solo skills del tipo filtrado)
- Impacto ESCO
- Skills emergentes del tipo

**Ejemplo:**

```markdown
# Evaluación de Pipelines vs Gold Standard (hard)

**Jobs evaluados:** 300
**Skill type:** hard
**Skills en gold standard:** 6,174

## 1. Extracción Pura (Sin Mapeo ESCO)
| Pipeline | Precision | Recall | F1-Score |
|----------|-----------|--------|----------|
| Pipeline A | 0.85 | 0.78 | 0.81 |
...
```

#### Implementación:

El sistema filtra skills por tipo **antes** de la comparación:

```python
# En dual_comparator.py
filtered_gold = gold_standard.filter_by_type('hard')
filtered_pipeline = pipeline.filter_by_type('hard')

# Solo skills hard participan en métricas
```

**Ventaja:** Permite analizar si los pipelines extraen mejor hard o soft skills.

---

## 💡 DECISIONES DE DISEÑO

### 1. Doble Comparación (Texto + ESCO)

**Comparación 1: Texto Normalizado**
- Evalúa capacidad de extracción pura
- No penaliza skills emergentes (Next.js, Tailwind, etc.)
- Fairness: no sesga por ESCO

**Comparación 2: Post-Mapeo ESCO**
- Re-mapea todos los pipelines con el MISMO código
- Pipeline A se re-mapea (no usa su mapeo existente)
- Evalúa estandarización
- Identifica skills no mapeables

**¿Por qué ambas?**
- Responde 2 preguntas distintas:
  1. ¿Qué extrae mejor? (sin ESCO)
  2. ¿Qué estandariza mejor? (con ESCO)

### 2. Normalización Unificada

**Problema:** Skills pueden tener variaciones (Python vs python vs PYTHON)

**Solución:** Diccionario canónico + reglas de normalización

**Aplicación:** Todos los pipelines se normalizan igual antes de comparar

### 3. Flexibilidad de Modos

**Problema:** No siempre tienes gold standard disponible

**Solución:** 3 modos independientes según qué tengas disponible

---

## 📝 ARCHIVOS DEL SISTEMA

```
src/evaluation/
├── __init__.py              # Exports
├── normalizer.py            # Normalización unificada (368 líneas)
├── metrics.py               # Cálculo de métricas (260 líneas)
└── dual_comparator.py       # Comparador multi-modo (630 líneas)

scripts/
└── evaluate_pipelines.py    # Script único de evaluación (400 líneas)

docs/
├── EVALUATION_SYSTEM.md     # Esta documentación
└── EVALUATION_IMPLEMENTATION_LOG.md  # Log detallado
```

**Total:** ~1,658 líneas de código + documentación

---

## ✅ CHECKLIST DE USO

### Antes de Evaluar

- [ ] Tienes gold standard en `gold_standard_annotations` (solo modo 1)
- [ ] Ejecutaste Pipeline A en los jobs que quieres evaluar
- [ ] Ejecutaste Pipeline B (LLMs) en los jobs que quieres evaluar
- [ ] Los jobs están en `extracted_skills` y/o `enhanced_skills`

### Ejecutar Evaluación

- [ ] Elegiste el modo apropiado (gold-standard, llm-comparison, descriptive)
- [ ] Especificaste los pipelines/LLMs correctos
- [ ] Verificaste el output directory

### Después de Evaluar

- [ ] Revisaste el reporte Markdown
- [ ] Verificaste las métricas hacen sentido
- [ ] Exportaste CSV si necesitas procesar más

---

## ❓ FAQ

**P: ¿Cómo ejecuto los pipelines?**
R: Este sistema NO ejecuta pipelines, solo los evalúa. Usa tu método habitual (orchestrator, scripts propios, etc.)

**P: ¿Puedo evaluar sin gold standard?**
R: Sí, usa modo `llm-comparison` o `descriptive`

**P: ¿Qué es "Pipeline A"?**
R: Pipeline A = NER + Regex + ESCO. Sus resultados están en tabla `extracted_skills`

**P: ¿Cómo especifico un LLM?**
R: Usa el nombre del modelo como aparece en `llm_model` column de `enhanced_skills`

**P: ¿El mapeo a ESCO es justo?**
R: Sí, todos los pipelines se re-mapean con el MISMO código (`ESCOMatcher3Layers`)

**P: ¿Puedo comparar Pipeline A vs Pipeline A?**
R: No tiene sentido, pero técnicamente funciona

**P: ¿Los reportes se sobreescriben?**
R: No, cada ejecución crea archivos con timestamp único

---

## 🎯 PRÓXIMOS PASOS

Este sistema está **completo y listo para usar**.

Opcionales (si necesitas):
- Visualizaciones (gráficos matplotlib/seaborn)
- Análisis por contexto (portal, país, tipo de skill)
- Export a otros formatos
- Integración con notebooks Jupyter

---

**Para cualquier duda, revisa el código - está documentado.**
