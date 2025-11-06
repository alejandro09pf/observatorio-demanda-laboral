# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-05 17:15:03
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex) (hard)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex) (hard)  | 1.0000 | 0.8138 | 0.8973 | 1783 | 1451 |

**Ganador:** Pipeline A (NER+Regex) (hard) (F1=0.8973)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | 1.0000 | 0.9118 | 0.9538 | 13.58% |

**Ganador:** Pipeline A (NER+Regex) (hard) (F1=0.9538)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | +0.0565 | +6.30% | 1254 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 1254

- .NET
- 3D rendering
- 3ds Max
- ACF
- AI
- AI Agents
- AI Builder
- AI Skills
- AI coding assistants
- AL
- ALM
- API
- API Gateway
- API Keys
- API Management
- API RESTful
- API de Looker
- API testing
- APIs
- APIs REST
- ASP
- ASP Core
- ATS
- AWR
- AWS
- AWS API Gateway
- AWS Certified Solutions Architect
- AWS CloudFormation
- AWS Glue
- Ab-Initio
