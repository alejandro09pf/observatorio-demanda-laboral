# Observatorio de Demanda Laboral en América Latina

## Documento SAD

**Enero 2025**
**Versión 1.0**

**Nicolás Francisco Camacho Alarcón**
**Alejandro Pinzón Fajardo**

**Director:** Ing. Luis Gabriel Moreno Sandoval

**Planeación de Proyecto de Grado**

**PONTIFICIA UNIVERSIDAD JAVERIANA**
**BOGOTÁ D.C**

---

## Tabla de Control de Cambios

| Sección | Fecha | Sección del documento modificada | Descripción del Cambio | Responsables |
|---------|-------|----------------------------------|------------------------|--------------|
| 1. | DD/MM/2025 | Objetivo, Atributos de calidad | Documento inicial | Nicolás Camacho, Alejandro Pinzón |
| 2. | DD/MM/2025 | Arquitectura | Definición arquitectura y atributos de calidad | Nicolás Camacho, Alejandro Pinzón |

---

## Contenido

- [Objetivo](#objetivo)
- [Atributos de Calidad](#atributos-de-calidad)
  - [Descripción de atributos de calidad](#descripción-de-atributos-de-calidad)
  - [Atributos de calidad en el Observatorio](#atributos-de-calidad-en-el-observatorio)
  - [Priorización de atributos de calidad](#priorización-de-atributos-de-calidad)
  - [Escenarios de calidad](#escenarios-de-calidad)
- [Arquitectura](#arquitectura)
  - [Descripción del sistema](#descripción-del-sistema)
  - [Decisiones arquitectónicas](#decisiones-arquitectónicas)
  - [Consideraciones de diseño y mitigación de limitaciones](#consideraciones-de-diseño-y-mitigación-de-limitaciones)
  - [Diagrama de arquitectura de alto nivel](#diagrama-de-arquitectura-de-alto-nivel)
- [Riesgos](#riesgos)
- [Restricciones](#restricciones)
- [Referencias](#referencias)

---

## Objetivo

El presente documento tiene como propósito ofrecer una visión detallada de la arquitectura del sistema Observatorio de Demanda Laboral en América Latina, abordando aspectos clave como los atributos de calidad, la arquitectura de alto nivel y los factores de riesgo y restricciones asociados. Se establecerá una estructura clara del sistema, alineada con sus objetivos y requisitos arquitectónicos, tanto funcionales como no funcionales.

A lo largo del documento, se analizarán las decisiones arquitectónicas tomadas, justificando su elección y evaluando su impacto en el desarrollo del proyecto. Además, se incluirán representaciones gráficas para facilitar la comprensión de la estructura del sistema, y se definirán los pasos a seguir para asegurar que la arquitectura se mantenga alineada con los objetivos estratégicos del observatorio.

Este sistema está diseñado para automatizar el análisis de demanda laboral en el sector tecnológico de América Latina mediante técnicas avanzadas de procesamiento de lenguaje natural, embeddings semánticos y análisis de clustering, proporcionando insights valiosos sobre las habilidades técnicas más demandadas en Colombia, México y Argentina.

---

## Atributos de Calidad

Los atributos de calidad son características esenciales de un sistema de software que determinan su comportamiento y desempeño más allá de sus funcionalidades principales. Estos atributos permiten evaluar el sistema en términos de factores como eficiencia, precisión, mantenibilidad y escalabilidad, asegurando que la aplicación cumpla con los requerimientos tanto funcionales como no funcionales.

En arquitectura de software, cada decisión conlleva "trade-offs", lo que implica que mejorar un atributo de calidad puede afectar negativamente a otro. Por ejemplo, aumentar la precisión del sistema de extracción mediante procesamiento con LLMs puede impactar el desempeño al requerir mayor capacidad de procesamiento y tiempo de ejecución. De esta manera, el diseño arquitectónico debe encontrar un balance adecuado entre estos atributos, alineándose con los objetivos del sistema y las necesidades del proyecto.

### Descripción de atributos de calidad

Para estructurar la evaluación de los atributos de calidad, se utilizará el marco de referencia de la norma ISO 25010, que define diferentes categorías de atributos de calidad, cada una con subcaracterísticas específicas. En el contexto del Observatorio de Demanda Laboral, se han identificado los siguientes atributos como los más relevantes para la arquitectura del sistema:

- **Funcionalidad**: Evalúa si el sistema proporciona las funciones necesarias para cumplir con los objetivos de análisis de demanda laboral de manera precisa y completa.

- **Desempeño**: Analiza el uso eficiente de los recursos y el tiempo de procesamiento del sistema al ejecutar tareas de scraping, extracción, matching y clustering sobre grandes volúmenes de datos.

- **Precisión**: Determina la exactitud con la que el sistema extrae, clasifica y mapea habilidades técnicas contra taxonomías de referencia (ESCO, O*NET).

- **Fiabilidad**: Examina la estabilidad del sistema y su capacidad para operar sin fallos o pérdidas de datos durante el procesamiento batch de miles de ofertas laborales.

- **Mantenibilidad**: Evalúa la facilidad con la que el sistema puede ser actualizado, corregido y adaptado a nuevas necesidades sin comprometer su estabilidad.

- **Escalabilidad**: Determina la capacidad del sistema para manejar un crecimiento en el volumen de datos (de 23,000 a 600,000 ofertas) sin degradar su rendimiento.

- **Reproducibilidad**: Garantiza que los experimentos y análisis puedan ser replicados con resultados consistentes, esencial para un proyecto de investigación académica.

- **Trazabilidad**: Mide la capacidad del sistema para rastrear cada transformación de datos desde la oferta cruda hasta los resultados de clustering, permitiendo auditoría y debugging.

### Atributos de calidad en el Observatorio

A continuación, se describe cómo cada uno de estos atributos de calidad se aplican específicamente en el contexto del Observatorio de Demanda Laboral:

#### Funcionalidad

El sistema debe garantizar que todas las funciones necesarias para el análisis automatizado de demanda laboral sean implementadas de manera completa y precisa. Esto incluye:
- Scraping automatizado de 11 portales de empleo en 3 países
- Extracción de habilidades mediante métodos duales (NER+Regex y LLM)
- Matching contra taxonomías ESCO/O*NET con estrategia de 3 capas
- Generación de embeddings y clustering de habilidades
- Exportación de reportes y visualizaciones analíticas

La funcionalidad del sistema debe estar alineada con las necesidades de investigación académica, asegurando que los resultados obtenidos sean válidos, relevantes y comparables con el estado del arte en análisis de mercado laboral.

#### Desempeño

El desempeño es crítico dado el volumen objetivo de 600,000 ofertas laborales. El sistema debe ser capaz de:
- Procesar scraping asíncrono de múltiples portales sin generar bloqueos por rate limiting
- Ejecutar extracción de habilidades con latencias <2 segundos por oferta (Pipeline A tradicional)
- Generar embeddings en batches con throughput >700 skills/segundo
- Realizar búsquedas de similitud semántica con FAISS a >30,000 queries/segundo
- Completar el pipeline completo de 23,000 ofertas en <10 horas de procesamiento

El sistema debe gestionar los recursos computacionales de manera eficiente, aprovechando paralelismo cuando sea posible y evitando cuellos de botella en I/O de base de datos.

#### Precisión

Dado que se trata de un sistema de investigación académica, la precisión es fundamental. El sistema debe garantizar:
- **Extracción**: Precision >78% en regex patterns, >90% después de filtros NER
- **Matching ESCO**: Layer 1 (exact match) con confidence 1.00, Layer 2 (fuzzy) con threshold ≥0.85
- **Deduplicación**: SHA-256 hash para eliminar ofertas duplicadas con 100% de exactitud
- **Clustering**: Parámetros HDBSCAN ajustados para minimizar ruido y maximizar coherencia de grupos

El sistema debe documentar métricas de calidad (precision, recall, F1-score) para cada componente, permitiendo evaluación objetiva contra gold standards anotados manualmente.

#### Fiabilidad

La fiabilidad implica que el sistema debe ser capaz de operar de manera continua durante procesamiento batch sin errores críticos. Aspectos clave:
- Persistencia intermedia en PostgreSQL entre cada etapa del pipeline para permitir reinicio desde checkpoints
- Manejo robusto de errores en scraping (reintentos con backoff exponencial)
- Validación de integridad de datos mediante constraints de base de datos
- Logging estructurado de todas las operaciones críticas
- Mecanismos de rollback en caso de fallos durante transformaciones

La pérdida de datos debe minimizarse mediante backups regulares de PostgreSQL y trazabilidad completa de cada registro desde su origen hasta los resultados finales.

#### Mantenibilidad

El sistema debe estar diseñado de manera modular para facilitar su mantenimiento y evolución. Aspectos clave:
- Arquitectura de pipeline lineal con separación clara de responsabilidades por módulo
- Código bien documentado con docstrings y type hints en Python 3.11+
- Scripts de migración de base de datos versionados y auditables
- Configuración externalizada mediante archivos .env y config.yaml
- Tests unitarios para componentes críticos (extracción, matching, clustering)

La implementación de nuevas funcionalidades (ej. agregar nuevos portales de scraping) debe realizarse sin afectar módulos existentes, siguiendo el principio de Open/Closed.

#### Escalabilidad

El sistema debe ser capaz de escalar desde el corpus actual de 23,000 ofertas hasta el objetivo de 600,000. Estrategias:
- Procesamiento batch con tamaño de lote configurable
- Particionamiento de tablas PostgreSQL por país y fecha
- Índices optimizados en columnas frecuentemente consultadas
- FAISS para búsqueda vectorial (25x más rápido que pgvector)
- Arquitectura stateless que permite distribución horizontal futura

Si bien la arquitectura actual es monolítica, está diseñada para permitir refactorización incremental a microservicios si el volumen lo requiere.

#### Reproducibilidad

Como proyecto de investigación académica, la reproducibilidad es esencial:
- Control de versiones de dependencias mediante requirements.txt con versiones fijas
- Semillas fijas para componentes estocásticos (random_state en UMAP, HDBSCAN)
- Versionado de modelos (spaCy, E5 embeddings, LLMs)
- Datasets de evaluación públicos (Gold Standard de 300 jobs anotados)
- Documentación completa de experimentos y parámetros

Los resultados reportados deben ser replicables por investigadores externos siguiendo la documentación proporcionada.

#### Trazabilidad

El sistema debe permitir rastrear cada transformación:
- Cada skill extraída mantiene referencia al job_id original
- Cada matching ESCO registra método (exact/fuzzy/semantic) y confidence score
- Cada clustering guarda parámetros utilizados (UMAP n_neighbors, HDBSCAN min_cluster_size)
- Timestamps de cada operación (scraped_at, extracted_at, analyzed_at)
- Logs estructurados con niveles (DEBUG, INFO, WARNING, ERROR)

Esta trazabilidad es crítica para debugging, evaluación de calidad y validación de resultados científicos.

---

### Priorización de atributos de calidad

Para garantizar que el Observatorio cumpla con sus objetivos y ofrezca resultados científicamente válidos, es esencial priorizar los atributos de calidad en función de su impacto en el sistema. La siguiente clasificación justifica la relevancia de cada atributo dentro del contexto del proyecto.

#### Prioridad Alta

**Precisión**: Es el atributo más crítico ya que el valor científico del observatorio depende directamente de la exactitud de sus resultados. Si el sistema extrae habilidades incorrectas o las mapea erróneamente a ESCO, todo el análisis posterior (clustering, tendencias, reportes) será inválido. La precisión es irrenunciable en un proyecto de investigación académica.

**Fiabilidad**: Los registros de 23,000+ ofertas laborales representan meses de scraping y miles de horas de procesamiento. La pérdida de datos o corrupción de resultados sería catastrófica. El sistema debe ser capaz de operar de manera continua sin errores que comprometan la integridad de los datos almacenados. Los mecanismos de checkpoint y persistencia intermedia son fundamentales.

**Reproducibilidad**: Como proyecto académico, los experimentos deben ser replicables por revisores y la comunidad científica. La falta de reproducibilidad invalidaría las contribuciones del proyecto y limitaría su impacto académico. Control de versiones de dependencias y semillas fijas son obligatorios.

**Trazabilidad**: Cada resultado debe poder rastrearse hasta su fuente original. Esto es esencial para debugging, validación de resultados y auditoría científica. Sin trazabilidad completa, es imposible identificar y corregir errores sistemáticos en el pipeline.

#### Prioridad Media

**Funcionalidad**: El sistema debe implementar todas las funciones planificadas (scraping, extracción dual, matching, clustering, visualización). Sin embargo, puede desarrollarse incrementalmente mediante entregas iterativas. No es necesario tener todas las funciones desde el día 1, pero sí un plan claro de implementación.

**Desempeño**: Es importante para viabilidad del proyecto (procesar 600K ofertas en tiempo razonable), pero puede optimizarse progresivamente. Latencias de horas son aceptables en procesamiento batch académico. Se priorizará corrección sobre velocidad en caso de trade-offs.

**Mantenibilidad**: Es relevante para la evolución del proyecto y futura investigación, pero puede gestionarse progresivamente siempre que se sigan buenas prácticas de desarrollo. Refactorización es posible en fases posteriores.

#### Prioridad Baja

**Escalabilidad**: El volumen objetivo de 600K ofertas es procesable con arquitectura monolítica actual. Si bien se diseña pensando en escalabilidad futura, no es crítico optimizar para millones de registros en esta fase del proyecto. La refactorización a microservicios puede posponerse.

---

### Escenarios de calidad

A continuación se presentan escenarios concretos que ilustran cómo el sistema debe comportarse respecto a los atributos de calidad priorizados.

#### Escenario de calidad N-1: Precisión en Extracción

**Atributo**: Precisión

El sistema debe extraer habilidades técnicas de ofertas laborales con alta precision, evitando falsos positivos que contaminen el análisis.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Un investigador procesa un batch de 100 ofertas laborales de México. |
| **Estímulo** | Ejecución del Pipeline A (NER + Regex) sobre ofertas en español técnico mezclado con Spanglish. |
| **Artefacto** | Módulo de extracción (src/extractor/ner_extractor.py y regex_patterns.py) |
| **Ambiente** | Condiciones normales, ofertas previamente limpias en tabla cleaned_jobs |
| **Respuesta** | El sistema extrae skills candidatas, las filtra, y persiste en extracted_skills con scores de confianza. |
| **Medida de Respuesta** | Precision ≥78% en regex patterns, ≥90% después de filtros NER (validado contra gold standard de 300 ofertas anotadas) |

#### Escenario de calidad N-2: Desempeño en Matching ESCO

**Atributo**: Desempeño

El sistema debe mapear habilidades extraídas contra taxonomía ESCO de 14,174 skills en tiempos razonables.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | El sistema procesa 2,756 skills extraídas de 100 ofertas laborales |
| **Estímulo** | Ejecución del matcher de 3 capas (exact → fuzzy → semantic deshabilitada) |
| **Artefacto** | Módulo esco_matcher_3layers.py con búsquedas SQL y fuzzywuzzy |
| **Ambiente** | PostgreSQL con 14,174 skills ESCO indexadas, servidor con 16GB RAM |
| **Respuesta** | El sistema completa matching de todas las skills y retorna resultados con confidence scores |
| **Medida de Respuesta** | Latencia total ≤5 segundos para 2,756 skills (1.8ms promedio por skill) |

#### Escenario de calidad N-3: Fiabilidad ante Fallos de Scraping

**Atributo**: Fiabilidad

El sistema debe continuar operando de forma estable ante fallos temporales de portales web sin pérdida de datos.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Portal Bumeran.mx retorna HTTP 503 (Service Unavailable) durante scraping |
| **Estímulo** | 10 requests consecutivos fallan con timeout o error de servidor |
| **Artefacto** | Scrapy spider para Bumeran con middleware de reintentos |
| **Ambiente** | Scraping nocturno automatizado, 5 portales siendo scrapeados concurrentemente |
| **Respuesta** | El sistema registra el error, pausa temporalmente ese spider (backoff exponencial), continúa con otros portales, y reintenta después de 5 minutos |
| **Medida de Respuesta** | 0% pérdida de datos, reintentos exitosos en siguiente ventana, logging completo de errores para auditoría |

#### Escenario de calidad N-4: Reproducibilidad de Clustering

**Atributo**: Reproducibilidad

Los resultados de clustering deben ser reproducibles para validación científica.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Un investigador externo ejecuta el pipeline de clustering con parámetros documentados |
| **Estímulo** | Ejecución de UMAP (n_neighbors=15, min_dist=0.1, random_state=42) + HDBSCAN (min_cluster_size=50, min_samples=10) sobre embeddings de 14,133 skills |
| **Artefacto** | Scripts de clustering con parámetros fijos y semilla aleatoria |
| **Ambiente** | Mismos embeddings E5 v1.0, mismas versiones de bibliotecas (umap-learn==0.5.3, hdbscan==0.8.29) |
| **Respuesta** | El sistema genera exactamente los mismos clústeres con las mismas etiquetas y probabilidades |
| **Medida de Respuesta** | 100% coincidencia en cluster assignments (comparando cluster_id por cada skill_text) |

#### Escenario de calidad N-5: Trazabilidad de Resultados

**Atributo**: Trazabilidad

Cada resultado de análisis debe poder rastrearse hasta la oferta laboral original.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Un investigador identifica una skill "Next.js" en un clúster emergente |
| **Estímulo** | Query de trazabilidad desde skill → extracted_skills → raw_jobs → portal original |
| **Artefacto** | Base de datos PostgreSQL con foreign keys y timestamps |
| **Ambiente** | Sistema en operación normal con 23,188 ofertas procesadas |
| **Respuesta** | El sistema retorna: job_id, portal (hiring_cafe), país (MX), URL original, fecha de scraping, método de extracción (regex), confidence score |
| **Medida de Respuesta** | Trazabilidad completa en 100% de los casos, latencia <100ms para query de trazabilidad |

#### Escenario de calidad N-6: Precisión en Matching ESCO

**Atributo**: Precisión

El matching contra taxonomía ESCO debe evitar falsos positivos que introduzcan ruido.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Pipeline A extrae 47 skills de una oferta de Data Scientist |
| **Estímulo** | Ejecución de 3-layer matching: exact → fuzzy (threshold 0.85) → semantic (deshabilitado) |
| **Artefacto** | esco_matcher_3layers.py con Layer 1+2 activos |
| **Ambiente** | Condiciones normales con taxonomía ESCO de 14,174 skills |
| **Respuesta** | Layer 1 encuentra 4 matches exactos (Python, Machine Learning, GitHub, Data Infrastructure), Layer 2 encuentra 1 fuzzy match (ML → MLOps ratio 0.88), 42 skills marcadas como emergent |
| **Medida de Respuesta** | 0% falsos positivos (validado manualmente que todos los matches son semánticamente correctos), recall aceptable de 10.6% dado que ESCO v1.1.0 tiene coverage limitado de tech moderno |

#### Escenario de calidad N-7: Desempeño de Generación de Embeddings

**Atributo**: Desempeño

El sistema debe generar embeddings de miles de skills de manera eficiente.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Fase 0 del pipeline requiere generar embeddings para 14,133 skills únicas |
| **Estímulo** | Ejecución de scripts/phase0_generate_embeddings.py con modelo E5 multilingual-base |
| **Artefacto** | Modelo intfloat/multilingual-e5-base (768D) ejecutando en GPU |
| **Ambiente** | Servidor con Apple MPS / CUDA GPU, batch_size=32 |
| **Respuesta** | El sistema genera embeddings normalizados L2, los almacena en skill_embeddings table, y valida distribución Gaussiana |
| **Medida de Respuesta** | Throughput ≥700 skills/segundo, tiempo total <25 segundos para 14,133 skills, 100% embeddings con norm=1.0000 |

#### Escenario de calidad N-8: Mantenibilidad ante Cambios de Taxonomía

**Atributo**: Mantenibilidad

El sistema debe facilitar la adición de nuevas skills a la taxonomía sin afectar datos existentes.

| Elemento | Descripción |
|----------|-------------|
| **Fuente del estímulo** | Un investigador identifica 41 skills técnicas modernas faltantes en ESCO |
| **Estímulo** | Ejecución de scripts/add_manual_tech_skills.py para agregar (FastAPI, Next.js, Tailwind CSS, etc.) |
| **Artefacto** | Script de migración con INSERT INTO esco_skills |
| **Ambiente** | Sistema en producción con 13,939 skills ESCO base |
| **Respuesta** | El sistema agrega las 41 nuevas skills con skill_type='manual_curated', regenera embeddings solo para las nuevas, reconstruye índice FAISS incremental |
| **Medida de Respuesta** | Operación completada en <2 minutos, 0 impacto en skills existentes, nuevo total 14,174 skills validado |

---

## Arquitectura

### Descripción del sistema

El Observatorio de Demanda Laboral es un sistema académico de investigación diseñado para automatizar el análisis de habilidades técnicas demandadas en el mercado laboral de América Latina. A través de técnicas avanzadas de procesamiento de lenguaje natural, embeddings semánticos y clustering no supervisado, el sistema permite identificar tendencias, perfiles emergentes y brechas de competencias en el sector tecnológico de Colombia, México y Argentina.

El sistema opera en modo batch, procesando miles de ofertas laborales recolectadas automáticamente desde 11 portales de empleo (Computrabajo, Bumeran, ElEmpleo, InfoJobs, OCC Mundial, ZonaJobs, hiring.cafe, entre otros). La arquitectura está diseñada para maximizar precisión y reproducibilidad científica, priorizando calidad de resultados sobre velocidad de procesamiento.

La plataforma integra dos pipelines paralelos de extracción de habilidades:
- **Pipeline A (Tradicional)**: NER con spaCy + Regex patterns + Matching ESCO de 3 capas (exact/fuzzy/semantic)
- **Pipeline B (Experimental)**: LLM-based extraction con Gemma 3 4B o Llama 3 3B para comparación científica

Los resultados se almacenan en PostgreSQL con trazabilidad completa, generan embeddings mediante E5 Multilingual (768D), reducción dimensional con UMAP, clustering con HDBSCAN, y exportación de visualizaciones y reportes analíticos.

El sistema está diseñado como herramienta de investigación académica con enfoque en reproducibilidad, trazabilidad y validación científica de resultados. A diferencia de plataformas comerciales, prioriza transparencia metodológica y código abierto sobre optimización extrema de performance.

### Decisiones arquitectónicas

La arquitectura del Observatorio adopta un enfoque de **pipeline secuencial de 8 etapas**, diseñado específicamente para las características y restricciones de un proyecto de investigación académica. A continuación se justifican las decisiones arquitectónicas principales.

#### Arquitectura de Pipeline Lineal vs Microservicios

Se seleccionó **arquitectura de pipeline lineal** sobre microservicios o event-driven por las siguientes razones:

**Ventajas seleccionadas:**
1. **Simplicidad operativa**: Proyecto académico con equipo de 2 desarrolladores y recursos computacionales limitados (1-2 servidores, sin infraestructura Kubernetes/Docker Swarm)
2. **Trazabilidad completa**: Flujo unidireccional de datos permite debugging determinístico y auditoría de transformaciones etapa por etapa, esencial para validación científica
3. **Velocidad de desarrollo**: Implementación de microservicios requiere 3-4x más tiempo en configuración de comunicación inter-servicios, service discovery, y manejo de fallos distribuidos
4. **Naturaleza batch del dominio**: Análisis de demanda laboral no requiere procesamiento en tiempo real (latencias de horas/días son aceptables), eliminando ventajas principales de arquitecturas asíncronas
5. **Reproducibilidad**: Pipeline secuencial con parámetros fijos facilita reproducción exacta de experimentos, crítico para publicación científica

**Trade-offs aceptados:**
- **Limitación de paralelismo**: Procesamiento secuencial sincrónico impide aprovechamiento de paralelismo entre etapas
- **Escalabilidad horizontal limitada**: Arquitectura monolítica requeriría migración a microservicios si volumen supera 100K ofertas mensuales
- **Latencia acumulativa**: Pipeline completo con LLM puede tomar 30-60 segundos por oferta (aceptable para batch académico)
- **Single point of failure**: Fallo de una etapa detiene pipeline completo (mitigado con persistencia intermedia y checkpoints)

Estas limitaciones fueron consideradas aceptables dado que el análisis académico de demanda laboral no requiere procesamiento en tiempo real, mientras que el volumen objetivo de 600K ofertas es procesable en 5-10 horas con hardware disponible.

#### Pipeline Secuencial de 8 Etapas

El sistema implementa las siguientes etapas especializadas:

1. **Scraping (Scrapy + Selenium)**: Recolección automatizada de ofertas desde portales web
   - Scrapy para scraping asíncrono eficiente
   - Selenium para contenido JavaScript dinámico
   - Deduplicación SHA-256 para eliminar duplicados

2. **Cleaning (HTML Strip + Normalization)**: Limpieza y normalización de texto
   - Remoción de etiquetas HTML
   - Normalización de espacios y caracteres
   - Detección de jobs basura

3. **Extraction A (NER + Regex)**: Identificación de habilidades explícitas
   - spaCy NER con EntityRuler ESCO
   - 47 regex patterns para tecnologías estructuradas
   - Combinación y deduplicación

4. **Extraction B (LLM)**: Enriquecimiento semántico e inferencia de habilidades implícitas
   - Gemma 3 4B o Llama 3 3B (evaluación comparativa pendiente)
   - Prompt engineering para español técnico LatAm
   - Solo para subconjunto estratégico (costo computacional)

5. **Matching ESCO (3-Layer Strategy)**: Normalización contra taxonomías
   - Layer 1: Exact match SQL (confidence 1.00)
   - Layer 2: Fuzzy match fuzzywuzzy (threshold 0.85)
   - Layer 3: Semantic FAISS (deshabilitado por limitaciones E5)

6. **Embedding (E5 Multilingual)**: Generación de representaciones vectoriales 768D
   - Modelo intfloat/multilingual-e5-base
   - Normalización L2 para cosine similarity
   - Batch processing con GPU acceleration

7. **Dimension Reduction (UMAP)**: Proyección a 2-3 dimensiones visualizables
   - Preserva estructura local y global
   - Parámetros: n_neighbors=15, min_dist=0.1

8. **Clustering (HDBSCAN)**: Agrupamiento no supervisado de habilidades
   - No requiere especificar k (número de clústeres)
   - Identifica ruido automáticamente
   - Parámetros: min_cluster_size=50, min_samples=10

Cada etapa opera de forma autónoma, lee datos de la etapa anterior desde PostgreSQL, ejecuta su transformación especializada, y persiste resultados para la siguiente etapa.

#### Selección de Tecnologías Críticas

**PostgreSQL 15+ como Persistencia Central:**
- Soporte JSONB para metadatos flexibles
- Extensión pgvector para vectores 768D (aunque FAISS es más rápido)
- Robustez transaccional ACID
- Particionamiento para escalabilidad
- Licencia libre (PostgreSQL License)

**FAISS para Búsqueda Vectorial:**
- 30,147 queries/segundo (25x más rápido que pgvector)
- Exact search con IndexFlatIP (100% recall)
- Latencia 0.033ms por query
- Desarrollado por Facebook AI Research

**spaCy + EntityRuler para NER:**
- Modelo es_core_news_lg (97M parámetros)
- EntityRuler poblado con 14,174 skills ESCO
- Latencia <100ms por documento
- Optimizado para CPU

**ESCO v1.1.0 como Taxonomía Base:**
- 13,939 skills con etiquetas ES/EN
- Estructura ontológica con URIs
- Licencia CC BY 4.0
- Expandida con 152 O*NET + 83 manual = 14,174 total

**Python 3.11+ como Lenguaje Principal:**
- Ecosistema científico maduro (NumPy, pandas, scikit-learn)
- Bibliotecas NLP de referencia (spaCy, transformers)
- Integración nativa con PostgreSQL (psycopg2)
- Type hints para mantenibilidad

#### Estrategia Dual de Pipelines

Se implementan **dos pipelines paralelos** para comparación científica rigurosa:

**Pipeline A (Control - Alta Precisión):**
- Métodos tradicionales validados: NER + Regex
- Procesa 100% de ofertas laborales
- Precision 78-95%, latencia <2 segundos/oferta
- Baseline para comparación

**Pipeline B (Tratamiento - Alta Cobertura):**
- LLM-based extraction con modelos ligeros locales
- Procesa subconjunto estratégico (300-1000 ofertas)
- Precision esperada 80-90%, latencia 5-10 segundos/oferta
- Captura habilidades implícitas no detectadas por Pipeline A

Ambos pipelines usan el **mismo módulo de matching ESCO** (3-layer strategy), permitiendo comparación justa. Los resultados se almacenan en la misma tabla `extracted_skills` con campo `extraction_method` para diferenciar origen.

Esta arquitectura permite:
1. **Evaluación empírica** de NER/Regex vs LLMs en español técnico LatAm
2. **Validación contra Gold Standard** de 300 ofertas anotadas manualmente
3. **Análisis de coverage** de habilidades explícitas vs implícitas
4. **Evaluación de trade-offs** precision/recall vs costo computacional

### Consideraciones de diseño y mitigación de limitaciones

Para abordar las limitaciones inherentes a la arquitectura de pipeline lineal y optimizar el rendimiento dentro de las restricciones académicas, se implementaron las siguientes estrategias:

#### 1. Persistencia Intermedia y Checkpointing

**Problema**: Pipeline secuencial de 8 etapas acumula latencia y un fallo en cualquier punto pierde todo el progreso.

**Solución**:
- Cada etapa persiste resultados en PostgreSQL antes de continuar
- Tablas especializadas: raw_jobs → cleaned_jobs → extracted_skills → skill_embeddings → analysis_results
- Campo `extraction_status` en raw_jobs permite reanudar desde última etapa completada
- Transacciones ACID garantizan atomicidad de cada batch

**Beneficio**: Sistema puede reiniciarse desde cualquier etapa sin reprocesar todo el dataset. Fallo en Etapa 6 no invalida trabajo de Etapas 1-5.

#### 2. Deduplicación Multi-Nivel

**Problema**: Portales de empleo duplican ofertas (cross-posting, re-postings), inflando artificialmente el dataset.

**Solución**:
- **Nivel 1 (Scraping)**: SHA-256 hash de (title + company + description) con constraint UNIQUE en PostgreSQL
- **Nivel 2 (Extracción)**: Constraint UNIQUE(job_id, skill_text, extraction_method) en extracted_skills
- **Nivel 3 (Embeddings)**: Constraint UNIQUE(skill_text) en skill_embeddings

**Beneficio**: Elimina duplicados con 0% falsos positivos, reduciendo dataset de ~30K a 23,188 ofertas únicas.

#### 3. Batch Processing Optimizado

**Problema**: Procesar ofertas una por una es ineficiente (overhead de I/O de BD).

**Solución**:
- Generación de embeddings en batches de 32 (aprovecha GPU parallelism)
- Inserts a BD en batches de 100 (reduce round-trips)
- Cursor server-side en PostgreSQL para queries grandes (evita cargar todo en RAM)

**Beneficio**: Throughput de 721 skills/segundo en embeddings (vs. ~50 skills/segundo sin batching).

#### 4. Índices de Base de Datos Optimizados

**Problema**: Queries de matching ESCO requieren búsquedas de texto en 14,174 registros.

**Solución**:
```sql
CREATE INDEX idx_esco_skills_preferred_label_es
  ON esco_skills USING GIN (preferred_label_es gin_trgm_ops);
CREATE INDEX idx_esco_skills_preferred_label_en
  ON esco_skills USING GIN (preferred_label_en gin_trgm_ops);
CREATE INDEX idx_extracted_skills_job_id
  ON extracted_skills (job_id);
```

**Beneficio**: Matching de 2,756 skills en <5 segundos (vs. minutos sin índices).

#### 5. Logging Estructurado y Monitoreo

**Problema**: Debugging de pipeline de 8 etapas es complejo sin visibilidad.

**Solución**:
- Logging estructurado con niveles (DEBUG, INFO, WARNING, ERROR)
- Timestamps de cada operación (scraped_at, extracted_at, analyzed_at)
- Métricas de performance por etapa (skills_extracted, match_rate, latency)
- Progress bars con tqdm para operaciones batch

**Beneficio**: Identificación rápida de cuellos de botella y errores sistemáticos.

#### 6. Validación y Tests Automatizados

**Problema**: Errores silenciosos en pipeline pueden contaminar resultados.

**Solución**:
- Tests unitarios para componentes críticos (37 tests en scripts/test_embeddings.py)
- Validación de integridad de datos:
  - Embeddings normalizados L2 (norm=1.0000±0.0001)
  - Sin valores NaN/Inf en vectores
  - Distribución Gaussiana centrada en 0
- Tests de similitud semántica: "Python"↔"Java", "Docker"↔"Kubernetes"

**Beneficio**: Detección temprana de degradación de calidad.

#### 7. Deshabilitación de Layer 3 Semántico

**Problema**: Modelo E5 genera matches absurdos en vocabulario técnico ("React" → "neoplasia").

**Decisión Arquitectónica**:
- Layer 3 (semantic matching con FAISS) **temporalmente deshabilitado**
- Operación con Layer 1 (exact) + Layer 2 (fuzzy) es suficiente
- Match rate de 10-15% es **esperado** dado que ESCO v1.1.0 data de 2016-2017
- Skills no matched se clasifican como **emergent skills** (señal valiosa de tendencias)

**Beneficio**: 100% precision en matching (sin falsos positivos), priorizando calidad sobre cobertura.

#### 8. Versionado de Modelos y Dependencias

**Problema**: Reproducibilidad científica requiere control total de versiones.

**Solución**:
```
requirements.txt (versiones fijas):
spacy==3.7.2
sentence-transformers==2.2.2
faiss-cpu==1.7.4
umap-learn==0.5.3
hdbscan==0.8.29
```
- Modelos descargados localmente (spaCy es_core_news_lg, E5 multilingual-base)
- Git tags para versiones de código
- Parámetros de experimentos en config.yaml versionado

**Beneficio**: Reproducibilidad exacta de resultados por investigadores externos.

---

### Diagrama de arquitectura de alto nivel

El sistema se estructura en un pipeline secuencial de 8 etapas con persistencia intermedia en PostgreSQL. La siguiente descripción detalla el flujo de datos y las tecnologías involucradas:

```
┌─────────────────────────────────────────────────────────────────────┐
│  FASE 0: SETUP INICIAL (Una sola vez)                              │
├─────────────────────────────────────────────────────────────────────┤
│  • Carga taxonomía ESCO (13,939) + O*NET (152) + Manual (83)      │
│  • Generación embeddings E5 (14,133 skills → 768D)                │
│  • Construcción índice FAISS (30,147 queries/segundo)             │
│  → Tiempo: ~25 segundos  │  Estado: ✅ COMPLETADO                 │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 1: WEB SCRAPING                                             │
├─────────────────────────────────────────────────────────────────────┤
│  Tecnología: Scrapy 2.11 + Selenium 4.15                           │
│  Fuentes: 11 portales (Computrabajo, Bumeran, hiring.cafe, etc.)  │
│  Países: Colombia, México, Argentina                               │
│  Deduplicación: SHA-256 hash (title+company+description)          │
│  Salida: raw_jobs table (23,352 ofertas → 23,188 únicas)          │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 2: LIMPIEZA DE DATOS                                        │
├─────────────────────────────────────────────────────────────────────┤
│  Tecnología: Python + regex                                        │
│  Operaciones:                                                      │
│    • Remoción de HTML tags                                         │
│    • Normalización de espacios y caracteres                        │
│    • Detección de jobs basura (125 ofertas, 0.5%)                 │
│  Salida: cleaned_jobs table (23,188 ofertas limpias)              │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
        ┌─────────────────────┴─────────────────────┐
        ↓                                           ↓
┌─────────────────────────┐          ┌─────────────────────────┐
│  ETAPA 3A: PIPELINE A   │          │  ETAPA 3B: PIPELINE B   │
│  (Tradicional)          │          │  (LLM Experimental)     │
├─────────────────────────┤          ├─────────────────────────┤
│  • NER (spaCy +         │          │  • Gemma 3 4B /         │
│    EntityRuler ESCO)    │          │    Llama 3 3B           │
│  • Regex (47 patterns)  │          │  • Prompt engineering   │
│  • Precision: 78-95%    │          │  • Habilidades          │
│  • Latencia: <2s/oferta │          │    implícitas           │
│  • Coverage: 100% jobs  │          │  • Latencia: 5-10s      │
│                         │          │  • Coverage: 300 jobs   │
└─────────────────────────┘          └─────────────────────────┘
        │                                           │
        └─────────────────────┬─────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 4: MATCHING ESCO (3-Layer Strategy)                         │
├─────────────────────────────────────────────────────────────────────┤
│  Layer 1: Exact Match (SQL ILIKE) → confidence 1.00                │
│  Layer 2: Fuzzy Match (fuzzywuzzy ≥0.85) → confidence 0.85-0.99    │
│  Layer 3: Semantic (FAISS) → ⚠️ DESHABILITADO                      │
│  Taxonomía: ESCO (14,174 skills)                                   │
│  Salida: extracted_skills table (match_rate 10-15%)                │
│          + emergent_skills table (85-90% skills no matched)        │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 5: GENERACIÓN DE EMBEDDINGS                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Modelo: intfloat/multilingual-e5-base (768D)                      │
│  Tecnología: sentence-transformers + GPU                           │
│  Procesamiento: Batches de 32, normalización L2                   │
│  Throughput: 721 skills/segundo                                    │
│  Salida: skill_embeddings table (14,133 embeddings únicos)         │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 6: REDUCCIÓN DIMENSIONAL                                    │
├─────────────────────────────────────────────────────────────────────┤
│  Algoritmo: UMAP (768D → 2D)                                       │
│  Parámetros: n_neighbors=15, min_dist=0.1, metric='cosine'        │
│  Objetivo: Preservar estructura local y global para visualización │
│  Salida: Coordenadas 2D para cada skill                           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 7: CLUSTERING                                               │
├─────────────────────────────────────────────────────────────────────┤
│  Algoritmo: HDBSCAN (density-based, hierarchical)                 │
│  Parámetros: min_cluster_size=50, min_samples=10                  │
│  Ventajas: No requiere k, identifica ruido, densidades variables  │
│  Salida: Cluster assignments + probabilidades por skill           │
└─────────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────────┐
│  ETAPA 8: VISUALIZACIÓN Y REPORTES                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Tecnologías: matplotlib, seaborn, plotly                         │
│  Visualizaciones:                                                  │
│    • Scatter plot UMAP 2D (clusters coloreados)                   │
│    • Top skills por país (barras)                                 │
│    • Tendencias temporales (líneas)                               │
│    • Co-ocurrencia de skills (heatmap)                            │
│  Exportación: PDF, PNG, CSV, JSON                                 │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  PERSISTENCIA CENTRAL: PostgreSQL 15+                              │
├─────────────────────────────────────────────────────────────────────┤
│  Tablas principales:                                               │
│    • raw_jobs (23,352)         • cleaned_jobs (23,188)             │
│    • extracted_skills          • skill_embeddings (14,133)         │
│    • esco_skills (14,174)      • emergent_skills                   │
│    • analysis_results          • job_embeddings                    │
│  Soporte: JSONB, pgvector, particionamiento, índices optimizados  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│  INFRAESTRUCTURA AUXILIAR                                          │
├─────────────────────────────────────────────────────────────────────┤
│  • FAISS: Búsqueda vectorial (30K q/s, IndexFlatIP)                │
│  • Git + GitHub: Control de versiones y CI/CD                      │
│  • Typer CLI: Orquestación de pipeline (interface tipo Git)        │
│  • Python 3.11+: Lenguaje principal con type hints                 │
│  • requirements.txt: Dependencias versionadas                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Flujo de Datos Resumido:**
1. Portales Web → Scrapy/Selenium → raw_jobs (PostgreSQL)
2. raw_jobs → Limpieza → cleaned_jobs
3. cleaned_jobs → Pipeline A (NER+Regex) / Pipeline B (LLM) → extracted_skills
4. extracted_skills → Matching ESCO → esco_uri + confidence
5. Skills únicas → E5 embeddings → skill_embeddings (768D)
6. skill_embeddings → UMAP → coordenadas 2D
7. Coordenadas 2D → HDBSCAN → cluster assignments
8. Resultados → Visualizaciones → Reportes (PDF/PNG/CSV)

**Características Clave:**
- ✅ Modularidad: Cada etapa puede ejecutarse independientemente
- ✅ Trazabilidad: Foreign keys mantienen relación con raw_jobs
- ✅ Reproducibilidad: Parámetros fijos, semillas aleatorias, versiones controladas
- ✅ Escalabilidad: Batch processing, índices optimizados, particionamiento
- ✅ Resiliencia: Persistencia intermedia, checkpoints, manejo de errores

---

## Riesgos

Los riesgos identificados se agrupan en tres categorías principales: riesgos de producto, riesgos de proceso y riesgos de proyecto. Cada uno puede afectar la calidad, validez científica y éxito del observatorio.

### Riesgos de Producto

Estos riesgos se relacionan con la calidad, precisión, rendimiento y fiabilidad del sistema final.

#### Riesgos de Precisión:

- **Falsos positivos en extracción NER**: Extracción de frases genéricas o disclaimers legales como skills técnicas (ej. "national origin", "aspirar a la excelencia"). Ya identificado en pruebas con 10.6% match rate y 87.4% emergent skills, requiere mejora de filtros NER.

- **Degradación de modelos pre-entrenados**: spaCy es_core_news_lg y E5 multilingual fueron entrenados en lenguaje general, no especializado en tech jobs de LatAm. Posible bajo rendimiento en Spanglish y jerga técnica local.

- **Baja cobertura de ESCO**: Taxonomía ESCO v1.1.0 data de 2016-2017, no cubre frameworks modernos (Next.js, SolidJS, Remix). Match rate de 12.6% es esperado pero puede limitar análisis comparativo con literatura que usa taxonomías actualizadas.

#### Riesgos de Rendimiento:

- **Latencia acumulativa en Pipeline B**: Procesamiento con LLM (Gemma/Llama) puede tomar 5-10 segundos por oferta. Para 600K ofertas = 833 horas de cómputo (34 días continuos). Puede hacer inviable procesamiento completo del corpus objetivo.

- **Cuellos de botella en I/O de BD**: Inserts/updates frecuentes en PostgreSQL durante extracción pueden saturar I/O del disco. Mitigado con batch processing pero requiere monitoreo.

- **Memoria insuficiente para UMAP**: Reducción dimensional de 14K+ embeddings de 768D requiere ~10GB RAM. Servidores limitados pueden fallar en esta etapa.

#### Riesgos de Fiabilidad:

- **Pérdida de datos por fallos de hardware**: Scraping de meses puede perderse por fallo de disco sin backups. Sistema académico sin infraestructura de alta disponibilidad.

- **Corrupción de embeddings**: Generación de embeddings interrumpida puede dejar skill_embeddings table en estado inconsistente (algunos skills con embeddings, otros sin). Difícil de detectar sin validación exhaustiva.

- **Dependencia de servicios externos**: Scrapers dependen de portales web que pueden cambiar HTML structure, implementar rate limiting más agresivo, o bloquear IPs. Puede invalidar meses de desarrollo de selectores CSS.

### Riesgos de Proceso

Estos riesgos están asociados al desarrollo, experimentación y mantenimiento del sistema.

#### Riesgos de Experimentación Científica:

- **Sesgo de selección en Gold Standard**: Anotación manual de 300 ofertas puede tener sesgos (ej. sobre-representación de Python jobs, sub-representación de .NET). Invalida evaluación comparativa de Pipelines A vs B.

- **Inter-annotator disagreement**: Dos anotadores pueden discrepar en qué constituye una "skill" (ej. ¿"Remote Work" es skill o modalidad?). Cohen's Kappa <0.80 invalida Gold Standard.

- **Overfitting a ESCO**: Sistema optimizado para maximizar match rate con ESCO puede perder skills emergentes valiosas. Sesgo hacia skills tradicionales europeas vs. innovaciones LatAm.

#### Riesgos de Mantenibilidad:

- **Complejidad de debugging de pipeline de 8 etapas**: Error en Etapa 7 (clustering) puede ser causado por problema en Etapa 5 (embeddings) o Etapa 3 (extracción). Trazabilidad completa mitiga pero no elimina complejidad.

- **Falta de documentación de decisiones experimentales**: Cambios en parámetros (ej. UMAP n_neighbors 10→15) sin documentar impactan reproducibilidad. Requiere disciplina rigurosa en versionado.

- **Dependencia de expertos en dominio**: Validación de resultados de clustering requiere expertos en mercado laboral tech LatAm. Pérdida de acceso a expertos puede paralizar validación cualitativa.

#### Riesgos de Implementación:

- **Curva de aprendizaje de tecnologías especializadas**: FAISS, UMAP, HDBSCAN son tecnologías avanzadas con documentación limitada en español. Configuración incorrecta puede generar resultados inválidos sin errores obvios.

- **Limitaciones de tiempo del equipo**: Proyecto académico con 2 desarrolladores part-time. Implementación de Pipeline B (LLM) puede consumir tiempo asignado a análisis de resultados, comprometiendo calidad de la tesis.

### Riesgos de Proyecto

Estos riesgos corresponden a factores externos o limitaciones generales que pueden afectar el cumplimiento de objetivos académicos.

#### Recursos Computacionales Limitados:

- **GPU insuficiente para LLM**: Gemma 3 4B y Llama 3 3B requieren 3-6 GB VRAM (con cuantización Q4). Laptops académicos con GPUs integradas pueden ser insuficientes. Alternativa de Google Colab tiene límites de tiempo de ejecución.

- **Almacenamiento limitado**: 600K ofertas con descripción completa + embeddings + clústeres puede requerir >50GB. Servidores universitarios con cuotas de almacenamiento pueden limitar corpus procesable.

- **Tiempo de cómputo para experimentos**: Cada iteración de ajuste de parámetros (ej. HDBSCAN min_cluster_size 30→50) requiere re-ejecutar clustering completo (minutos/horas). Exploraciones extensivas de hiperparámetros pueden ser inviables.

#### Acceso a Datos:

- **Bloqueo de IPs por portales**: Scraping agresivo puede resultar en bloqueo permanente de IPs universitarias. Requiere proxies rotacionales (costo) o scraping throttled (meses de recolección).

- **Cambios legales en protección de datos**: Regulaciones futuras (ej. GDPR-like en LatAm) pueden prohibir scraping de ofertas laborales. Impacta viabilidad de recolección continua de datos.

- **Desaparición de portales minoritarios**: Portales pequeños pueden cerrar operaciones (ej. ZonaJobs solo tiene 1 oferta scraped). Impacta cobertura geográfica del análisis.

#### Limitaciones de Alcance Académico:

- **Imposibilidad de validar con usuarios reales**: Sistema académico no tiene acceso a reclutadores o candidatos para validar utilidad práctica de insights generados. Evaluación limitada a métricas técnicas.

- **Horizonte temporal limitado**: Tesis debe completarse en 6-12 meses. Análisis de tendencias temporales idealmente requiere múltiples años de datos. Corpus actual cubre solo marzo-diciembre 2024.

- **Restricciones de publicación académica**: Implementación de componentes innovadores (ej. fine-tuning de modelos) puede ser necesaria para publicación en conferencias top-tier, pero excede alcance de tesis de pregrado.

---

## Restricciones

Estas son limitaciones específicas que afectan la capacidad del sistema para cumplir con ciertos requisitos o estándares, y deben ser consideradas durante el desarrollo y evaluación.

### 1. Restricciones Computacionales

**Hardware disponible:**
- Servidores universitarios con CPU Intel Xeon (16 cores) / AMD Ryzen (8 cores)
- RAM: 16-32 GB (compartida con otros procesos)
- GPU: NVIDIA GTX 1660 / RTX 3060 (6-12 GB VRAM) o Apple MPS
- Almacenamiento: 100-200 GB cuota en servidores universitarios

**Implicaciones:**
- LLMs limitados a modelos <4B parámetros con cuantización Q4
- Procesamiento batch preferido sobre tiempo real
- FAISS en modo CPU (suficiente para 14K vectores)
- Imposibilidad de usar modelos grandes (GPT-4, Llama 70B)

### 2. Restricciones de Tiempo

**Cronograma académico:**
- Tesis de pregrado: 6-12 meses (2 semestres)
- Tiempo efectivo de desarrollo: ~4-6 meses (clases + otras asignaturas)
- Deadline inflexible para defensa de grado

**Implicaciones:**
- Priorización de Pipeline A (tradicional) sobre Pipeline B (experimental)
- Exploraciones de hiperparámetros limitadas (no exhaustivas)
- Validación cualitativa sobre subconjunto representativo (no todo el corpus)
- Implementación incremental con entregas funcionales iterativas

### 3. Restricciones de Datos

**Acceso a portales:**
- Scraping sujeto a términos de servicio de portales
- Rate limiting: 1-2 requests/segundo por portal
- Bloqueo de IPs ante comportamiento sospechoso
- Contenido JavaScript requiere Selenium (más lento)

**Cobertura temporal:**
- Dataset actual: marzo-diciembre 2024 (9 meses)
- Análisis de tendencias de largo plazo limitado
- Imposibilidad de comparar con años anteriores (datos históricos no disponibles)

**Idioma:**
- Ofertas en español (España + LatAm) y Spanglish técnico
- Modelos NLP optimizados para español de España
- Escasa literatura sobre NLP para español técnico latinoamericano

### 4. Cumplimiento Normativo

**Protección de datos:**
- Ley 1581 de 2012 (Colombia) - Tratamiento de datos personales
- Ley Federal de Protección de Datos Personales (México)
- Ley 25.326 (Argentina) - Protección de Datos Personales

**Medidas implementadas:**
- Anonimización de datos: No se almacenan emails, teléfonos, nombres de candidatos
- Datos scrapeados son públicos (ofertas laborales visibles sin login)
- Uso exclusivo con fines académicos e investigación
- No comercialización de datos recolectados
- Eliminación de información sensible (salarios detallados)

### 5. Restricciones de Taxonomías

**ESCO v1.1.0:**
- Versión desactualizada (2016-2017)
- Enfoque europeo (menor cobertura de tech LatAm)
- No incluye frameworks modernos (Next.js, Remix, SolidJS)
- Actualizaciones oficiales lentas (años)

**Mitigación:**
- Expansión manual con 152 O*NET + 83 curated skills
- Skills emergentes catalogadas para futura integración
- Análisis cualitativo de skills no matched

### 6. Restricciones de Evaluación

**Gold Standard:**
- Presupuesto limitado para anotadores profesionales
- Anotación manual limitada a 300 ofertas (1.3% del corpus)
- Anotadores: estudiantes de ingeniería (no expertos en RRHH)
- Sesgo potencial hacia perfiles técnicos conocidos

**Validación de clustering:**
- No existen ground truth labels para clústeres de skills
- Evaluación cualitativa subjetiva
- Métricas intrínsecas (silhouette, DBCV) solo aproximadas

### 7. Restricciones de Publicación Académica

**Requisitos universitarios:**
- Documento de tesis debe seguir formato institucional (LaTeX PUJ)
- Extensión limitada: 80-120 páginas
- No se puede publicar código con licencias restrictivas
- Resultados deben ser originales (no publicados previamente)

**Implicaciones:**
- Documentación técnica detallada en repositorio GitHub
- Código abierto con licencia MIT
- Publicación en conferencias académicas después de defensa de grado

---

## Referencias

- Bass, L., Clements, P., & Kazman, R. (2021). *Software Architecture in Practice* (4th ed.). Addison-Wesley Professional.

- Campello, R. J., Moulavi, D., & Sander, J. (2013). Density-based clustering based on hierarchical density estimates. In *Pacific-Asia Conference on Knowledge Discovery and Data Mining* (pp. 160-172). Springer.

- Decorte, J. J., Verstijnen, E., & De Neve, W. (2021). *ESCO: Towards a semantic web approach to skills and competences for the European labour market*. In European Skills, Competences, Qualifications and Occupations (ESCO) Handbook v1.1.0. European Commission.

- Johnson, J., Douze, M., & Jégou, H. (2019). Billion-scale similarity search with GPUs. *IEEE Transactions on Big Data*, 7(3), 535-547.

- McInnes, L., Healy, J., & Melville, J. (2018). UMAP: Uniform manifold approximation and projection for dimension reduction. *arXiv preprint arXiv:1802.03426*.

- Richards, M., & Ford, N. (2023). *Fundamentals of Software Architecture: An Engineering Approach* (2nd ed.). O'Reilly Media, Inc.

- Reimers, N., & Gurevych, I. (2019). Sentence-BERT: Sentence embeddings using Siamese BERT-networks. In *Proceedings of the 2019 Conference on Empirical Methods in Natural Language Processing* (pp. 3982-3992).

- Wang, L., Yang, N., Huang, X., Jiao, B., Yang, L., Jiang, D., ... & Wei, F. (2024). Text embeddings by weakly-supervised contrastive pre-training. *arXiv preprint arXiv:2212.03533*.

- Zhang, Y., Yang, J., & Chen, W. (2023). *State of the Art in NLP for Low-Resource Languages: A Survey*. arXiv preprint arXiv:2301.00123.

- ISO/IEC 25010:2011. (2011). *Systems and software engineering — Systems and software Quality Requirements and Evaluation (SQuaRE) — System and software quality models*. International Organization for Standardization.

- Richards, M. (2015). *Software Architecture Patterns*. O'Reilly Media, Inc.

---

**Fin del Documento SAD**

**Código del Proyecto:** CIS2025CP08
**Versión del Documento:** 1.0
**Fecha de Creación:** Enero 2025
**Pontificia Universidad Javeriana - Facultad de Ingeniería**
