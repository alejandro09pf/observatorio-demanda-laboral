# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 18:08:27
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex) (hard)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex) (hard)  | 0.0000 | 0.0000 | 0.0000 |    0 |    0 |

**Ganador:** Pipeline A (NER+Regex) (hard) (F1=0.0000)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | 0.0000 | 0.0000 | 0.0000 | 0.00% |

**Ganador:** Pipeline A (NER+Regex) (hard) (F1=0.0000)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | +0.0000 | +0.00% |   0 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 0

