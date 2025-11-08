# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-06 19:40:35
**Jobs evaluados:** 300
**Pipelines:** Pipeline A.1 (N-gram + TF-IDF)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A.1 (N-gram + TF-IDF) | 0.0875 | 0.1762 | 0.1169 | 2038 | 4103 |

**Ganador:** Pipeline A.1 (N-gram + TF-IDF) (F1=0.1169)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A.1 (N-gram + TF-IDF) | 0.4789 | 0.4811 | 0.4800 | 5.70% |

**Ganador:** Pipeline A.1 (N-gram + TF-IDF) (F1=0.4800)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A.1 (N-gram + TF-IDF) | +0.3631 | +310.54% | 3869 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 3869

- A.M
- ABAP Junior
- ADN
- AI
- AI Builder – Uso
- AI Engineers
- AI Skills
- AI Speech
- AI Studio
- AI Tools
- AI agents
- AI agents is
- AI and
- AI and NLP using LLMs
- AI and automation to streamline
- AI assistants that empower
- AI companies
- AI ecosystem architecture
- AI engineers
- AI models
- AI models PLEASE NOTE
- AI models will
- AI optimization Benefits We are
- AI outputs meet
- AI project
- AI researchers
- AI systems for
- AI to address
- AI to transform underwriting
- AI tooling
