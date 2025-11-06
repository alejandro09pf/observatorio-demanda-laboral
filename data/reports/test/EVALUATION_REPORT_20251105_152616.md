# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 15:26:16
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex), Pipeline B (llama-3.2-3b-instruct-MOCK), Pipeline B (gemma-3-4b-instruct-MOCK)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex)         | 0.8571 | 0.7500 | 0.8000 |   96 |   84 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | 0.8966 | 0.8125 | 0.8525 |   96 |   87 |
| Pipeline B (gemma-3-4b-instruct-MOCK) | 0.9091 | 0.8333 | 0.8696 |   96 |   88 |

**Ganador:** Pipeline B (gemma-3-4b-instruct-MOCK) (F1=0.8696)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex)         | 0.6667 | 0.6452 | 0.6557 | 35.71% |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | 0.7333 | 0.7097 | 0.7213 | 34.48% |
| Pipeline B (gemma-3-4b-instruct-MOCK) | 0.7812 | 0.8065 | 0.7937 | 36.36% |

**Ganador:** Pipeline B (gemma-3-4b-instruct-MOCK) (F1=0.7937)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex)         | -0.1443 | -18.03% |  54 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | -0.1311 | -15.38% |  57 |
| Pipeline B (gemma-3-4b-instruct-MOCK) | -0.0759 | -8.73% |  56 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 67

- AWS
- Android
- Análisis
- Api Rest
- Aplicaciones de escritorio
- Aplicaciones web
- Aprendizaje continuo
- Arquitectura de software
- Atención al detalle
- Automatización
- Backend
- Bases de datos no relacionales
- Bases de datos relacionales
- Buenas prácticas
- Calidad de datos
- Colaboración
- Creatividad
- Curiosidad
- DBA
- Desarrollo de aplicaciones
- Desarrollo móvil
- Desarrollo móvil nativo
- Desarrollo web
- Dinamismo
- Estructuras de datos
- GCP
- Garantía de calidad
- Gestión de cargas de datos
- Gitflow
- Herramientas internas
