# Evaluación de Pipelines vs Gold Standard

**Fecha:** 2025-11-06 00:30:18
**Jobs evaluados:** 300
**Pipelines:** Pipeline A (NER+Regex) (hard), Pipeline B (gemma-3-4b-instruct) (hard)

---

## 1. Extracción Pura (Sin Mapeo ESCO)

| Pipeline | Precision | Recall | F1-Score | Support | Predicted |
|----------|-----------|--------|----------|---------|----------|
| Pipeline A (NER+Regex) (hard)  | 0.2057 | 0.2827 | 0.2381 | 1836 | 2523 |
| Pipeline B (gemma-3-4b-instruct) (hard) | 0.4873 | 0.4364 | 0.4605 | 1888 | 1691 |

**Ganador:** Pipeline B (gemma-3-4b-instruct) (hard) (F1=0.4605)

---

## 2. Post-Mapeo ESCO (Estandarización)

| Pipeline | Precision | Recall | F1-Score | Cobertura ESCO |
|----------|-----------|--------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | 0.6484 | 0.8137 | 0.7217 | 10.90% |
| Pipeline B (gemma-3-4b-instruct) (hard) | 0.8925 | 0.7981 | 0.8426 | 12.60% |

**Ganador:** Pipeline B (gemma-3-4b-instruct) (hard) (F1=0.8426)

---

## 3. Impacto del Mapeo a ESCO

| Pipeline | Δ F1 | Δ F1 (%) | Skills Perdidas |
|----------|------|----------|----------------|
| Pipeline A (NER+Regex) (hard)  | +0.4836 | +203.09% | 2248 |
| Pipeline B (gemma-3-4b-instruct) (hard) | +0.3822 | +83.00% | 1478 |

---

## 4. Skills Emergentes (No en ESCO)

**Total:** 3408

- .NET
- 12-Factor App Methodology
- 2+ Years Cloud
- 2+ years hands-on experience with Applicative Infrastructure troubleshooting of key life cycle management tools
- 3 Years Fullstack Development Experience Strong
- 3 Years Of Full-Stack Engineering Experience With Proficiency In
- 3D Rendering
- 3D object implementation
- 4 Years Backend Or
- 5 Years In Backend Engineering
- A Sharp Feedback Loop Into Engineering
- A Strong Engineering Background
- A key aspect of this position is staying ahead of technological advancements and contributing innovative ideas to enhance our tech stack and security practices
- A/B testing
- ABOUT
- ACE
- ACF
- ADA
- ADO
- AEM
- AI
- AI Agents
- AI Builder
- AI Coding Assistants (GitHub Copilot, ChatGPT
- AI Speech
- AI Tools: AI coding assistant
- AI agents
- AI coding assistant (Cursor, Copilot, etc
- AI tooling
- AI tools Open-source
