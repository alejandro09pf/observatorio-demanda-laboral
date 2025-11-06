# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 16:22:06
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex) (soft), Pipeline B (llama-3.2-3b-instruct-MOCK) (soft), Pipeline B (gemma-3-4b-instruct-MOCK) (soft)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex) (soft)  | 1.0000 | 0.8448 | 0.9159 |  290 |  245 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (soft) | 1.0000 | 0.8586 | 0.9239 |  290 |  249 |
| Pipeline B (gemma-3-4b-instruct-MOCK) (soft) | 1.0000 | 0.8690 | 0.9299 |  290 |  252 |

**Ganador:** Pipeline B (gemma-3-4b-instruct-MOCK) (soft) (F1=0.9299)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex) (soft)  | 1.0000 | 1.0000 | 1.0000 | 4.49% |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (soft) | 1.0000 | 1.0000 | 1.0000 | 4.42% |
| Pipeline B (gemma-3-4b-instruct-MOCK) (soft) | 1.0000 | 0.8182 | 0.9000 | 3.57% |

**Ganador:** Pipeline A (NER+Regex) (soft) (F1=1.0000)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex) (soft)  | +0.0841 | +9.18% | 234 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (soft) | +0.0761 | +8.23% | 238 |
| Pipeline B (gemma-3-4b-instruct-MOCK) (soft) | -0.0299 | -3.21% | 243 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 276

- Abstracción
- Actualización continua
- Adaptabilidad
- Adaptación
- Adaptación al cambio
- Agilidad
- Ambición
- Ambigüedad
- Análisis
- Análisis de causa raíz
- Análisis de procesos
- Análisis de requerimientos
- Apertura a la crítica
- Aprendizaje
- Aprendizaje continuo
- Aprendizaje rápido
- Argumentación
- Aseguramiento de calidad
- Asistencia técnica
- Atención a usuarios
- Atención al cliente
- Atención al detalle
- Auditoría
- Autoconocimiento
- Autodidacta
- Autogestión
- Automatización
- Automotivación
- Autonomía
- Buenas prácticas
