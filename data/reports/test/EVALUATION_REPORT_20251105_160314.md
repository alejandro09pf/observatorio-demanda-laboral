# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 16:03:14
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex), Pipeline B (llama-3.2-3b-instruct-MOCK), Pipeline B (gemma-3-4b-instruct-MOCK)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex)         | 1.0000 | 0.8194 | 0.9008 | 2038 | 1670 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | 1.0000 | 0.8621 | 0.9260 | 2038 | 1757 |
| Pipeline B (gemma-3-4b-instruct-MOCK) | 1.0000 | 0.8499 | 0.9188 | 2038 | 1732 |

**Ganador:** Pipeline B (llama-3.2-3b-instruct-MOCK) (F1=0.9260)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex)         | 1.0000 | 0.9198 | 0.9582 | 12.34% |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | 1.0000 | 0.9434 | 0.9709 | 12.18% |
| Pipeline B (gemma-3-4b-instruct-MOCK) | 1.0000 | 0.9340 | 0.9659 | 12.12% |

**Ganador:** Pipeline B (llama-3.2-3b-instruct-MOCK) (F1=0.9709)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex)         | +0.0575 | +6.38% | 1464 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) | +0.0449 | +4.85% | 1543 |
| Pipeline B (gemma-3-4b-instruct-MOCK) | +0.0470 | +5.12% | 1522 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 1790

- .NET
- 3D rendering
- 3ds Max
- ACF
- AI
- AI Agents
- AI Builder
- AI Skills
- AI Speech
- AI coding assistants
- AI training
- AKS
- AL
- ALDON
- ALM
- AML
- API
- API Context
- API Gateway
- API Keys
- API Management
- API RESTful
- API de Looker
- API testing
- APIs
- APIs REST
- APQP
- ARM templates
- ASP
- ASP Core
