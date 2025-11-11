# Experimentos - Observatorio de Demanda Laboral

Esta carpeta contiene la documentación de experimentos realizados durante el desarrollo del sistema de extracción de skills.

---

## Pipeline A.2 - N-gram Matching contra ESCO

**Objetivo:** Explorar si N-gram matching exhaustivo contra la taxonomía ESCO puede competir con los pipelines basados en Regex y LLMs.

**Duración:** ~40 horas de desarrollo e investigación

**Resultado:** F1 20.41% (mejor versión) vs F1 79.15% (Regex) - El enfoque no es competitivo para producción.

### 📄 Documentos

#### 1. [PIPELINE_A2_NGRAMS_EXPERIMENT.md](./PIPELINE_A2_NGRAMS_EXPERIMENT.md)
**Experimento inicial (A2.0)**
- Descripción del enfoque naive
- Generación de 85,039 n-gramas desde ESCO
- Resultados: F1 6.68%
- Análisis de por qué falló

#### 2. [PIPELINE_A2_ALL_VERSIONS_ANALYSIS.md](./PIPELINE_A2_ALL_VERSIONS_ANALYSIS.md)
**Análisis de 4 versiones (A2.0 - A2.3)**
- A2.0: Original naive
- A2.1: Filtrado por longitud y frecuencia
- A2.2: Solo tech skills (mejor: F1 9.73%)
- A2.3: Eliminación de n-gramas genéricos
- Comparación detallada y lecciones aprendidas

#### 3. [PIPELINE_A2_FINAL_REPORT.md](./PIPELINE_A2_FINAL_REPORT.md) ⭐
**Reporte comprehensivo final**
- Todas las 6 versiones (A2.0 → A2.IMPROVED)
- Corrección del enfoque conceptual (A2.FIXED)
- Implementación de mejoras (alias, custom skills, substring matching)
- Mejor resultado: F1 20.41%
- Análisis de limitaciones fundamentales
- Recomendaciones para la tesis

---

## Resumen de Resultados

| Versión | F1 | Enfoque |
|---------|-----|---------|
| Pipeline A (Regex) | **79.15%** | 548 patrones curados ✅ |
| Pipeline B (LLM) | **84.26%** | Gemma 3 4B ✅ |
| **A2.IMPROVED** | **20.41%** | N-grams + mejoras 🏆 |
| A2.FIXED | 16.99% | Enfoque correcto |
| A2.2 | 9.73% | Solo tech skills |
| A2.0 | 6.68% | Naive original |

---

## Lecciones Principales

1. **100 patrones curados > 85,000 n-gramas automáticos**
   - La curación manual importa más que la cobertura exhaustiva

2. **ESCO no fue diseñada para extracción directa**
   - Taxonomía semántica para clasificación ≠ diccionario para matching

3. **El contexto semántico es crítico**
   - Los LLMs superan enfoques lexicográficos porque entienden contexto

4. **Documentar fallos es valioso**
   - Este experimento justifica empíricamente por qué Pipeline A y B son superiores

---

## Archivos Relacionados

### Scripts
```
scripts/experiments/
├── generate_ngram_dictionary.py
├── generate_filtered_ngram_dictionaries.py
├── pipeline_a2_ngram_extractor.py
├── pipeline_a2_FIXED.py
├── pipeline_a2_IMPROVED.py
├── evaluate_pipeline_a2.py
├── evaluate_all_versions.py
├── evaluate_pipeline_a2_FIXED.py
└── evaluate_pipeline_a2_IMPROVED.py
```

### Datos Generados
```
data/processed/
├── ngram_skill_dictionary.json          (85,039 n-gramas)
├── ngram_dict_v21.json                  (55,589 n-gramas)
├── ngram_dict_v22.json                  (24,134 n-gramas)
└── ngram_dict_v23.json                  (84,792 n-gramas)
```

### Resultados
```
outputs/evaluation/
├── pipeline_a2_results.json
├── pipeline_a2_all_versions_results.json
├── pipeline_a2_FIXED_results.json
└── pipeline_a2_IMPROVED_results.json
```

---

## Valor para la Tesis

Este experimento **fortalece** la tesis al:

✅ Demostrar rigor metodológico (6 iteraciones)
✅ Validar empíricamente las limitaciones de taxonomías oficiales
✅ Justificar la elección de Pipeline A y B
✅ Documentar exhaustivamente un camino que NO funciona (igualmente valioso en investigación)

---

**Última actualización:** 2025-11-10
