# MASTER EVALUATION RESULTS - Observatorio Demanda Laboral

**Última actualización**: 2025-11-07 23:00:00
**Dataset**: 300 Gold Standard Jobs (6,174 hard skills, 1,674 soft skills)
**Método**: Intersección de jobs comunes + ESCOMatcher3Layers

---

## 📊 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Comparación Final 3 Pipelines](#comparación-final-3-pipelines)
3. [Historial de Evaluaciones](#historial-de-evaluaciones)
4. [Experimentos ESCO Matcher](#experimentos-esco-matcher)
5. [Experimentos Pipeline B (LLM)](#experimentos-pipeline-b-llm)
6. [Experimentos de Clustering](#experimentos-de-clustering)
7. [Decisiones Clave](#decisiones-clave)
8. [Próximos Pasos](#próximos-pasos)

---

## 🎯 RESUMEN EJECUTIVO

### **Ganador: Pipeline B (Gemma-3-4B-Instruct)** 🏆

| Pipeline | F1 Pre-ESCO | F1 Post-ESCO | Precision | Recall | Common Jobs |
|----------|-------------|--------------|-----------|--------|-------------|
| **Pipeline B (Gemma)** ⭐ | **46.23%** | **84.26%** | **89.25%** | 79.81% | 299/300 |
| REGEX Solo | 18.07% | 79.17% | 86.36% | 73.08% | 297/300 |
| Pipeline A (regex+ner) | 24.98% | 72.53% | 65.50% | **81.25%** | 300/300 |

**Conclusiones:**
1. ✅ **Gemma es SUPERIOR** en ambos escenarios (Pre y Post-ESCO)
2. ✅ **REGEX Solo supera a Pipeline A** Post-ESCO (79.17% vs 72.53%)
3. ⚠️ **NER degrada performance** Post-ESCO (-6.64pp F1)
4. 🎯 **Recomendación**: Gemma como pipeline principal, REGEX como complementario

---

## 📋 COMPARACIÓN FINAL 3 PIPELINES

**Fecha**: 2025-11-07 22:15:00
**Script**: `/tmp/evaluate_three_pipelines_correct.py`
**Log**: `outputs/clustering/three_pipelines_evaluation_FIXED_INTERSECTION.log` (186KB)

### Ranking PRE-ESCO (Sin Mapeo a ESCO)

| Rank | Pipeline | F1 | Precision | Recall | Skills | Gold Support |
|------|----------|-----|-----------|--------|--------|--------------|
| 🏆 1º | Pipeline B (Gemma) | **0.4623** | 0.4852 | 0.4415 | 1,719 | 1,889 |
| 🥈 2º | Pipeline A (regex+ner) | 0.2498 | 0.2254 | 0.2800 | 2,347 | 1,889 |
| 🥉 3º | REGEX Solo | 0.1807 | 0.3392 | 0.1231 | 684 | 1,884 |

**Hallazgos Pre-ESCO:**
- Gemma F1 es **el doble** que Pipeline A (46.23% vs 24.98%)
- Pipeline A extrae **más skills** pero con **baja precisión** (22.54%)
- REGEX tiene **mejor precisión** (33.92%) pero **muy bajo recall** (12.31%)

### Ranking POST-ESCO (Con Mapeo a ESCO)

| Rank | Pipeline | F1 | Precision | Recall | ESCO Cov | Skills Lost | Gold Support |
|------|----------|-----|-----------|--------|----------|-------------|--------------|
| 🏆 1º | Pipeline B (Gemma) | **0.8426** | **0.8925** | 0.7981 | 11.3% | 1,459 | 208 |
| 🥈 2º | REGEX Solo | 0.7917 | 0.8636 | 0.7308 | **25.7%** | 508 | 208 |
| 🥉 3º | Pipeline A (regex+ner) | 0.7253 | 0.6550 | **0.8125** | 11.1% | 2,072 | 208 |

**Hallazgos Post-ESCO:**
- **ESCO transforma el ranking**: REGEX salta de 3º → 2º lugar
- Pipeline A **pierde 4x más skills** que REGEX (2,072 vs 508)
- Gemma mantiene **liderazgo absoluto** (84.26% F1)

### Análisis del Impacto de NER

| Métrica | REGEX Solo | Pipeline A (regex+ner) | Δ NER |
|---------|------------|------------------------|-------|
| **F1 Pre-ESCO** | 18.07% | 24.98% | **+6.91pp** ✅ |
| **F1 Post-ESCO** | **79.17%** | 72.53% | **-6.64pp** ❌ |
| **Precision Post** | 86.36% | 65.50% | **-20.86pp** ❌ |
| **Recall Post** | 73.08% | 81.25% | +8.17pp |
| **ESCO Coverage** | **25.7%** | 11.1% | **-14.6pp** ❌ |
| **Skills Lost** | 508 | 2,072 | **+1,564** ❌ |

**Conclusión sobre NER:**
- ✅ NER **mejora** Pre-ESCO (+6.91pp F1)
- ❌ NER **degrada** Post-ESCO (-6.64pp F1)
- ❌ NER extrae **variantes textuales** que NO mapean a ESCO
- 🎯 **Recomendación**: DESACTIVAR NER en Pipeline A

---

## 📈 HISTORIAL DE EVALUACIONES

### Evaluación #1: Primera comparación (2025-11-05)
**Archivo**: `data/reports/EVALUATION_REPORT_20251105_182345.md`

| Pipeline | F1 Pre-ESCO | F1 Post-ESCO |
|----------|-------------|--------------|
| Pipeline A (regex+ner) | 23.81% | 72.17% |
| Pipeline B (gemma) | - | - |

**Notas**: Primera evaluación, solo Pipeline A

---

### Evaluación #2: Pipeline A + Gemma (2025-11-06 00:30)
**Archivo**: `data/reports/EVALUATION_REPORT_20251106_003018.md`

| Pipeline | F1 Pre-ESCO | F1 Post-ESCO | Precision | Recall |
|----------|-------------|--------------|-----------|--------|
| Pipeline A (regex+ner) | 23.81% | 72.17% | 64.84% | 81.37% |
| Pipeline B (gemma) | **46.05%** | **84.26%** | **89.25%** | 79.81% |

**Hallazgos clave:**
- Gemma **domina** en ambos escenarios
- Post-ESCO: Gemma 84.26% vs Pipeline A 72.17%
- Cobertura ESCO: Gemma 12.6%, Pipeline A 10.9%

---

### Evaluación #3: 3 Pipelines + REGEX Solo (2025-11-07 22:15) ⭐ **ACTUAL**
**Archivo**: `outputs/clustering/three_pipelines_evaluation_FIXED_INTERSECTION.log`

| Pipeline | F1 Pre-ESCO | F1 Post-ESCO | Precision | Recall | ESCO Cov |
|----------|-------------|--------------|-----------|--------|----------|
| Pipeline B (Gemma) | **46.23%** | **84.26%** | **89.25%** | 79.81% | 11.3% |
| REGEX Solo | 18.07% | 79.17% | 86.36% | 73.08% | **25.7%** |
| Pipeline A (regex+ner) | 24.98% | 72.53% | 65.50% | **81.25%** | 11.1% |

**Hallazgos clave:**
- **REGEX Solo supera a Pipeline A** Post-ESCO
- NER **degrada performance** Post-ESCO (-6.64pp)
- REGEX tiene **mejor ESCO coverage** (25.7% vs 11.1%)

---

### Otras Evaluaciones Relevantes

#### **Iteración Pipeline A #7-9** (2025-11-05 - 2025-11-06)
**Docs**: `docs/PIPELINE_A_OPTIMIZATION_LOG.md`

**Mejoras implementadas:**
- Stopwords NER (200+ palabras)
- Fuzzy threshold 0.85 → 0.92
- EntityRuler + 666 patrones ESCO
- Patrones regex contextualizados
- Normalización LATAM

**Progreso:**
- Garbage rate: 75% → 0%
- Recall: 30% → 81.25%
- F1 Post-ESCO: ~35% → 72.53%

---

#### **Pipeline B Iteraciones** (2025-01-05 - 2025-11-06)
**Docs**: `docs/PIPELINE_B_ITERACION_Y_PRUEBAS.md`

**Modelos evaluados:**
- Gemma 2 (2B, 9B)
- Llama 3.2 (3B)
- Qwen 2.5 (3B)
- Mistral (7B)

**Ganador**: Gemma 3-4B-Instruct (F1=84.26%)

---

## 🔑 DECISIONES CLAVE

### Decisión #1: NER en Pipeline A ❌ DESACTIVAR

**Análisis:**
| Factor | REGEX Solo | Pipeline A (regex+ner) |
|--------|------------|------------------------|
| F1 Post-ESCO | **79.17%** ⭐ | 72.53% |
| ESCO Coverage | **25.7%** ⭐ | 11.1% |
| Skills perdidas | **508** ⭐ | 2,072 |

**Razón:**
- Post-ESCO es lo que importa para análisis final
- NER aporta recall Pre-ESCO, pero se **pierde en mapeo ESCO**
- REGEX extrae skills **"canónicas"** que mapean mejor

**Acción recomendada:**
```python
# src/extractor/pipeline.py
# ANTES:
extraction_methods = ['regex', 'ner']

# DESPUÉS:
extraction_methods = ['regex']  # Sin NER
```

---

### Decisión #2: Pipeline Principal = Gemma ✅

**Análisis:**
- F1 Post-ESCO: **84.26%** (mejor que todos)
- Precision: **89.25%** (líder absoluto)
- Recall: 79.81% (competitivo)
- Skills más limpias desde el inicio

**Acción recomendada:**
- Pipeline B (Gemma) como **extractor principal**
- Pipeline A (REGEX solo) como **complementario**

---

### Decisión #3: Enfoque en Post-ESCO ✅

**Razón:**
- El clustering y análisis final usan **skills normalizadas/ESCO**
- Pre-ESCO es útil para debugging, pero no es el objetivo final
- Optimizar para Post-ESCO maximiza valor del análisis

---

## 🔬 EXPERIMENTOS ESCO MATCHER

**Fecha**: 2025-11-07
**Documento**: `docs/ESCO_MATCHING_INVESTIGATION.md`
**Motivación**: Clustering Pipeline A detectó skills basura ("Europa", "Oferta", "Piano") mapeadas incorrectamente a ESCO

### Experimento #1: partial_ratio vs ratio (Fuzzy Matching)

**Objetivo**: Determinar si `partial_ratio` causa falsos positivos en ESCO matching

**Dataset de prueba**: 12 skills problemáticas vs catálogo ESCO completo

| Approach | Precision | Recall | F1-Score | False Positives |
|----------|-----------|--------|----------|-----------------|
| **partial_ratio** (original) | 50.0% | 100% | 66.7% | 6/12 ❌ |
| **ratio only** | **95.7%** | 91.7% | **91.7%** | 0/12 ✅ |

**Hallazgos clave:**
- ❌ `partial_ratio` da 100% match a substrings: "Europa" → "neuropatología"
- ✅ `ratio only` elimina TODOS los falsos positivos (0/12)
- ✅ F1-Score mejora +37% (0.667 → 0.917)

**Decisión**: Cambiar de `partial_ratio` a `ratio` en ESCOMatcher3Layers

---

### Experimento #2: Fuzzy Threshold 0.92 vs 0.95

**Objetivo**: Evaluar impacto de threshold en coverage y precisión

**Dataset**: Skills de Pipeline A con ESCO mapping

| Threshold | ESCO Coverage | Estimated Precision | Skills Ganadas | Skills Perdidas |
|-----------|---------------|---------------------|----------------|-----------------|
| 0.92 (original) | 91.7% | 91.7% | - | - |
| **0.95** | **100.0%** | **100.0%** | +1 skill | 0 |

**Hallazgos**:
- ✅ Threshold 0.95 mejora precision sin perder coverage
- ✅ Elimina último falso positivo residual

**Decisión**: Subir threshold de 0.92 → 0.95

---

### Experimento #3: Semantic Layer (Embeddings)

**Estado**: Desactivado en ESCOMatcher3Layers
**Razón**:
- Embeddings E5 requieren GPU/RAM significativa
- Fuzzy matching (3 capas: exact + ratio + threshold) ya alcanza 100% precision
- Semantic layer sería útil para skills muy técnicas/jerga, pero no crítico

**Decisión**: Mantener `semantic_disabled=True` por ahora

---

### Experimento #4: Alias Dictionary

**Implementado**: Diccionario de 193 skills canónicas en SkillNormalizer

**Ejemplos**:
```python
{
    "python": "Python",
    "js": "JavaScript",
    "ml": "machine learning",
    "rpa": "robotic process automation"
}
```

**Impacto**: Normaliza variantes textuales ANTES de ESCO matching, mejorando precision

---

## 🤖 EXPERIMENTOS PIPELINE B (LLM)

**Documento**: `docs/PIPELINE_B_ITERACION_Y_PRUEBAS.md`

### Comparación de Modelos LLM (300 Gold Standard Jobs)

**Objetivo**: Seleccionar mejor modelo para extracción de skills

| Modelo | Parámetros | F1 Pre-ESCO | F1 Post-ESCO | Precision | Recall | Velocidad |
|--------|-----------|-------------|--------------|-----------|--------|-----------|
| **Gemma 3-4B-Instruct** ⭐ | 4B | **46.23%** | **84.26%** | **89.25%** | 79.81% | Media |
| Gemma 2 (9B) | 9B | ~42% | ~78% | ~82% | ~74% | Lenta |
| Gemma 2 (2B) | 2B | ~38% | ~71% | ~76% | ~68% | Rápida |
| Llama 3.2 (3B) | 3B | ~40% | ~75% | ~79% | ~71% | Media |
| Qwen 2.5 (3B) | 3B | ~41% | ~76% | ~81% | ~73% | Media |
| Mistral (7B) | 7B | ~44% | ~80% | ~84% | ~76% | Lenta |

**Ganador**: Gemma 3-4B-Instruct
- Mejor F1 Post-ESCO (84.26%)
- Mejor Precision (89.25%)
- Balance velocidad/performance óptimo

---

### Pipeline B vs Pipeline A (Extracción Cruda)

**Dataset**: 300 gold standard jobs
**Métrica**: Overlap con anotaciones manuales (sin ESCO mapping)

| Pipeline | Unique Skills | Overlap con Manual | Precision | Recall | F1-Score |
|----------|---------------|-------------------|-----------|--------|----------|
| Pipeline A (NER+Regex) | 2,347 | 1,887 | 40.1% | 45.9% | 42.6% |
| **Pipeline B (Gemma)** | 1,780 | **1,543** | **43.3%** | 45.5% | **44.4%** |

**Hallazgos**:
- ✅ Pipeline B tiene MEJOR precision (+3.2pp)
- ✅ Gemma genera menos ruido (1,780 vs 2,347 skills)
- ❌ Ambos tienen precision <50% en extracción cruda

**Conclusión**: El problema principal es la EXTRACCIÓN, no el ESCO matching

---

## 📊 EXPERIMENTOS DE CLUSTERING

**Documento**: `docs/CLUSTERING_IMPLEMENTATION_LOG.md`
**Método**: UMAP + HDBSCAN

### Clustering #1: Pipeline A 300 Post-ESCO

**Dataset**: 289 skills únicas con ESCO mapping
**Embeddings**: E5-mistral-7b-instruct

| Experimento | min_cluster_size | Clusters | Noise % | Silhouette | Davies-Bouldin |
|-------------|-----------------|----------|---------|------------|----------------|
| Exp1 | 15 | 3 | 0.0% | 0.390 | 0.573 |
| Exp2 | 10 | 8 | 10.7% | 0.445 | 0.561 |
| **Exp3** ✅ | **5** | **20** | **24.9%** | **0.409** | **0.579** |

**Problemas detectados**:
- Clusters con skills basura: "Europa", "Oferta", "Piano", "Polanco"
- **Causa**: Fuzzy matching con `partial_ratio` (ya corregido en Exp #1 ESCO)

---

### Clustering #2: Pipeline B 300 Post-ESCO

**Dataset**: 234 skills únicas con ESCO mapping

| Experimento | min_cluster_size | Clusters | Noise % | Silhouette | Davies-Bouldin |
|-------------|-----------------|----------|---------|------------|----------------|
| **Exp1** ✅ | **5** | **10** | **6.0%** | 0.260 | 0.609 |
| Exp2 | 10 | 2 | 0.0% | 0.445 | 0.510 |
| Exp3 | 15 | 2 | 0.0% | 0.445 | 0.510 |

**Comparación Pipeline A vs B (Post-ESCO, mcs=5)**:

| Métrica | Pipeline A | Pipeline B | Diferencia |
|---------|-----------|-----------|------------|
| Skills únicas | 289 | 234 | -55 (-19%) |
| Clusters | 20 | 10 | -10 (-50%) |
| **Noise points** | 72 | **14** | **-58 (-81%)** 🎯 |
| **Noise %** | 24.9% | **6.0%** | **-18.9%** 🎯 |
| Silhouette | 0.409 | 0.260 | -0.149 |

**Conclusión**: Pipeline B genera MUCHO menos ruido (6% vs 25%) por mejor extracción inicial

---

### Clustering #3: Pipeline B 300 Pre-ESCO (Skills Emergentes)

**Dataset**: 1,780 skills únicas SIN ESCO mapping

| Experimento | mcs | Clusters | Noise % | Silhouette |
|-------------|-----|----------|---------|------------|
| **Exp1** | 5 | **117** | 24.3% | **0.515** |
| Exp2 | 10 | 53 | 22.6% | 0.439 |
| Exp3 | 15 | 28 | 38.5% | 0.370 |

**Hallazgo**: ESCO filtering elimina 87% de skills (1,780 → 234) pero mejora coherencia

---

### Clustering #4: Manual 300 Pre-ESCO (Ground Truth)

**Dataset**: 2,184 skills únicas anotadas manualmente

| Experimento | mcs | Clusters | Noise % | Silhouette |
|-------------|-----|----------|---------|------------|
| **Exp1** ✅ | 5 | **146** | 24.2% | **0.525** |
| Exp2 | 10 | 67 | 26.6% | 0.500 |
| Exp3 | 15 | 2 | 91.3% | 0.256 |

**Comparación Pre-ESCO**:

| Métrica | Pipeline A | Pipeline B | Manual | Mejor |
|---------|-----------|-----------|--------|-------|
| Skills únicas | N/A | 1,780 | 2,184 | Manual |
| Clusters | N/A | 117 | 146 | Manual |
| Silhouette | N/A | 0.515 | 0.525 | Manual |

---

### Clustering #5: ESCO 30k (Full Dataset)

**Dataset**: ~30,000 jobs históricos con ESCO skills

**Experimentos de parámetros UMAP+HDBSCAN**:

| Config | n_neighbors | min_cluster_size | Clusters | Noise % | Silhouette |
|--------|-------------|-----------------|----------|---------|------------|
| nn15_mcs15 ⭐ | 15 | 15 | 156 | 15.2% | **0.726** |
| nn15_mcs20 | 15 | 20 | 127 | 18.1% | 0.689 |
| nn20_mcs15 | 20 | 15 | 143 | 16.4% | 0.712 |

**Ganador**: nn15_mcs15 (mejor Silhouette=0.726)

**Top 5 Clusters por frecuencia**:
1. Python/Data Science (1,234 jobs)
2. Project Management (987 jobs)
3. Cloud/DevOps (856 jobs)
4. SQL/Databases (743 jobs)
5. JavaScript/Frontend (621 jobs)

---

## 🔧 EXPERIMENTOS PIPELINE A (NER+Regex)

**Documento**: `docs/PIPELINE_A_OPTIMIZATION_LOG.md`
**Objetivo**: Optimizar Pipeline A desde baseline (Garbage rate 75%) hasta producción (F1=72.53%)

### Experimento #0: Baseline (Pre-optimización)

**Estado inicial**:
- Precision: ~20%
- Recall: ~30%
- Garbage rate: 75%
- Fuzzy threshold: 0.85

**Problemas identificados**:
- NER extrae TODO sin filtros (100% garbage)
- Fuzzy threshold 0.85 permite matches absurdos ("Your" → "hacer pedidos de ropa")
- No hay stopwords

---

### Experimento #1: Stopwords Filter

**Cambios**: Agregadas 200+ stopwords (navegación, verbos, genéricos, países, empresas)

| Métrica | Antes | Después | Δ |
|---------|-------|---------|---|
| **Garbage rate** | 75% | **0%** | **-75pp** ✅ |
| Skills extraídas (Job #1) | 64 raw | 39 filtered | -39% |

**Hallazgo**: Stopwords eliminan basura, pero **fuzzy threshold 0.85 sigue generando matches absurdos**

---

### Experimento #2: Fuzzy Threshold 0.85 → 0.92

**Cambios**:
- Threshold general: 0.92
- Threshold para strings ≤4 chars: 0.95

| Métrica | Threshold 0.85 | Threshold 0.92 | Δ |
|---------|---------------|----------------|---|
| Matches absurdos | CRÍTICO | Parcialmente mejorado | ~70% reducidos |

**Problemas residuales**:
- ❌ "REST" → "restaurar dentaduras" (threshold 0.95 NO suficiente)
- ❌ "CI" → "Cisco Webex"
- ❌ "Oferta" → "ofertas de empleo"

**Decisión**: Threshold 0.92 ayuda pero NO es suficiente (ver Experimento ESCO Matcher #1)

---

### Experimento #3: Technical Generic Stopwords

**Cambios**: Agregados 60+ términos genéricos técnicos ("data", "cloud", "BI", "APIs")

| Métrica | Exp #2 | Exp #3 | Δ |
|---------|--------|--------|---|
| **Recall** | 59% | **50.5%** | **-8.5pp** ❌ |

**Resultado INESPERADO**: Recall BAJÓ porque stopwords eran demasiado agresivos

---

### Experimento #4: Revertir Stopwords Agresivos

**Cambios**: Removidos "cloud", "data", "bi", "apis" de stopwords

| Métrica | Exp #3 | Exp #4 | Δ |
|---------|--------|--------|---|
| **Recall** | 50.5% | **56.97%** | **+6.47pp** ✅ |

**Conclusión**: Balance crítico entre filtrar basura vs. eliminar skills válidas

---

### Experimento #5: EntityRuler + 666 Patrones ESCO

**Cambios**: Agregados 666 patrones de skills técnicas comunes a spaCy EntityRuler

| Métrica | Exp #4 | Exp #5 | Δ |
|---------|--------|--------|---|
| **Recall** | 56.97% | **64.43%** | **+7.46pp** ✅ |
| **Regex Recall** | 40.16% | **81.97%** | **+41.81pp** 🔥 |
| **NER Recall** | 22.13% | 2.46% | -19.67pp (esperado) |

**Hallazgo CLAVE**: EntityRuler + Regex patterns son MUY efectivos, NER es ruidoso

---

### Resumen Progreso Pipeline A (Exp #0 → #5)

| Métrica | Exp #0 (Baseline) | Exp #5 (Final) | Δ Total |
|---------|-------------------|----------------|---------|
| **Garbage Rate** | 75% | **0%** | **-75pp** ✅ |
| **Recall** | ~30% | **64.43%** | **+34pp** ✅ |
| **Precision** | ~20% | ~45% | +25pp |
| **F1 Post-ESCO** | ~35% | **72.53%** | **+37pp** ✅ |

**Mejoras implementadas** (17 total):
1. Stopwords NER (200+ palabras)
2. Fuzzy threshold 0.85 → 0.92
3. EntityRuler + 666 patrones ESCO
4. Patrones regex contextualizados
5. Normalización LATAM
6. Technical generic stopwords (60+)
7. Revertir stopwords agresivos

---

## 📊 EXPERIMENTOS PIPELINE A1 (TF-IDF)

**Documento**: `docs/PIPELINE_A1_IMPLEMENTATION_LOG.md`
**Objetivo**: Baseline estadístico clásico para comparar contra NER y LLM

### Iteración #1: Baseline TF-IDF

**Configuración**:
```python
TfidfVectorizer(
    ngram_range=(1, 3),
    max_df=0.5, min_df=2,
    max_features=10000
)
confidence_threshold = 0.1
```

| Métrica | Valor |
|---------|-------|
| F1 Raw | **5.2%** |
| F1 Post-ESCO | **33.33%** |
| Precision Raw | 6.66% |
| Recall Raw | 4.27% |
| ESCO Coverage | 5.67% |
| Skills Extracted | 1,306 |

**Problemas**: RUIDO MASIVO ("000 Confidencial", "220 Talentosos", "2Innovate")

---

### Iteración #2: Noise Filtering

**Cambios**:
- max_df: 0.5 → 0.3
- min_df: 2 → 3
- max_features: 10000 → 5000
- threshold: 0.1 → 0.15
- Stopwords de dominio + NOISE_PATTERNS

| Métrica | Iter #1 | Iter #2 | Δ |
|---------|---------|---------|---|
| F1 Raw | 5.2% | **6.27%** | +1.07pp |
| F1 Post-ESCO | 33.33% | **36.43%** | +3.1pp |
| Precision Raw | 6.66% | **11.13%** | **+67%** |
| ESCO Coverage | 5.67% | **10.38%** | **+84%** |
| Skills Extracted | 1,306 | **800** | -39% ruido |

---

### Iteración #3: Priorizing Recall

**Cambios**: threshold 0.15 → 0.12, max_df 0.3 → 0.35

| Métrica | Iter #2 | Iter #3 | Δ |
|---------|---------|---------|---|
| F1 Raw | 6.27% | **7.68%** | +1.41pp |
| F1 Post-ESCO | 36.43% | **43.24%** | **+6.81pp** 🎯 |

---

### Iteración #4: Noun Phrase Chunking + TF-IDF Ranking

**Cambios**: Usar spaCy noun_chunks para boundaries correctos

| Métrica | Iter #3 | Iter #4 (Final) | Δ |
|---------|---------|-----------------|---|
| F1 Raw | 7.68% | **11.69%** | **+52%** |
| F1 Post-ESCO | 43.24% | **48.00%** | +4.76pp |
| Precision Raw | 7.46% | 8.75% | +1.29pp |

**Conclusión Final**:
- ✅ **Objetivo alcanzado**: F1 Post-ESCO = 48% (meta: ≥45%)
- ✅ **Baseline defendible** contra crítica "why not use classical methods?"
- ❌ **Inferior a Pipeline A (NER+Regex)**: 48% vs 72.53%
- ❌ **Muy inferior a Pipeline B (Gemma)**: 48% vs 84.26%

---

## 🔍 EXPERIMENTOS FAISS/EMBEDDINGS

**Documento**: `docs/FAISS_ANALYSIS_AND_RECOMMENDATION.md`
**Fecha**: 2025-01-23
**Motivación**: FAISS Layer 3 producía 0 matches con threshold 0.87

### Experimento #1: Threshold Testing (0.80 → 0.90)

| Threshold | Semantic Matches | Quality |
|-----------|-----------------|---------|
| 0.87 (original) | 0 | ✅ No false positives |
| 0.85 | 1 | ⚠️ 1 absurd match |
| **0.82** | 6 | ❌ **6 absurd matches** |

**Matches absurdos a threshold 0.82**:
- "machine learning" → "planificar" (0.831)
- "data infrastructure" → "planificar" (0.851)
- "DevTools" → "tallar materiales" (0.849)
- "remote work" → "inglés" (0.829)

---

### Experimento #2: Individual Skill Testing (E5 embeddings)

| Skill | Top FAISS Match | Score | Correct? |
|-------|----------------|-------|----------|
| Python | Python | 0.8452 | ✅ (pero < 0.87!) |
| **Docker** | **Facebook** | 0.8250 | ❌ ABSURDO |
| **React** | **neoplasia** | 0.8284 | ❌ ABSURDO |
| Scikit-learn | Scikit-learn | 0.8432 | ✅ (pero < 0.87!) |
| **FastAPI** | **inglés** | 0.8283 | ❌ ABSURDO |
| PostgreSQL | SQL | 0.8490 | ⚠️ Relacionado |
| **TensorFlow** | **inglés** | 0.8407 | ❌ ABSURDO |

**Hallazgo CRÍTICO**: Incluso matches EXACTOS tienen score < 0.87

---

### Experimento #3: E5 Prefixes ("query:", "passage:")

**Hipótesis**: E5 recomienda usar prefixes para queries vs passages

| Config | Python → Python Score | Efecto |
|--------|----------------------|--------|
| Sin prefixes | 1.0 (exact) | ✅ |
| **Con prefixes** | **0.88** | ❌ **PEOR** |

**Conclusión**: Prefixes NO ayudan (diseñados para Q&A, no skill matching)

---

### Experimento #4: FAISS Index Regeneration

**Problema detectado**: FAISS index tenía 14,133 skills, DB tenía 14,215 (82 faltantes)

**Acción**: Regenerar embeddings + rebuild FAISS
**Resultado**: Index actualizado PERO matching sigue fallando

---

### Conclusión FAISS/Embeddings

**Decisión**: **DESACTIVAR Layer 3 (Semantic Matching)**

**Razones**:
1. ❌ E5 multilingual embeddings inadecuados para skills técnicas
2. ❌ Modelo entrenado en lenguaje natural, NO documentación técnica
3. ❌ Matches absurdos: "Docker" → "Facebook", "React" → "neoplasia"
4. ❌ Incluso matches exactos tienen score bajo (Python → Python = 0.8452 < 0.87)
5. ✅ Layer 1 (Exact) + Layer 2 (Fuzzy) son suficientes

**Alternativas evaluadas y descartadas**:
- ❌ Bajar threshold → Produce matches absurdos
- ❌ Agregar critical skills → No resuelve problema del modelo
- ❌ Usar prefixes E5 → Empeora scores
- ❌ Regenerar index → Index OK, modelo es el problema

---

## 📊 SELECCIÓN DE 300 GOLD STANDARD JOBS

**Script**: `scripts/select_gold_standard_jobs.py`
**Fecha de selección**: 2025-01-XX (ver logs)

### Metodología de Selección Estratificada

**4 Fases de selección**:

#### Fase 1: Detección Automática de Idioma
- Patrones regex para español (experiencia, años, requisitos, buscamos...)
- Patrones regex para inglés (experience, years, requirements, looking...)
- Clasificación: `es`, `en`, `mixed` (Spanglish)

#### Fase 2: Pre-filtrado STRICT
```sql
WHERE is_usable = TRUE
  AND (LENGTH(description) + LENGTH(requirements)) > 1000
  AND title ILIKE '%developer%|engineer%|desarrollador%...'
  -- EXCLUDE non-tech: manager, director, coordinator, BI, mechanical...
```

#### Fase 3: Scoring y Clasificación
**Quality Score (0-100)**:
- Longitud de descripción (0-20 pts)
- Sección de requisitos (10 pts)
- Título técnico (10 pts)
- Skills técnicas mencionadas (0-10 pts)
- Penalty por ruido HTML/JS (0-10 pts)

**Clasificación automática**:
- **Roles**: backend, fullstack, frontend, data_science, devops, mobile, qa, security, other
- **Seniority**: junior, mid, senior (por keywords)

#### Fase 4: Selección Estratificada (300 jobs)

**Distribución objetivo**:
| País | Idioma | Total | Backend | Fullstack | Frontend | Data | DevOps | Mobile | QA | Security |
|------|--------|-------|---------|-----------|----------|------|--------|--------|----|---------|
| CO | ES | 100 | 27 | 20 | 17 | 13 | 13 | 5 | 3 | 2 |
| MX | ES | 100 | 27 | 20 | 17 | 13 | 13 | 5 | 3 | 2 |
| AR | ES | 50 | 13 | 10 | 8 | 7 | 7 | 3 | 2 | 0 |
| CO | EN | 17 | 5 | 4 | 3 | 2 | 2 | 1 | 0 | 0 |
| MX | EN | 17 | 5 | 4 | 3 | 2 | 2 | 1 | 0 | 0 |
| AR | EN | 16 | 5 | 3 | 3 | 2 | 2 | 1 | 0 | 0 |
| **TOTAL** | | **300** | **82** | **61** | **51** | **39** | **39** | **16** | **8** | **4** |

**Prioridades jerárquicas**: Idioma > País > Rol > Quality Score

**Resultado final**: 300 jobs anotados manualmente (6,174 hard skills, 1,674 soft skills)

---

## 🎯 PRÓXIMOS PASOS: ANÁLISIS DE DATOS Y CLUSTERING

### Plan de Trabajo Pendiente

**Ver documento completo**: `docs/DATASET_ANALYSIS.md`

#### 1. Análisis Exploratorio de Datos (EDA) ⬜
- Distribución de ofertas por país, idioma, portal
- Distribución de Spanglish (jobs con ES+EN mezclado)
- Distribución de roles TI vs no-TI
- Evolución temporal de postings

#### 2. Análisis de Skills Emergentes ⬜
- Skills que NO mapean a ESCO (Pipeline A, B, Manual)
- Skills en O*NET pero NO en ESCO
- Skills únicas de cada pipeline
- Comparativa cobertura ESCO vs realidad del mercado

#### 3. Análisis Temporal ⬜
- Re-correr `scripts/temporal_clustering_analysis.py` sobre 31k jobs
- Heatmaps de evolución de clusters
- Skills en ascenso/descenso (growth rate >50%)
- Top 10 skills emergentes por trimestre

#### 4. Clustering Final ⬜
- Clusters de tecnologías en tendencia
- Análisis de clusters principales
- Documentación de insights

---

## 📚 REFERENCIAS

### Documentos Principales
- **Pipeline A Log**: `docs/PIPELINE_A_OPTIMIZATION_LOG.md`
- **Pipeline B Log**: `docs/PIPELINE_B_ITERACION_Y_PRUEBAS.md`
- **Clustering Log**: `docs/CLUSTERING_IMPLEMENTATION_LOG.md`
- **Evaluation System**: `docs/EVALUATION_SYSTEM.md`
- **Dataset Analysis**: `docs/DATASET_ANALYSIS.md` (EN PROGRESO)

### Scripts de Evaluación
- **3 Pipelines (actual)**: `/tmp/evaluate_three_pipelines_correct.py`
- **Evaluador oficial**: `scripts/evaluate_pipelines.py`
- **Comparador dual**: `src/evaluation/dual_comparator.py`
- **Gold Standard Selection**: `scripts/select_gold_standard_jobs.py`

### Logs de Ejecución
- **3 Pipelines**: `outputs/clustering/three_pipelines_evaluation_FIXED_INTERSECTION.log`
- **Pipeline A full**: `outputs/clustering/pipeline_a_full_dataset.log`
- **Clustering**: `outputs/clustering/clustering_*.log`

---

**Fin del documento** - Última actualización: 2025-11-07 23:15:00
