# Gold Standard Dataset - 300 Job Ads

Este directorio contiene el **gold standard** de 300 ofertas laborales anotadas manualmente para evaluación del pipeline de extracción.

## Estructura

```
data/gold_standard/
├── selected_jobs.json          # 300 jobs seleccionados (sin anotar)
├── annotations/
│   ├── CO_001.json  ... CO_100.json  # 100 jobs Colombia
│   ├── MX_001.json  ... MX_100.json  # 100 jobs México
│   ├── AR_001.json  ... AR_100.json  # 100 jobs Argentina
├── completed_annotations.json  # Todas las anotaciones completadas
└── validation_results/         # Resultados de validación vs pipeline
```

## Distribución (Según Diseño de Tesis)

**Total: 300 jobs**
- **100 Colombia** (CO)
- **100 México** (MX)
- **100 Argentina** (AR)

**Por tipo de posición:**
- **50% Desarrollo Software** (150 jobs): Frontend, Backend, Full-stack, Mobile
- **25% Ciencia de Datos** (75 jobs): Data Scientist, ML Engineer, Data Analyst
- **25% DevOps/Infraestructura** (75 jobs): DevOps, Cloud Engineer, SRE, Platform Engineer

## Formato de Anotación

Cada archivo JSON contiene:

```json
{
  "job_id": "uuid-from-database",
  "metadata": {
    "country": "CO|MX|AR",
    "portal": "nombre_portal",
    "title": "título del job",
    "job_type": "dev_software|data_science|devops_infra",
    "seniority": "junior|mid|senior",
    "annotated_by": "nombre_anotador",
    "annotation_date": "2025-11-03",
    "annotation_time_minutes": 15
  },
  "ground_truth_skills": [
    {
      "skill_text": "Python",
      "skill_type": "hard",
      "esco_uri": "esco:S1.2.3.4",
      "esco_label": "Python (programming language)",
      "confidence": "certain|probable|uncertain",
      "extraction_difficulty": "explicit|implicit|inferrable",
      "source_evidence": "texto exacto donde aparece"
    }
  ],
  "expected_metrics": {
    "total_skills": 25,
    "hard_skills": 20,
    "soft_skills": 5,
    "esco_matchable": 15,
    "emergent_skills": 10
  },
  "quality_flags": {
    "is_tech_job": true,
    "has_clear_requirements": true,
    "language_quality": "high|medium|low",
    "has_salary_info": false
  },
  "notes": "Comentarios del anotador sobre casos especiales"
}
```

## Proceso de Anotación

### 1. Selección (Automática)
```bash
python scripts/select_gold_standard_jobs.py
# Output: data/gold_standard/selected_jobs.json
```

### 2. Anotación (Manual)
```bash
python scripts/annotate_gold_standard.py --job-id <uuid>
# Interface CLI para anotar job por job
# Guarda en: data/gold_standard/annotations/{COUNTRY}_{NUM}.json
```

### 3. Validación (Automática)
```bash
python scripts/validate_pipeline_vs_gold_standard.py
# Compara pipeline output vs ground truth
# Output: data/gold_standard/validation_results/
```

## Criterios de Anotación

### Skills a Incluir:
✅ Lenguajes de programación
✅ Frameworks y librerías
✅ Bases de datos
✅ Cloud platforms y herramientas
✅ Metodologías (si se requiere certificación/experiencia)
✅ Soft skills SOLO si son críticas (ej: "liderazgo de equipo técnico")

### Skills a Excluir:
❌ Soft skills genéricas ("trabajo en equipo", "comunicación")
❌ Educación básica ("título universitario", "inglés intermedio")
❌ Legal disclaimers
❌ Descripciones de empresa
❌ Beneficios

### Casos Especiales:
- **Skills implícitas**: Si dice "Desarrollador Full-stack" → inferir Frontend + Backend
- **Variantes**: Normalizar ("React.js" → "React", "PostgreSQL" → "PostgreSQL")
- **Versiones**: Incluir si se especifica ("Python 3.x" → marcar versión)
- **Acrónimos**: Expandir en notes si hay ambigüedad ("ML" → Machine Learning)

## Métricas de Calidad

Cada anotación debe incluir:
- **Tiempo de anotación**: Para estimar costo de ground truth creation
- **Confidence level**: Para cada skill identificada
- **Extraction difficulty**: Explicit vs implicit vs inferrable

## Validación Inter-Anotador

Si hay múltiples anotadores:
- Calcular Cohen's Kappa para acuerdo inter-anotador
- Resolver discrepancias por consenso
- Documentar casos edge en `notes`

## Uso del Gold Standard

Este dataset se usa para:
1. **Evaluar Pipeline A** (NER + Regex + ESCO)
2. **Evaluar Pipeline B** (Gemma 4B vs Llama 3B)
3. **Calcular métricas** (Precision, Recall, F1)
4. **Identificar failure modes** del pipeline
5. **Optimizar thresholds** de matching
6. **Reportar en tesis** (Capítulo 7: Resultados)
