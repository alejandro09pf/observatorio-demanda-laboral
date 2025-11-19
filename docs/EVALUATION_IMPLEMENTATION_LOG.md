# Sistema de Evaluación de Pipelines - Log de Implementación

**Fecha de Inicio:** 2025-11-05
**Autores:** Nicolás Francisco Camacho Alarcón y Alejandro Pinzón
**Objetivo:** Evaluar y comparar Pipeline A (NER+Regex) vs Pipeline B (LLMs) contra Gold Standard

---

## 📋 CONTEXTO DEL PROYECTO

### Estado Actual de la Base de Datos

**Gold Standard:**
- ✅ 300 jobs seleccionados (`raw_jobs.is_gold_standard = TRUE`)
- ✅ 7,848 skills anotados manualmente (`gold_standard_annotations`)
- Formato: `skill_text` capitalizado (Python, JavaScript, PostgreSQL, etc.)

**Pipeline A (NER + Regex + ESCO):**
- ✅ Código implementado en `src/extractor/`
- ❌ NO ejecutado en los 300 jobs gold standard
- Tabla: `extracted_skills` (actualmente vacía)

**Pipeline B (LLM Direct Extraction):**
- ✅ Código implementado en `src/llm_processor/`
- ✅ 9 LLMs configurados (Gemma 3, Llama 3.2, Qwen 2.5, Qwen3, Mistral, Phi, DeepSeek)
- ❌ NO ejecutado en los 300 jobs gold standard
- Tabla: `enhanced_skills` (actualmente vacía)

**Infraestructura ESCO:**
- ✅ 14,174 skills en taxonomía (ESCO + O*NET + Manual)
- ✅ Embeddings generados (768D, multilingual-e5-base)
- ✅ Índice FAISS construido (30,147 q/s)
- ✅ ESCOMatcher3Layers con 3 capas (exact, fuzzy, semantic)

---

## 🎯 ESTRATEGIA DE EVALUACIÓN ACORDADA

### Decisión Clave: Doble Comparación

**PROBLEMA IDENTIFICADO:**
- Pipeline A ya mapea a ESCO durante extracción
- Pipeline B no mapea a ESCO (solo extrae texto)
- Gold Standard probablemente no tiene ESCO URIs
- Skills emergentes (Next.js, Tailwind, FastAPI) no están en ESCO

**SOLUCIÓN ACORDADA:**
Realizar **2 comparaciones independientes**:

1. **Comparación 1: Extracción Pura (Texto Normalizado)**
   - Evalúa capacidad de extracción SIN bias de ESCO
   - No penaliza skills emergentes
   - Completamente justo entre pipelines

2. **Comparación 2: Post-Mapeo ESCO (Estandarización)**
   - Mapear TODOS los pipelines con el MISMO código (`ESCOMatcher3Layers`)
   - Re-mapear Pipeline A (no usar su mapeo existente)
   - Evalúa qué pipeline produce skills más estandarizables
   - Calcula impacto de ESCO en métricas

### Normalización Unificada

**Reglas de normalización:**
1. Tecnologías conocidas: Diccionario canónico (PostgreSQL, JavaScript, React, AWS)
2. Variantes comunes: postgres→PostgreSQL, js→JavaScript, k8s→Kubernetes
3. Fallback: Title case (primera letra mayúscula)
4. Remover espacios extras, caracteres especiales

**Aplicación:**
- Normalizar Gold Standard antes de comparar
- Normalizar Pipeline A (ignorar esco_uri existente)
- Normalizar Pipeline B

---

## 📊 MÉTRICAS A CALCULAR

### Métricas Principales (Ambas Comparaciones)

**Por Pipeline:**
- **Precision:** % de skills extraídos que están en gold standard
- **Recall:** % de skills del gold standard que fueron detectados
- **F1-Score:** Media armónica de Precision y Recall
- **False Positives:** Skills extraídos que NO están en gold standard
- **False Negatives:** Skills en gold standard que NO fueron detectados

**Métricas Adicionales (Comparación 2):**
- **Cobertura ESCO:** % de skills que se pudieron mapear a ESCO
- **Skills Perdidas:** Skills que se perdieron en el mapeo
- **Delta F1:** Diferencia de F1 entre Comparación 1 y 2
- **Skills Emergentes:** Skills modernas no en ESCO

### Análisis por Contexto (Pipeline B)

**Por portal:** bumeran, computrabajo, elempleo, etc.
**Por país:** CO, MX, AR
**Por tipo de skill:** lenguajes, frameworks, cloud, databases, soft skills
**Por longitud de job ad:** corto (< 500 palabras), medio (500-1500), largo (> 1500)
**Por complejidad:** número de skills en gold standard (simple: < 20, complejo: > 40)

### Análisis de Rendimiento (Pipeline B)

**Velocidad:** segundos/job
**Tokens:** generados y consumidos
**Memoria:** uso de RAM durante inferencia

---

## 🏗️ ARQUITECTURA DEL SISTEMA

### Estructura de Directorios

```
src/evaluation/
├── __init__.py
├── normalizer.py              # Normalización unificada de skills
├── metrics.py                 # Precision, Recall, F1, Confusion Matrix
├── dual_comparator.py         # Comparación dual (texto + ESCO)
├── pipeline_evaluator.py      # Evalúa un pipeline individual
├── llm_evaluator.py           # Compara LLMs individuales
├── context_analyzer.py        # Análisis por contexto
└── report_generator.py        # Genera reportes MD/CSV/JSON

scripts/
├── run_pipeline_a_gold_standard.py      # Ejecuta Pipeline A en 300 jobs
├── run_pipeline_b_gold_standard.py      # Ejecuta Pipeline B (por modelo)
├── evaluate_extraction_pipelines.py     # Script principal de evaluación
└── generate_evaluation_reports.py       # Genera reportes finales

data/reports/
├── EVALUATION_REPORT.md                 # Reporte ejecutivo principal
├── pipeline_comparison_pure.csv         # Comparación 1 (texto)
├── pipeline_comparison_esco.csv         # Comparación 2 (ESCO)
├── llm_ranking.csv                      # Ranking de LLMs
├── llm_context_analysis.csv             # Performance por contexto
├── esco_impact_analysis.csv             # Análisis de impacto ESCO
└── charts/                              # Gráficos PNG
    ├── f1_comparison_pure.png
    ├── f1_comparison_esco.png
    ├── context_heatmap.png
    ├── confusion_matrix_*.png
    └── speed_vs_quality.png
```

---

## 🚀 PLAN DE EJECUCIÓN

### FASE 0: Preparación (30 min)
- [x] Análisis de código existente
- [x] Definición de estrategia de evaluación
- [ ] Crear documento de memoria persistente
- [ ] Crear estructura de directorios

### FASE 1: Normalización Unificada (30 min)
- [ ] Implementar `src/evaluation/normalizer.py`
- [ ] Diccionario canónico de tecnologías
- [ ] Funciones de normalización
- [ ] Tests unitarios de normalización

### FASE 2: Ejecutar Pipelines (1-2 horas)
- [ ] Script: `run_pipeline_a_gold_standard.py`
- [ ] Ejecutar Pipeline A en 300 jobs gold standard
- [ ] Script: `run_pipeline_b_gold_standard.py`
- [ ] Ejecutar Pipeline B con 4 LLMs:
  - [ ] Llama 3.2 3B Instruct
  - [ ] Gemma 3 4B Instruct
  - [ ] Qwen 2.5 3B Instruct
  - [ ] Qwen3 4B
- [ ] Verificar datos en BD

### FASE 3: Sistema de Métricas (1 hora)
- [ ] Implementar `src/evaluation/metrics.py`
- [ ] Precision, Recall, F1
- [ ] Confusion Matrix
- [ ] False Positives/Negatives detallados

### FASE 4: Comparador Dual (2 horas)
- [ ] Implementar `src/evaluation/dual_comparator.py`
- [ ] Comparación 1: Texto normalizado
- [ ] Comparación 2: Post-mapeo ESCO
- [ ] Análisis de impacto ESCO
- [ ] Identificación de skills perdidas

### FASE 5: Análisis de Contexto (1-2 horas)
- [ ] Implementar `src/evaluation/context_analyzer.py`
- [ ] Análisis por portal
- [ ] Análisis por país
- [ ] Análisis por tipo de skill
- [ ] Análisis de rendimiento (velocidad, tokens)

### FASE 6: Reportes y Visualizaciones (2 horas)
- [ ] Implementar `src/evaluation/report_generator.py`
- [ ] Reporte principal en Markdown
- [ ] Tablas CSV comparativas
- [ ] Gráficos:
  - [ ] Barras: F1-Score por pipeline
  - [ ] Heatmap: LLM × Contexto
  - [ ] Scatter: Precision vs Recall
  - [ ] Scatter: Velocidad vs Calidad
  - [ ] Confusion Matrices
  - [ ] Stacked bar: Tipos de skills

### FASE 7: Validación y Ajustes (1 hora)
- [ ] Revisar resultados
- [ ] Validar métricas
- [ ] Ajustar visualizaciones
- [ ] Documentar hallazgos

---

## 🎓 LLMs SELECCIONADOS PARA EVALUACIÓN

**Criterio de selección:** 2-4 modelos pequeños (2-4B), descargados, variedad de familias

1. **Llama 3.2 3B Instruct** (Meta)
   - Tamaño: 2.1 GB
   - Context: 128K tokens
   - Fortaleza: Multilingual, reasoning

2. **Gemma 3 4B Instruct** (Google)
   - Tamaño: 2.8 GB
   - Context: 8K tokens
   - Fortaleza: Última generación, balance velocidad/calidad

3. **Qwen 2.5 3B Instruct** (Alibaba)
   - Tamaño: 2.1 GB
   - Context: 32K tokens
   - Fortaleza: Structured outputs

4. **Qwen3 4B** (Alibaba)
   - Tamaño: 2.5 GB
   - Context: 32K tokens
   - Fortaleza: Última generación (Abril 2025), hybrid reasoning

---

## 📝 FORMATO DE RESULTADOS ESPERADOS

### Ejemplo de Output

```markdown
# Evaluación de Pipelines de Extracción

## 1. Comparación de Extracción Pura

### Métricas Generales
| Pipeline           | Precision | Recall | F1-Score | Skills/Job |
|--------------------|-----------|--------|----------|------------|
| Pipeline A         | 0.85      | 0.78   | 0.81     | 24.3       |
| Pipeline B (Llama) | 0.88      | 0.82   | 0.85     | 26.1       |
| Pipeline B (Gemma) | 0.83      | 0.79   | 0.81     | 23.8       |
| Pipeline B (Qwen2.5)| 0.86     | 0.80   | 0.83     | 25.2       |
| Pipeline B (Qwen3) | 0.87      | 0.81   | 0.84     | 25.8       |

**Conclusión:** Pipeline B (Llama) extrae mejor (+4.9% F1)

---

## 2. Comparación Post-Mapeo ESCO

### Métricas con ESCO
| Pipeline           | Precision | Recall | F1-Score | Cobertura ESCO |
|--------------------|-----------|--------|----------|----------------|
| Pipeline A         | 0.82      | 0.71   | 0.76     | 85%            |
| Pipeline B (Llama) | 0.85      | 0.75   | 0.80     | 89%            |
| Pipeline B (Gemma) | 0.80      | 0.73   | 0.76     | 85%            |

**Conclusión:** Pipeline B (Llama) sigue siendo mejor (+5.3% F1)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline           | Δ F1-Score | Skills Perdidas | Skills Emergentes |
|--------------------|------------|-----------------|-------------------|
| Pipeline A         | -6.2%      | 4 skills        | Next.js, Tailwind |
| Pipeline B (Llama) | -5.9%      | 3 skills        | FastAPI, Svelte   |

**Conclusión:** Mapeo a ESCO reduce F1 ~6% por pérdida de skills emergentes

---

## 4. Análisis por Contexto (Pipeline B)

### Performance por País
| LLM    | CO F1  | MX F1  | AR F1  | Avg F1 |
|--------|--------|--------|--------|--------|
| Llama  | 0.86   | 0.85   | 0.84   | 0.85   |
| Gemma  | 0.82   | 0.81   | 0.80   | 0.81   |

### Performance por Portal
| LLM    | bumeran | computrabajo | elempleo | Avg |
|--------|---------|--------------|----------|-----|
| Llama  | 0.87    | 0.84         | 0.85     | 0.85|
| Gemma  | 0.83    | 0.80         | 0.81     | 0.81|
```

---

## 🔬 PREGUNTAS DE INVESTIGACIÓN

### Preguntas Principales

1. **¿Pipeline A (NER+Regex) o Pipeline B (LLM) extrae mejor?**
   - Hipótesis: LLM extrae mejor (mayor recall, detecta implícitos)

2. **¿Cuál LLM funciona mejor para extracción de skills?**
   - Hipótesis: Modelos más grandes (Qwen3 4B, Llama 3.2 3B) > pequeños

3. **¿El mapeo a ESCO penaliza skills emergentes?**
   - Hipótesis: Sí, ~5-10% reducción de F1 por skills no en ESCO

4. **¿El contexto afecta la performance de LLMs?**
   - Hipótesis: Sí, algunos LLMs mejores para ciertos tipos de jobs

### Preguntas Secundarias

5. ¿Qué tipos de skills extrae mejor cada pipeline? (lenguajes vs frameworks vs soft skills)
6. ¿Cuál es el trade-off velocidad vs calidad en Pipeline B?
7. ¿Hay skills que ningún pipeline detecta correctamente? (blind spots)
8. ¿Los LLMs generan más false positives o false negatives?

---

## 📊 DECISIONES DE DISEÑO

### Decisión 1: Comparación Dual (Texto + ESCO)
**Fecha:** 2025-11-05
**Razón:** Evaluar extracción pura sin penalizar skills emergentes, luego evaluar estandarización
**Alternativas consideradas:** Solo comparar vía ESCO URIs (descartado por injusto)
**Impacto:** Permite ver impacto real de ESCO en métricas

### Decisión 2: Re-mapear Pipeline A a ESCO
**Fecha:** 2025-11-05
**Razón:** Garantizar fairness - mismo código de mapeo para ambos pipelines
**Alternativas consideradas:** Usar mapeo existente de Pipeline A (descartado por injusto)
**Impacto:** Comparación completamente justa

### Decisión 3: Normalización Case-Insensitive + Diccionario
**Fecha:** 2025-11-05
**Razón:** Gold Standard usa capitalización correcta, pipelines pueden variar
**Alternativas consideradas:** Fuzzy matching (descartado, demasiado permisivo)
**Impacto:** Elimina diferencias triviales (Python vs python vs PYTHON)

### Decisión 4: 4 LLMs para Evaluación Inicial
**Fecha:** 2025-11-05
**Razón:** Probar sistema con subset antes de expandir a los 9 modelos
**Selección:** Llama 3.2 3B, Gemma 3 4B, Qwen 2.5 3B, Qwen3 4B
**Criterio:** Variedad de familias, tamaños 2-4B, ya descargados
**Impacto:** Validación rápida, puede expandirse después

---

## 🐛 PROBLEMAS Y SOLUCIONES

### Problema 1: Pipeline A deduplica con lowercase pero guarda original
**Fecha:** 2025-11-05
**Síntoma:** Puede tener "python", "Python", "PYTHON" como 3 entries
**Causa:** Línea 231 en `extractor/pipeline.py` usa `lower()` para deduplicar pero guarda `skill.skill_text` original
**Solución:** Normalizar antes de guardar en BD
**Estado:** Pendiente de implementar en scripts de ejecución

### Problema 2: Pipeline B no mapea a ESCO
**Fecha:** 2025-11-05
**Síntoma:** Tabla `enhanced_skills` vacía, no hay esco URIs
**Causa:** Pipeline B solo extrae, no mapea (diseño intencional)
**Solución:** Mapear en Comparación 2 usando `ESCOMatcher3Layers`
**Estado:** Por implementar en `dual_comparator.py`

---

## 📈 RESULTADOS Y HALLAZGOS

### Ejecución Pipeline A
**Fecha:** [Pendiente]
**Jobs procesados:** 0/300
**Skills extraídos:** 0
**Tiempo:** -
**Notas:** -

### Ejecución Pipeline B - Llama 3.2 3B
**Fecha:** [Pendiente]
**Jobs procesados:** 0/300
**Skills extraídos:** 0
**Tiempo:** -
**Notas:** -

### Ejecución Pipeline B - Gemma 3 4B
**Fecha:** [Pendiente]
**Jobs procesados:** 0/300
**Skills extraídos:** 0
**Tiempo:** -
**Notas:** -

### Comparación 1: Extracción Pura
**Fecha:** [Pendiente]
**Pipeline ganador:** -
**Delta F1:** -
**Hallazgos clave:** -

### Comparación 2: Post-ESCO
**Fecha:** [Pendiente]
**Pipeline ganador:** -
**Cobertura ESCO promedio:** -
**Skills emergentes identificadas:** -
**Hallazgos clave:** -

---

## 🔗 REFERENCIAS

### Código Relevante
- `src/extractor/pipeline.py` - Pipeline A implementation
- `src/extractor/esco_matcher_3layers.py` - ESCO matcher (exact, fuzzy, semantic)
- `src/llm_processor/pipeline.py` - Pipeline B implementation
- `src/llm_processor/model_registry.py` - LLM configurations

### Documentación
- `docs/CORRECTED_COMPLETE_FLOW.md` - Flujo completo del sistema
- `docs/PIPELINE_B_IMPLEMENTATION.md` - Implementación Pipeline B
- `data/gold_standard/README.md` - Descripción del gold standard

### Papers de Referencia
- ESCO Taxonomy v1.1.0 - European Skills Classification
- O*NET Hot Technologies - US Labor Department

---

## ✅ CHECKLIST DE PROGRESO

### Preparación
- [x] Análisis de código existente
- [x] Definición de estrategia
- [ ] Documento de memoria persistente
- [ ] Estructura de directorios

### Implementación
- [ ] Normalizer
- [ ] Metrics calculator
- [ ] Dual comparator
- [ ] Context analyzer
- [ ] Report generator

### Ejecución
- [ ] Pipeline A en 300 jobs
- [ ] Pipeline B (Llama) en 300 jobs
- [ ] Pipeline B (Gemma) en 300 jobs
- [ ] Pipeline B (Qwen 2.5) en 300 jobs
- [ ] Pipeline B (Qwen3) en 300 jobs

### Análisis
- [ ] Comparación 1 (texto)
- [ ] Comparación 2 (ESCO)
- [ ] Análisis de contexto
- [ ] Análisis de rendimiento
- [ ] Identificar skills emergentes

### Documentación
- [ ] Reporte principal
- [ ] Tablas CSV
- [ ] Gráficos
- [ ] Conclusiones
- [ ] Recomendaciones

---

**Última actualización:** 2025-11-05
**Próximo paso:** Implementar normalizer y crear estructura de directorios


---

## 📝 PROGRESO DE IMPLEMENTACIÓN

### Sesión: 2025-11-05

#### FASE 0: Preparación ✅ COMPLETADA
- [x] Análisis de código existente
- [x] Definición de estrategia de evaluación (doble comparación)
- [x] Creación de documento de memoria persistente
- [x] Creación de estructura de directorios

#### FASE 1: Normalización Unificada ✅ COMPLETADA
**Archivo:** `src/evaluation/normalizer.py` (368 líneas)

**Implementado:**
- Diccionario canónico con 200+ tecnologías
  - Lenguajes: Python, JavaScript, Java, C++, Go, Rust, etc.
  - Frameworks: React, Vue.js, Django, Flask, Spring Boot, etc.
  - Databases: PostgreSQL, MySQL, MongoDB, Redis, etc.
  - Cloud: AWS, Azure, GCP, Heroku, etc.
  - DevOps: Docker, Kubernetes, Jenkins, Terraform, etc.
- Normalización de variantes: postgres→PostgreSQL, js→JavaScript, k8s→Kubernetes
- Blacklist de términos no-skills: experiencia, años, salario, etc.
- Funciones de limpieza y title case
- Singleton pattern para performance

**Decisiones:**
- Case-insensitive matching con diccionario
- Preservar acrónimos (AWS, API, SQL)
- Remover acentos para matching
- Fallback a Title Case para skills desconocidas

#### FASE 2: Sistema de Métricas ✅ COMPLETADA
**Archivo:** `src/evaluation/metrics.py` (260 líneas)

**Implementado:**
- Clase `MetricsCalculator` con métodos:
  - `calculate()`: Precision, Recall, F1, Accuracy
  - `calculate_aggregate()`: Micro-averaging para múltiples jobs
  - `calculate_per_job()`: Métricas individuales por job
  - `calculate_macro_average()`: Macro-averaging
- Clase `ConfusionMatrix`: TP, FP, TN, FN
- Clase `EvaluationMetrics`: Container de todas las métricas
- Funciones helper: `calculate_metrics()`, `compare_pipelines()`, `print_metrics()`

**Métricas calculadas:**
- Precision: TP / (TP + FP)
- Recall: TP / (TP + FN)
- F1-Score: 2 * (P * R) / (P + R)
- Accuracy: (TP + TN) / Total
- Listas detalladas de TP, FP, FN

#### FASE 3: Comparador Dual ✅ COMPLETADA
**Archivo:** `src/evaluation/dual_comparator.py` (430 líneas)

**Implementado:**
- Clase `DualPipelineComparator`:
  - `load_gold_standard()`: Carga anotaciones manuales
  - `load_pipeline_a()`: Carga extracted_skills
  - `load_pipeline_b()`: Carga enhanced_skills por modelo
  - `compare_pure_text()`: Comparación 1 (texto normalizado)
  - `compare_post_esco()`: Comparación 2 (post-mapeo ESCO)
  - `analyze_esco_impact()`: Análisis de impacto
  - `run_dual_comparison()`: Orquestador principal
- Dataclasses:
  - `PipelineData`: Container de skills por job
  - `ComparisonResult`: Resultado de comparación
  - `DualComparisonReport`: Reporte completo

**Características:**
- Fairness: Re-mapea Pipeline A a ESCO (no usa mapeo existente)
- Normalización unificada para todos
- Identifica skills emergentes (perdidas en mapeo ESCO)
- Calcula cobertura ESCO por pipeline
- Análisis de impacto: Δ F1, Δ Precision, Δ Recall

#### FASE 4: Scripts de Ejecución ✅ COMPLETADA

**Script 1:** `scripts/run_pipeline_a_gold_standard.py` (200 líneas)
- Ejecuta Pipeline A (NER + Regex + ESCO) en 300 jobs gold standard
- Normaliza skills antes de guardar (fairness)
- Guarda en tabla `extracted_skills`
- Flags: `--limit N`, `--dry-run`
- Estadísticas: total jobs, skills extraídos, tiempo promedio

**Script 2:** `scripts/run_pipeline_b_gold_standard.py` (220 líneas)
- Ejecuta Pipeline B (LLM) en 300 jobs gold standard
- Soporte para cualquier modelo del registry
- Normaliza skills antes de guardar
- Guarda en tabla `enhanced_skills` con `llm_model`
- Flags: `--model <name>`, `--limit N`, `--dry-run`, `--list-models`
- Tracking de velocidad por job

**Script 3:** `scripts/evaluate_extraction_pipelines.py` (280 líneas)
- Script principal de evaluación
- Usa `DualPipelineComparator` para comparar
- Soporta múltiples LLMs simultáneos
- Genera 3 tipos de reportes:
  1. Markdown: `EVALUATION_REPORT.md` (reporte ejecutivo)
  2. CSV: `pipeline_comparison_pure.csv`, `pipeline_comparison_esco.csv`
  3. JSON: `evaluation_results.json` (datos completos)
- Flags: `--llm-models <names>`, `--pipeline-a-only`, `--output-dir`

#### Módulo de Evaluación Creado
**Estructura:**
```
src/evaluation/
├── __init__.py           (Exports principales)
├── normalizer.py         (368 líneas) ✅
├── metrics.py            (260 líneas) ✅
└── dual_comparator.py    (430 líneas) ✅
```

**Total de código:** ~1,060 líneas implementadas

---

## 🚀 PRÓXIMOS PASOS

### Ejecución Inmediata

1. **Ejecutar Pipeline A** (5-10 min):
```bash
python scripts/run_pipeline_a_gold_standard.py
```

2. **Ejecutar Pipeline B con 4 LLMs** (1-2 horas total):
```bash
# Llama 3.2 3B (~15-20 min)
python scripts/run_pipeline_b_gold_standard.py --model llama-3.2-3b-instruct

# Gemma 3 4B (~15-20 min)
python scripts/run_pipeline_b_gold_standard.py --model gemma-3-4b-instruct

# Qwen 2.5 3B (~15-20 min)
python scripts/run_pipeline_b_gold_standard.py --model qwen2.5-3b-instruct

# Qwen3 4B (~15-20 min)
python scripts/run_pipeline_b_gold_standard.py --model qwen3-4b
```

3. **Generar Evaluación** (1-2 min):
```bash
python scripts/evaluate_extraction_pipelines.py \
  --llm-models llama-3.2-3b-instruct gemma-3-4b-instruct qwen2.5-3b-instruct qwen3-4b
```

### Tareas Pendientes (Opcionales)

- [ ] Context analyzer (análisis por portal, país, tipo de skill)
- [ ] Report generator con gráficos (matplotlib/seaborn)
- [ ] Análisis de rendimiento (velocidad vs calidad)
- [ ] Skills emergentes ranking
- [ ] Expandir con más LLMs (si resultados son buenos)

---

## 📊 OUTPUTS ESPERADOS

Después de ejecutar todo, tendrás:

**En base de datos:**
- `extracted_skills`: ~7,200 skills (300 jobs × 24 skills/job promedio) - Pipeline A
- `enhanced_skills`: ~31,200 skills (300 jobs × 26 skills/job × 4 LLMs) - Pipeline B

**En data/reports/:**
- `EVALUATION_REPORT.md`: Reporte ejecutivo con conclusiones
- `pipeline_comparison_pure.csv`: Métricas comparación texto
- `pipeline_comparison_esco.csv`: Métricas comparación ESCO
- `evaluation_results.json`: Datos completos en JSON

**Tiempo estimado total:** ~2-3 horas

---

**Última actualización:** 2025-11-05 14:55:23

