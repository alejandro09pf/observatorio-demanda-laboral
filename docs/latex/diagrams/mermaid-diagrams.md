# Diagramas Mermaid para el Observatorio de Demanda Laboral

Estos diagramas pueden ser generados en: https://mermaid.live/

## 1. Arquitectura del Pipeline (Vertical)

```mermaid
flowchart TD
    A[Portales de Empleo<br/>Computrabajo, Bumeran, ElEmpleo] --> B

    B[1. Web Scraper<br/>Scrapy + Selenium] --> C[(PostgreSQL<br/>raw_jobs)]
    C --> D[2. Skill Extractor<br/>NER + Regex + ESCO]

    D --> E[(PostgreSQL<br/>extracted_skills)]
    E --> F[3. LLM Processor<br/>Mistral 7B / LLaMA 3]

    F --> G[(PostgreSQL<br/>enhanced_skills)]
    G --> H[4. Embedding Generator<br/>E5 Multilingual]

    H --> I[(PostgreSQL + pgvector<br/>skill_embeddings)]
    I --> J[5. Analyzer<br/>UMAP + HDBSCAN]

    J --> K[(PostgreSQL<br/>analysis_results)]
    K --> L[Reportes Finales<br/>PDF / PNG / CSV]

    style A fill:#fff4e6
    style B fill:#cce5ff
    style D fill:#cce5ff
    style F fill:#cce5ff
    style H fill:#cce5ff
    style J fill:#cce5ff
    style C fill:#d4edda
    style E fill:#d4edda
    style G fill:#d4edda
    style I fill:#d4edda
    style K fill:#d4edda
    style L fill:#ffe6cc
```

## 2. Arquitectura con Capas (Horizontal)

```mermaid
flowchart LR
    subgraph Input["Entrada de Datos"]
        P[Portales Web]
    end

    subgraph Processing["Capa de Procesamiento"]
        S[Scraper]
        E[Extractor]
        L[LLM]
        EM[Embedder]
        A[Analyzer]
    end

    subgraph Storage["Capa de Almacenamiento"]
        DB1[(raw_jobs)]
        DB2[(extracted_skills)]
        DB3[(enhanced_skills)]
        DB4[(skill_embeddings)]
        DB5[(analysis_results)]
    end

    subgraph Output["Salida"]
        R[Reportes]
    end

    P --> S
    S --> DB1
    DB1 --> E
    E --> DB2
    DB2 --> L
    L --> DB3
    DB3 --> EM
    EM --> DB4
    DB4 --> A
    A --> DB5
    DB5 --> R

    style Input fill:#fff4e6
    style Processing fill:#cce5ff
    style Storage fill:#d4edda
    style Output fill:#ffe6cc
```

## 3. Flujo de Datos Detallado

```mermaid
sequenceDiagram
    actor User as Usuario
    participant Orch as Orchestrator
    participant Scraper
    participant DB as PostgreSQL
    participant Extractor
    participant LLM
    participant Embedder
    participant Analyzer

    User->>Orch: start-automation
    activate Orch

    Orch->>Scraper: run spider CO
    activate Scraper
    Scraper->>Scraper: Scrapea portales
    Scraper->>DB: INSERT raw_jobs
    deactivate Scraper

    Orch->>Extractor: process-jobs
    activate Extractor
    Extractor->>DB: SELECT raw_jobs
    Extractor->>Extractor: NER + Regex + ESCO
    Extractor->>DB: INSERT extracted_skills
    deactivate Extractor

    Orch->>LLM: enhance-skills
    activate LLM
    LLM->>DB: SELECT extracted_skills
    LLM->>LLM: Normalizar + Inferir
    LLM->>DB: INSERT enhanced_skills
    deactivate LLM

    Orch->>Embedder: generate-embeddings
    activate Embedder
    Embedder->>DB: SELECT enhanced_skills
    Embedder->>Embedder: E5 Model (768D)
    Embedder->>DB: INSERT skill_embeddings
    deactivate Embedder

    Orch->>Analyzer: run-clustering
    activate Analyzer
    Analyzer->>DB: SELECT skill_embeddings
    Analyzer->>Analyzer: UMAP + HDBSCAN
    Analyzer->>DB: INSERT analysis_results
    Analyzer->>Analyzer: Generate reports
    deactivate Analyzer

    Analyzer-->>User: PDF/PNG/CSV
    deactivate Orch
```

## 4. Arquitectura de Módulos (Componentes)

```mermaid
---
config:
  theme: mc
---
C4Context
    title Arquitectura de Componentes del Observatorio
    Person(user, "Investigador", "Usuario del sistema")
    System_Ext(portals, "Portales de Empleo", "Computrabajo, Bumeran")
    System_Ext(esco, "ESCO API", "Taxonomía de skills")
    System_Boundary(obs, "Observatorio de Demanda Laboral") {
        Container(orch, "Orchestrator CLI", "Python/Typer", "Controla el pipeline")
        ContainerDb(db, "PostgreSQL", "PostgreSQL 15+", "Almacena datos")
        Container(scraper, "Web Scraper", "Scrapy", "Recolecta ofertas")
        Container(extractor, "Extractor", "spaCy/Regex", "Extrae habilidades")
        Container(llm, "LLM Processor", "Mistral/LLaMA", "Enriquece datos")
        Container(embedder, "Embedder", "E5 Model", "Genera vectores")
        Container(analyzer, "Analyzer", "UMAP/HDBSCAN", "Agrupa skills")
    }
```

## 5. Diagrama de Secuencia (Flujo Completo)

```mermaid
sequenceDiagram
    actor User as Usuario
    participant Orch as Orchestrator
    participant Scraper
    participant DB as PostgreSQL
    participant Extractor
    participant LLM
    participant Embedder
    participant Analyzer

    User->>Orch: start-automation
    activate Orch

    Orch->>Scraper: run spider CO
    activate Scraper
    Scraper->>Scraper: Scrapea portales
    Scraper->>DB: INSERT raw_jobs
    deactivate Scraper

    Orch->>Extractor: process-jobs
    activate Extractor
    Extractor->>DB: SELECT raw_jobs
    Extractor->>Extractor: NER + Regex + ESCO
    Extractor->>DB: INSERT extracted_skills
    deactivate Extractor

    Orch->>LLM: enhance-skills
    activate LLM
    LLM->>DB: SELECT extracted_skills
    LLM->>LLM: Normalizar + Inferir
    LLM->>DB: INSERT enhanced_skills
    deactivate LLM

    Orch->>Embedder: generate-embeddings
    activate Embedder
    Embedder->>DB: SELECT enhanced_skills
    Embedder->>Embedder: E5 Model (768D)
    Embedder->>DB: INSERT skill_embeddings
    deactivate Embedder

    Orch->>Analyzer: run-clustering
    activate Analyzer
    Analyzer->>DB: SELECT skill_embeddings
    Analyzer->>Analyzer: UMAP + HDBSCAN
    Analyzer->>DB: INSERT analysis_results
    Analyzer->>Analyzer: Generate reports
    deactivate Analyzer

    Analyzer-->>User: PDF/PNG/CSV
    deactivate Orch
```

## 6. Diagrama de Estados del Job

```mermaid
stateDiagram-v2
    [*] --> Scraped: Web Scraping
    Scraped --> Extracted: Skill Extraction
    Extracted --> Enhanced: LLM Processing
    Enhanced --> Vectorized: Embedding Generation
    Vectorized --> Analyzed: Clustering
    Analyzed --> Reported: Report Generation
    Reported --> [*]

    Scraped --> Failed: Error
    Extracted --> Failed: Error
    Enhanced --> Failed: Error
    Vectorized --> Failed: Error
    Analyzed --> Failed: Error

    Failed --> Scraped: Retry
```

## 7. Diagrama ER Simplificado

```mermaid
erDiagram
    RAW_JOBS ||--o{ EXTRACTED_SKILLS : contains
    RAW_JOBS ||--o{ ENHANCED_SKILLS : contains
    EXTRACTED_SKILLS ||--o{ ENHANCED_SKILLS : enriches
    ENHANCED_SKILLS ||--o{ SKILL_EMBEDDINGS : generates
    SKILL_EMBEDDINGS ||--o{ ANALYSIS_RESULTS : clusters
    ESCO_SKILLS ||--o{ EXTRACTED_SKILLS : maps_to
    ESCO_SKILLS ||--o{ ENHANCED_SKILLS : normalizes

    RAW_JOBS {
        uuid job_id PK
        string portal
        string country
        text description
        timestamp scraped_at
    }

    EXTRACTED_SKILLS {
        uuid extraction_id PK
        uuid job_id FK
        text skill_text
        string extraction_method
        text esco_uri
    }

    ENHANCED_SKILLS {
        uuid enhancement_id PK
        uuid job_id FK
        text normalized_skill
        text esco_concept_uri
        float llm_confidence
    }

    SKILL_EMBEDDINGS {
        uuid embedding_id PK
        text skill_text
        vector embedding
        string model_name
    }

    ANALYSIS_RESULTS {
        uuid analysis_id PK
        string analysis_type
        jsonb results
    }

    ESCO_SKILLS {
        text esco_uri PK
        text preferred_label_es
        text skill_type
    }
```

## Instrucciones de Uso

### Para generar imágenes:

1. Ve a https://mermaid.live/
2. Copia y pega el código de cualquier diagrama
3. Ajusta colores y estilos si deseas
4. Exporta como PNG o SVG (alta resolución)
5. Incluye la imagen en LaTeX con:

```latex
\begin{figure}[H]
\centering
\includegraphics[width=0.8\textwidth]{diagrams/pipeline-mermaid.png}
\caption{Arquitectura del Pipeline}
\label{fig:pipeline-mermaid}
\end{figure}
```

### Recomendaciones:

- **Diagrama 1** es el más completo y recomendado para la sección de arquitectura
- **Diagrama 3** es excelente para explicar el flujo detallado
- **Diagrama 5** es perfecto para mostrar la secuencia temporal
- **Diagrama 7** es ideal para documentar la base de datos

### Alternativas online:

- https://mermaid.live/ (oficial)
- https://mermaid.ink/ (API para generar URLs)
- VS Code con extensión "Mermaid Preview"
