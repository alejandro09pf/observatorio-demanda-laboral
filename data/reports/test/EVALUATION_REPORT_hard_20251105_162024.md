# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 16:20:24
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex) (hard), Pipeline B (llama-3.2-3b-instruct-MOCK) (hard), Pipeline B (gemma-3-4b-instruct-MOCK) (hard)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex) (hard)  | 1.0000 | 0.8138 | 0.8973 | 1783 | 1451 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (hard) | 1.0000 | 0.8609 | 0.9253 | 1783 | 1535 |
| Pipeline B (gemma-3-4b-instruct-MOCK) (hard) | 1.0000 | 0.8474 | 0.9174 | 1783 | 1511 |

**Ganador:** Pipeline B (llama-3.2-3b-instruct-MOCK) (hard) (F1=0.9253)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | 1.0000 | 0.9118 | 0.9538 | 13.58% |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (hard) | 1.0000 | 0.9412 | 0.9697 | 13.36% |
| Pipeline B (gemma-3-4b-instruct-MOCK) (hard) | 1.0000 | 0.9363 | 0.9671 | 13.43% |

**Ganador:** Pipeline B (llama-3.2-3b-instruct-MOCK) (hard) (F1=0.9697)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | +0.0565 | +6.30% | 1254 |
| Pipeline B (llama-3.2-3b-instruct-MOCK) (hard) | +0.0444 | +4.80% | 1330 |
| Pipeline B (gemma-3-4b-instruct-MOCK) (hard) | +0.0497 | +5.41% | 1308 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 1547

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
