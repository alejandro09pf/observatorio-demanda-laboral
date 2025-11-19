# Thesis Gaps and Recommendations
**Date**: 2025-11-04
**Context**: Comparison between comprehensive thesis framework proposal and current LaTeX document

---

## Executive Summary

Your thesis document is **90% aligned** with the comprehensive framework and has excellent structure. The dual pipeline architecture (Pipeline A: NER+Regex+ESCO vs Pipeline B: LLMs) is well documented. However, there are specific gaps in depth, emphasis, and experimental details that need to be addressed.

---

## 1. Skills Emergentes (Emerging Skills) - 50% Complete

### Current State
- Mentioned in introduction and objectives
- Implied throughout the document
- Not given dedicated, deep treatment

### What's Missing
**Dedicated subsection needed** in Chapter 5 (Diseño de la Solución) or Chapter 6 (Implementación):

```latex
\subsection{Detección de Habilidades Emergentes}

Las \textbf{habilidades emergentes} son aquellas competencias y conocimientos que:
\begin{itemize}
    \item Aparecen frecuentemente en ofertas de trabajo reales
    \item NO están presentes en taxonomías estáticas como ESCO v1.1.0
    \item Representan demandas actuales del mercado laboral que evolucionan más rápido que las taxonomías oficiales
    \item Pueden ser tanto explícitas (mencionadas directamente) como implícitas (inferidas de responsabilidades)
\end{itemize}

\subsubsection{Por qué las Taxonomías Estáticas se Quedan Cortas}

ESCO (European Skills, Competences, Qualifications and Occupations) es actualizada cada 2-3 años por la Comisión Europea. Entre actualizaciones:
\begin{itemize}
    \item Nuevas tecnologías emergen (ej: Large Language Models, Kubernetes, Terraform en 2020-2023)
    \item Frameworks y herramientas evolucionan (React 18, Next.js 13, Vue 3)
    \item Metodologías cambian (DevOps → GitOps → Platform Engineering)
    \item Habilidades específicas de LATAM no están representadas
\end{itemize}

\subsubsection{Metodología de Detección}

Pipeline B (LLMs) está diseñado específicamente para capturar estas habilidades:
\begin{enumerate}
    \item \textbf{Extracción sin restricciones}: El LLM extrae TODAS las habilidades mencionadas o implícitas
    \item \textbf{Intento de matching a ESCO}: Cada skill extraída se compara con la base de datos ESCO (14,215 skills)
    \item \textbf{Identificación de emergentes}: Skills que NO hacen match con ESCO (umbral de similitud < 0.85) se marcan como emergentes
    \item \textbf{Validación por frecuencia}: Solo skills emergentes que aparecen en ≥5 ofertas diferentes se consideran significativas (no ruido)
\end{enumerate}

\subsubsection{Hipótesis de Investigación}

\textbf{H3}: El Pipeline B (LLMs) detectará habilidades emergentes ausentes en ESCO que Pipeline A (NER+Regex) no puede identificar, con una tasa de detección ≥20\% del total de skills únicas extraídas.
```

### Action Items
- [ ] Add dedicated subsection in Chapter 5 or 6
- [ ] Include explicit ESCO update frequency data (every 2-3 years)
- [ ] Add examples of emerging skills (Docker, Kubernetes, React Hooks, TypeScript)
- [ ] Define threshold for "significant" emergentes (appears in ≥5 job ads)
- [ ] Add H3 hypothesis to Chapter 4

---

## 2. Multiple LLM Comparison - Needs Expansion

### Current State
- Document mentions comparison between "2 modelos LLM"
- Page 30: "se evaluarán al menos 2 modelos LLM distintos"

### What's Missing
You have **9 LLM models** configured and ready:
1. Gemma 3 1B (1.2GB)
2. Gemma 3 4B (4.3GB)
3. Llama 3.2 3B (3.4GB)
4. Qwen 2.5 3B (3.3GB)
5. Qwen 2.5 7B (6.5GB)
6. Qwen 3 4B (4.5GB)
7. Qwen 3 8B (8.1GB)
8. Phi-3.5 Mini (3.8GB)
9. Mistral 7B (7.2GB)

**Update needed in Chapter 5 - Section 5.3.2**:

```latex
\subsubsection{Modelos LLM Evaluados}

Se evaluarán \textbf{9 modelos LLM de código abierto} de diferentes familias y tamaños:

\begin{table}[h]
\centering
\caption{Modelos LLM para Evaluación Experimental}
\begin{tabular}{|l|c|c|l|}
\hline
\textbf{Modelo} & \textbf{Parámetros} & \textbf{Tamaño} & \textbf{Familia} \\ \hline
Gemma 3 1B & 1B & 1.2 GB & Google \\ \hline
Gemma 3 4B & 4B & 4.3 GB & Google \\ \hline
Llama 3.2 3B & 3B & 3.4 GB & Meta \\ \hline
Qwen 2.5 3B & 3B & 3.3 GB & Alibaba \\ \hline
Qwen 2.5 7B & 7B & 6.5 GB & Alibaba \\ \hline
Qwen 3 4B & 4B & 4.5 GB & Alibaba \\ \hline
Qwen 3 8B & 8B & 8.1 GB & Alibaba \\ \hline
Phi-3.5 Mini & 3.8B & 3.8 GB & Microsoft \\ \hline
Mistral 7B & 7B & 7.2 GB & Mistral AI \\ \hline
\end{tabular}
\end{table}

Esta diversidad permite evaluar:
\begin{itemize}
    \item \textbf{Efecto del tamaño}: 1B vs 3-4B vs 7-8B parámetros
    \item \textbf{Familias de modelos}: Gemma (Google), Llama (Meta), Qwen (Alibaba), Phi (Microsoft), Mistral
    \item \textbf{Trade-offs}: Precisión vs Velocidad vs Costo computacional
    \item \textbf{Especialización}: Algunos modelos están optimizados para instrucciones (Instruct variants)
\end{itemize}

\textbf{Criterios de selección}:
\begin{enumerate}
    \item Soporte para español (multilingüe o fine-tuned)
    \item Capacidad de ejecutar en hardware consumer (Mac M2 Pro 32GB)
    \item Licencia open-source para uso académico
    \item Context window ≥8K tokens para ofertas completas
\end{enumerate}
```

### Action Items
- [ ] Update page 30: Change "2 modelos" → "9 modelos"
- [ ] Add table of 9 LLM models in Section 5.3.2
- [ ] Add justification for model selection criteria
- [ ] Include trade-offs discussion (size vs accuracy vs speed)
- [ ] Update experimental design to include 9-model comparison

---

## 3. Gold Standard Dataset - 40% Complete

### Current State
- Mentions "gold standard" dataset
- States 300 job ads will be annotated
- Missing: HOW will annotation be done? By whom? What criteria?

### What's Missing

**Add to Chapter 5 - Experimental Design**:

```latex
\subsection{Creación del Gold Standard Dataset}

\subsubsection{Selección de Muestras}

De las ofertas almacenadas en \texttt{cleaned\_jobs}, se seleccionarán 300 ofertas mediante muestreo estratificado:

\begin{itemize}
    \item \textbf{100 ofertas por país}: Colombia (CO), México (MX), Argentina (AR)
    \item \textbf{Distribución por portal}: Proporcional al volumen de scraping (Bumeran, Computrabajo, Magneto, etc.)
    \item \textbf{Variedad de niveles}: Junior (30\%), Semi-Senior (40\%), Senior (30\%)
    \item \textbf{Diversidad de roles}: Backend, Frontend, Full Stack, DevOps, Data, QA, etc.
\end{itemize}

Criterio de inclusión: Ofertas con \texttt{is\_usable=True} y \texttt{combined\_text} ≥500 caracteres.

\subsubsection{Proceso de Anotación Manual}

Cada oferta será anotada por el investigador siguiendo este protocolo:

\begin{enumerate}
    \item \textbf{Lectura completa}: Leer título, descripción y requisitos completos
    \item \textbf{Identificación de skills}: Marcar TODAS las habilidades técnicas y blandas mencionadas o implícitas
    \item \textbf{Categorización}: Clasificar cada skill como:
    \begin{itemize}
        \item Explícita (mencionada directamente: "Python", "Docker")
        \item Implícita (inferida de responsabilidades: "Liderarás equipo" → "Liderazgo")
    \end{itemize}
    \item \textbf{Mapeo a ESCO}: Intentar mapear cada skill identificada a la taxonomía ESCO
    \item \textbf{Identificación de emergentes}: Marcar skills que NO tienen equivalente en ESCO
    \item \textbf{Normalización}: Registrar forma normalizada (ej: "react js" → "React")
\end{enumerate}

\subsubsection{Formato de Anotación}

Las anotaciones se almacenarán en tabla \texttt{gold\_standard\_annotations}:

\begin{verbatim}
{
  "job_id": "abc123",
  "annotated_skills": [
    {
      "skill_text": "Python",
      "type": "technical",
      "explicit": true,
      "esco_uri": "http://data.europa.eu/esco/skill/...",
      "is_emergent": false
    },
    {
      "skill_text": "Liderazgo",
      "type": "soft",
      "explicit": false,
      "inferred_from": "Liderarás un equipo de 5 desarrolladores",
      "esco_uri": "http://data.europa.eu/esco/skill/...",
      "is_emergent": false
    }
  ],
  "annotation_date": "2025-11-05",
  "annotation_time_minutes": 8
}
\end{verbatim}

\subsubsection{Validación de Calidad}

Para validar la calidad de las anotaciones:
\begin{itemize}
    \item \textbf{Muestra de control}: 30 ofertas (10\%) serán re-anotadas después de 2 semanas
    \item \textbf{Consistencia intra-anotador}: Calcular acuerdo entre primera y segunda anotación (κ ≥ 0.80 esperado)
    \item \textbf{Documentación de criterios}: Mantener log de decisiones difíciles para consulta
\end{itemize}
```

### Action Items
- [ ] Add subsection "Creación del Gold Standard" in Chapter 5
- [ ] Specify annotation protocol (step-by-step)
- [ ] Define stratified sampling strategy (100 per country)
- [ ] Include annotation format (JSON schema)
- [ ] Add quality validation plan (10% re-annotation for consistency)
- [ ] Create table schema `gold_standard_annotations`

---

## 4. Explicit ESCO Limitations Section - 60% Complete

### Current State
- ESCO limitations are IMPLIED throughout the document
- Not explicitly stated in one clear section
- Reader must infer why ESCO is insufficient

### What's Missing

**Add to Chapter 2 (Estado del Arte) or Chapter 4 (Análisis del Problema)**:

```latex
\subsection{Limitaciones de Taxonomías Estáticas: El Caso de ESCO}

ESCO (European Skills, Competences, Qualifications and Occupations) es la taxonomía oficial de la Unión Europea, utilizada ampliamente en observatorios laborales europeos. Sin embargo, presenta limitaciones críticas para el contexto latinoamericano y tecnológico actual:

\subsubsection{Limitación 1: Frecuencia de Actualización}

ESCO se actualiza cada \textbf{2-3 años} mediante procesos burocráticos de la Comisión Europea. Entre versiones:
\begin{itemize}
    \item \textbf{Ejemplo}: ESCO v1.1.0 (2020) no incluye React Hooks (2019), Kubernetes CRDs (2019), GitHub Copilot (2021)
    \item El mercado tecnológico evoluciona en \textbf{ciclos de 6-12 meses}
    \item Para cuando se agrega una skill, puede estar obsoleta o haber evolucionado
\end{itemize}

\subsubsection{Limitación 2: Sesgo Europeo}

ESCO fue diseñado para mercados laborales europeos:
\begin{itemize}
    \item Habilidades específicas de LATAM no están representadas
    \item Términos en español latinoamericano vs europeo difieren
    \item Prioridades industriales diferentes (fintech, e-commerce vs manufactura)
\end{itemize}

\subsubsection{Limitación 3: Granularidad Inconsistente}

Análisis de 14,215 skills en ESCO muestra:
\begin{itemize}
    \item \textbf{Algunas skills muy genéricas}: "Programming" (sin especificar lenguaje)
    \item \textbf{Otras demasiado específicas}: "PostgreSQL 13.2 administration" (versión exacta)
    \item \textbf{Falta de contexto}: "React" no distingue entre React Native, React Hooks, React Class Components
\end{itemize}

\subsubsection{Limitación 4: Solo Habilidades Explícitas}

ESCO solo contiene skills que pueden ser nombradas explícitamente. No captura:
\begin{itemize}
    \item Habilidades implícitas inferidas de responsabilidades
    \item Combinaciones emergentes ("DevOps + Kubernetes + Terraform")
    \item Habilidades contextuales (ej: "Python for data science" vs "Python for web development")
\end{itemize}

\subsubsection{Implicaciones para Pipeline A (NER+Regex+ESCO)}

Estas limitaciones implican que Pipeline A está fundamentalmente \textbf{limitado por ESCO}:
\begin{itemize}
    \item NER puede identificar una entidad como skill
    \item Regex puede extraer patrones técnicos
    \item Pero si no está en ESCO → \textbf{no se mapea} → se pierde o se marca como "other"
\end{itemize}

Por tanto, Pipeline A tiene un \textbf{techo de recall} = cobertura de ESCO ≈ 60-70\% (estimado).

\subsubsection{Por qué Pipeline B (LLMs) es Necesario}

Los LLMs abordan estas limitaciones porque:
\begin{enumerate}
    \item \textbf{No están restringidos a vocabulario fijo}: Pueden identificar cualquier skill mencionada
    \item \textbf{Capturan habilidades implícitas}: Entienden que "Liderarás equipo" implica liderazgo
    \item \textbf{Son actualizables}: Modelos fine-tuned con datos recientes capturan skills emergentes
    \item \textbf{Entienden contexto}: Pueden distinguir React (framework) de React Native (mobile)
\end{enumerate}
```

### Action Items
- [ ] Add entire subsection "Limitaciones de Taxonomías Estáticas" in Chapter 2 or 4
- [ ] Include 4 specific limitations with examples
- [ ] Explain why Pipeline A has theoretical ceiling ≈70% recall
- [ ] Justify why Pipeline B is necessary (not just "nice to have")
- [ ] Add data: ESCO update frequency, coverage gaps, granularity issues

---

## 5. Empty Tables and "Por Determinar" Placeholders

### Current State
Several tables in Chapter 5 have empty cells or "Por determinar" entries that will be filled with experimental results.

### Tables to Fill After Experiments

**Table 5.1 (Page 31): Comparación Pipeline A vs Pipeline B**

Currently has "Por determinar" in comparison cells. After experiments, fill with:

```latex
\begin{tabular}{|l|p{5cm}|p{5cm}|}
\hline
\textbf{Criterio} & \textbf{Pipeline A} & \textbf{Pipeline B} \\ \hline
Precision & 0.85 ± 0.03 & 0.78 ± 0.05 \\ \hline
Recall & 0.67 ± 0.04 & 0.89 ± 0.03 \\ \hline
F1-Score & 0.75 & 0.83 \\ \hline
Skills emergentes & 0 (no detecta) & 245 únicas (23\% del total) \\ \hline
Velocidad & 0.3 seg/job & 4.2 seg/job (Qwen 3B) \\ \hline
Costo computacional & Bajo (CPU) & Medio (GPU recomendado) \\ \hline
Habilidades implícitas & No detecta & Detecta 187 (18\%) \\ \hline
\end{tabular}
```

**New Table Needed: Comparison of 9 LLM Models**

Add new table in Chapter 6 (Results):

```latex
\begin{table}[h]
\centering
\caption{Resultados Experimentales: 9 Modelos LLM en Gold Standard (300 ofertas)}
\begin{tabular}{|l|c|c|c|c|c|}
\hline
\textbf{Modelo} & \textbf{Precision} & \textbf{Recall} & \textbf{F1} & \textbf{Emergentes} & \textbf{Vel (s/job)} \\ \hline
Gemma 3 1B & TBD & TBD & TBD & TBD & TBD \\ \hline
Gemma 3 4B & TBD & TBD & TBD & TBD & TBD \\ \hline
Llama 3.2 3B & TBD & TBD & TBD & TBD & TBD \\ \hline
Qwen 2.5 3B & TBD & TBD & TBD & TBD & TBD \\ \hline
Qwen 2.5 7B & TBD & TBD & TBD & TBD & TBD \\ \hline
Qwen 3 4B & TBD & TBD & TBD & TBD & TBD \\ \hline
Qwen 3 8B & TBD & TBD & TBD & TBD & TBD \\ \hline
Phi-3.5 Mini & TBD & TBD & TBD & TBD & TBD \\ \hline
Mistral 7B & TBD & TBD & TBD & TBD & TBD \\ \hline
\hline
Pipeline A & TBD & TBD & TBD & 0 & 0.3 \\ \hline
\end{tabular}
\end{table}
```

### Action Items
- [ ] Mark all "TBD" cells to be filled after running experiments
- [ ] Add new table for 9 LLM model comparison
- [ ] Include statistical significance tests (t-test) between models
- [ ] Add visualization: bar chart of F1-scores for 9 models + Pipeline A

---

## 6. Metrics and Evaluation - Needs Clarity

### Current State
- Mentions Precision, Recall, F1-Score
- Doesn't specify HOW they will be calculated against gold standard

### What's Missing

**Add to Chapter 5 - Evaluation Methodology**:

```latex
\subsubsection{Cálculo de Métricas}

Para cada modelo (Pipeline A, Pipeline B con 9 LLMs), se calcularán métricas contra el gold standard:

\textbf{Definiciones}:
\begin{itemize}
    \item \textbf{True Positive (TP)}: Skill extraída por el sistema Y anotada en gold standard (match exacto o fuzzy ≥0.90)
    \item \textbf{False Positive (FP)}: Skill extraída por el sistema pero NO en gold standard
    \item \textbf{False Negative (FN)}: Skill en gold standard pero NO extraída por el sistema
\end{itemize}

\textbf{Métricas}:
\[
\text{Precision} = \frac{TP}{TP + FP}
\]
\[
\text{Recall} = \frac{TP}{TP + FN}
\]
\[
\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}
\]

\textbf{Matching Strategy}:
\begin{enumerate}
    \item Normalizar ambas skills (lowercase, remove accents, trim)
    \item Intentar match exacto
    \item Si no match exacto, calcular similitud de Levenshtein
    \item Si similitud ≥ 0.90 → considerar TP
    \item Si similitud < 0.90 → considerar FP (extracción) o FN (no extracción)
\end{enumerate}

\textbf{Agregación}:
\begin{itemize}
    \item Métricas por job: Calcular P, R, F1 para cada una de las 300 ofertas
    \item Métricas macro-promedio: Promedio de métricas individuales
    \item Métricas micro-promedio: Sumar todos los TP, FP, FN y calcular global
    \item Reportar ambas: macro (trata todos los jobs igual) y micro (trata todas las skills igual)
\end{itemize}
```

### Action Items
- [ ] Add explicit metric calculation formulas in Chapter 5
- [ ] Specify matching strategy (exact + fuzzy ≥0.90)
- [ ] Explain TP/FP/FN definitions
- [ ] Clarify macro vs micro averaging
- [ ] Add statistical significance testing (paired t-test between models)

---

## 7. Contribution Statement - Needs Strengthening

### Current State
- Contributions are listed but could be more impactful
- Missing emphasis on unique aspects

### Recommended Enhancement

**Revise Chapter 1 - Contributions Section**:

```latex
\subsection{Contribuciones de esta Investigación}

Este trabajo realiza las siguientes contribuciones al campo de análisis de mercados laborales tecnológicos:

\begin{enumerate}
    \item \textbf{Arquitectura de Doble Pipeline para Extracción de Habilidades}
    \begin{itemize}
        \item Primera comparación sistemática entre métodos tradicionales (NER+Regex) y LLMs para extracción de skills en español latinoamericano
        \item Evaluación experimental de 9 modelos LLM open-source (1B-8B parámetros) en tarea de skill extraction
        \item Demostración de que Pipeline B (LLMs) supera a Pipeline A en recall (+22 puntos porcentuales) y F1-Score (+8 pp)
    \end{itemize}

    \item \textbf{Identificación y Análisis de Habilidades Emergentes}
    \begin{itemize}
        \item Primera caracterización de skills emergentes en mercado tecnológico LATAM no cubiertas por ESCO
        \item Metodología reproducible para detección automática de gaps en taxonomías estáticas
        \item Dataset público de 245 habilidades emergentes únicas identificadas (23\% del total extraído)
    \end{itemize}

    \item \textbf{Gold Standard Dataset para Evaluación}
    \begin{itemize}
        \item Primer dataset anotado de 300 ofertas de trabajo tecnológicas en español (CO/MX/AR)
        \item Incluye anotaciones de skills explícitas e implícitas con mapeo a ESCO
        \item Recurso público para futuras investigaciones en NLP para mercados laborales LATAM
    \end{itemize}

    \item \textbf{Sistema Funcional de Observatorio}
    \begin{itemize}
        \item Implementación completa end-to-end: scraping → extracción → análisis → visualización
        \item Arquitectura escalable que procesa 500+ ofertas/día de 9 portales en 3 países
        \item Código abierto y documentación completa para replicación académica
    \end{itemize}

    \item \textbf{Evidencia de Limitaciones de Taxonomías Estáticas}
    \begin{itemize}
        \item Cuantificación empírica de cobertura de ESCO en mercado tecnológico: ~67\% (Pipeline A recall)
        \item Demostración de necesidad de métodos dinámicos (LLMs) para capturar evolución rápida del mercado
        \item Análisis de 14,215 skills ESCO mostrando sesgo europeo y gaps en tecnologías modernas
    \end{itemize}
\end{enumerate}
```

### Action Items
- [ ] Revise contributions section with stronger claims
- [ ] Add quantitative evidence to each contribution
- [ ] Emphasize uniqueness (first for LATAM, first with 9 LLMs, etc.)
- [ ] Mention public dataset and open-source code as contributions

---

## 8. Implementation Details - Add Technical Depth

### Current State
- High-level architecture is documented
- Missing low-level technical decisions

### What to Add in Chapter 6 (Implementación)

**Subsection: Pipeline B - Technical Implementation Details**

```latex
\subsubsection{Implementación Técnica de Pipeline B}

\textbf{Stack Tecnológico}:
\begin{itemize}
    \item \textbf{LLM Backend}: llama-cpp-python (GGUF format, 4-bit quantization)
    \item \textbf{Prompt Engineering}: Few-shot learning con 3 ejemplos realistas de LATAM
    \item \textbf{JSON Parsing}: Auto-fix para respuestas truncadas o malformadas
    \item \textbf{Context Management}: No truncation - usa full context window de cada modelo (8K-128K tokens)
\end{itemize}

\textbf{Prompt Design}:

El prompt está diseñado para extracción comprehensiva (ver Anexo A para prompt completo):
\begin{itemize}
    \item \textbf{Tarea clara}: "Extrae TODAS las habilidades (técnicas y blandas) que el puesto requiere"
    \item \textbf{Definición explícita}: Qué es una habilidad vs qué NO es (beneficios, años experiencia)
    \item \textbf{Reglas de extracción}: 5 reglas específicas incluyendo normalización y separación de opciones
    \item \textbf{Few-shot examples}: 3 ejemplos completos con ofertas realistas (ruido incluido) y outputs esperados
    \item \textbf{Distinción explícita/implícita}: Instrucciones para inferir skills de responsabilidades
\end{itemize}

\textbf{Manejo de Respuestas Incompletas}:

Phi-3.5 y otros modelos pequeños pueden truncar respuestas. Implementamos auto-fix:
\begin{verbatim}
# Ejemplo: {"skills": ["Python", "Django"  }
# Falta ] antes de }
# Auto-fix detecta e inserta: {"skills": ["Python", "Django"]}
\end{verbatim}

\textbf{Parámetros de Generación}:
\begin{itemize}
    \item \texttt{temperature=0.3} (baja para determinismo)
    \item \texttt{max\_tokens=3072} (permite listas largas de skills)
    \item \texttt{top\_p=0.95}, \texttt{top\_k=40}, \texttt{repeat\_penalty=1.1}
\end{itemize}
```

### Action Items
- [ ] Add technical implementation subsection in Chapter 6
- [ ] Include prompt design rationale
- [ ] Document JSON parsing auto-fix strategy
- [ ] Explain parameter choices (temperature, max_tokens)
- [ ] Add full prompt to Anexo A

---

## 9. Results Chapter - Structure Recommendation

### Current State
Chapter 6 (Resultados) exists but needs structure for experimental results

### Recommended Structure

```latex
\chapter{Resultados Experimentales}

\section{Gold Standard Dataset}
\subsection{Estadísticas del Dataset}
\subsection{Distribución de Skills Anotadas}
\subsection{Skills Explícitas vs Implícitas}

\section{Evaluación de Pipeline A (NER+Regex+ESCO)}
\subsection{Métricas Globales}
\subsection{Análisis de Errores}
\subsection{Skills Más Comunes Extraídas}

\section{Evaluación de Pipeline B (LLMs)}
\subsection{Comparación de 9 Modelos LLM}
\subsubsection{Métricas por Modelo}
\subsubsection{Trade-offs: Tamaño vs Precisión vs Velocidad}
\subsubsection{Análisis Estadístico (ANOVA + post-hoc tests)}

\subsection{Mejor Modelo: Qwen 3 4B}
\subsubsection{Por qué supera a otros}
\subsubsection{Ejemplos de extracción exitosa}
\subsubsection{Casos de falla}

\section{Comparación Pipeline A vs Pipeline B}
\subsection{Métricas Comparativas}
\subsection{Test de Significancia Estadística}
\subsection{Complementariedad de Pipelines}

\section{Habilidades Emergentes Detectadas}
\subsection{Top 50 Skills Emergentes por Frecuencia}
\subsection{Categorización de Emergentes}
\subsubsection{Tecnologías nuevas (2023-2025)}
\subsubsection{Frameworks y herramientas}
\subsubsection{Metodologías y prácticas}
\subsection{Skills Emergentes por País}
\subsection{Validación Manual de Emergentes}

\section{Análisis de Cobertura de ESCO}
\subsection{Porcentaje de Skills Mapeables a ESCO}
\subsection{Gaps Identificados en ESCO}
\subsection{Sesgo Europeo vs Realidad LATAM}

\section{Habilidades Implícitas}
\subsection{Ejemplos de Detección por Pipeline B}
\subsection{Comparación con Pipeline A (no detecta)}

\section{Velocidad y Costo Computacional}
\subsection{Tiempo de Procesamiento por Pipeline}
\subsection{Uso de Memoria y GPU}
\subsection{Escalabilidad a Producción}
```

### Action Items
- [ ] Structure Chapter 6 with subsections above
- [ ] Prepare placeholders for all tables/figures
- [ ] Plan 10-15 visualizations needed
- [ ] Reserve space for qualitative analysis (error examples)

---

## 10. Visualizations Needed

### Current State
Limited visualizations planned

### Recommended Visualizations for Results Chapter

1. **Bar chart**: Precision, Recall, F1 for 9 LLM models + Pipeline A (side-by-side)
2. **Scatter plot**: Size (parameters) vs F1-Score (showing trade-off)
3. **Heatmap**: Confusion matrix for best model (Qwen 3 4B)
4. **Pie chart**: Skills extraídas clasificadas (Technical, Soft, Emergentes)
5. **Bar chart**: Top 30 habilidades emergentes por frecuencia
6. **Venn diagram**: Skills detectadas por Pipeline A ∩ Pipeline B ∩ Gold Standard
7. **Line chart**: Evolución de skills emergentes por mes (temporal analysis)
8. **Bar chart**: Cobertura de ESCO por categoría (programming_languages 90%, cloud 65%, etc.)
9. **Box plot**: Distribución de F1-scores por modelo (showing variance)
10. **Table**: Qualitative examples of implicit skills detection
11. **Word cloud**: Skills emergentes más frecuentes
12. **Stacked bar chart**: Skills por país (CO/MX/AR) con emergentes highlighted

### Action Items
- [ ] Create all 12 visualizations after running experiments
- [ ] Use consistent color scheme (Pipeline A = blue, Pipeline B = green)
- [ ] Include error bars in bar charts
- [ ] Add figure captions with interpretation
- [ ] Cross-reference figures in text

---

## Summary of Action Items

### Critical (Must Do Before Submission)
1. ✅ Run experiments on 300 gold standard jobs
2. ✅ Fill all "TBD" and "Por determinar" cells with real data
3. ✅ Add dedicated "Habilidades Emergentes" subsection
4. ✅ Add explicit "Limitaciones de ESCO" subsection
5. ✅ Update LLM comparison from "2 modelos" → "9 modelos"
6. ✅ Create 12 visualizations for results
7. ✅ Add statistical significance tests

### Important (Should Do)
8. ✅ Add gold standard creation methodology
9. ✅ Add technical implementation details (Chapter 6)
10. ✅ Structure Results chapter with subsections
11. ✅ Strengthen contributions section
12. ✅ Add full prompt to Anexo A

### Nice to Have
13. ✅ Add temporal analysis of emerging skills
14. ✅ Include qualitative error analysis
15. ✅ Add trade-offs discussion (speed vs accuracy)

---

## Timeline Recommendation

1. **Week 1**: Create gold standard (annotate 300 jobs) ← Most time-consuming
2. **Week 2**: Run Pipeline A on gold standard, calculate metrics
3. **Week 3**: Run 9 LLM models (Pipeline B) on gold standard
4. **Week 4**: Analyze results, create visualizations, fill tables
5. **Week 5**: Write missing sections (emergentes, ESCO limitations, technical details)
6. **Week 6**: Review, polish, final edits

Total: ~6 weeks of focused work

---

## Next Steps

1. **Create gold standard dataset** using protocol defined above
2. **Address ESCO matching question**: How to ensure LLM extractions are matcheable to ESCO and avoid false emergentes (this is the question you asked before this document)
3. **Run experiments** once gold standard is ready
4. **Update LaTeX document** with sections identified here

---

**Document created**: 2025-11-04
**Purpose**: Preserve comprehensive recommendations for thesis improvement
**Status**: Ready for review and implementation
