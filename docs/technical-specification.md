# Master Technical Specification
## Automated Labor Market Observatory for Latin America
### Complete Implementation Blueprint

**Version:** 1.0  
**Date:** January 2025  
**Team Size:** 2 developers  
**Target OS:** Windows (primary), macOS (secondary)  
**Database:** PostgreSQL 15+ with pgvector  
**Taxonomy:** ESCO (European Skills, Competences, Qualifications and Occupations)  

---

## Table of Contents
1. [System Overview](#1-system-overview)
2. [Architecture Design](#2-architecture-design)
3. [Technology Stack](#3-technology-stack)
4. [Module Specifications](#4-module-specifications)
5. [Database Design](#5-database-design)
6. [API Specifications](#6-api-specifications)
7. [Data Flow Formats](#7-data-flow-formats)
8. [Evaluation Metrics](#8-evaluation-metrics)
9. [Project Structure](#9-project-structure)

---

## 1. System Overview

### 1.1 Linear Pipeline Architecture

```
┌─────────────────────┐
│   Job Portals       │
│ (Computrabajo, etc) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────┐
│  Module 1: Scraper  │────▶│   PostgreSQL    │
│  Scrapy + Parsing   │     │   Raw Jobs DB   │
└─────────────────────┘     └─────────────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────┐
│ Module 2: Extractor │────▶│   PostgreSQL    │
│  NER + Regex + ESCO │     │ Initial Skills  │
└─────────────────────┘     └─────────────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────┐
│  Module 3: LLM      │────▶│   PostgreSQL    │
│ Dedup + Implicit +  │     │ Enhanced Skills │
│    Normalize        │     └─────────────────┘
└─────────────────────┘
           │
           ▼
┌─────────────────────┐     ┌─────────────────┐
│ Module 4: Embedder  │────▶│   PostgreSQL    │
│ Vectorization with  │     │ Skill Vectors   │
│    E5/SBERT         │     │   (pgvector)    │
└─────────────────────┘     └─────────────────┘
           │
           ▼
┌─────────────────────┐     
│ Module 5: Analyzer  │
│  UMAP + HDBSCAN +   │
│ Static Visualization│
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│   Output: Reports   │
│   PDF/PNG/CSV       │
└─────────────────────┘
```

### 1.2 Key Design Decisions

| Component | Decision | Rationale |
|-----------|----------|-----------|
| Database | PostgreSQL 15 | Free, JSON support, pgvector for embeddings |
| Taxonomy | ESCO v1.1.0 | Superior Spanish support, comprehensive tech skills |
| Scraping | Scrapy 2.11 | Async, robust, extensible |
| NER | spaCy 3.7 | Best Spanish models |
| LLM | Mistral 7B / LLaMA 3 | Local execution, good Spanish performance |
| Embeddings | multilingual-e5-base | Best multilingual quality |
| Clustering | HDBSCAN | Handles varying densities |
| Visualization | Matplotlib + ReportLab | Static outputs only |

---

## 2. Architecture Design

### 2.1 Execution Flow

1. **Orchestrator** triggers scraping jobs by country/portal
2. **Scraper** fetches and parses job postings → stores in `raw_jobs` table
3. **Extractor** processes each job with NER + regex → stores in `extracted_skills` table
4. **LLM Processor** enhances skills → stores in `enhanced_skills` table
5. **Embedder** vectorizes skills → stores in `skill_embeddings` table
6. **Analyzer** clusters and generates reports → saves to `outputs/` directory

### 2.2 Module Communication

All modules communicate through PostgreSQL database and filesystem:
- **Database**: Central data store with defined schemas
- **Filesystem**: Configuration files, temporary data, final outputs
- **No direct API calls between modules** (simplifies architecture)

---

## 3. Technology Stack

### 3.1 Core Dependencies

```yaml
# Python version
python: 3.10.11 (minimum 3.10)

# Data Processing
scrapy: 2.11.0
beautifulsoup4: 4.12.2
lxml: 4.9.3
pandas: 2.1.4
numpy: 1.24.3

# NLP
spacy: 3.7.2
spacy-model-es_core_news_lg: 3.7.0
transformers: 4.36.2
sentence-transformers: 2.2.2
langdetect: 1.0.9

# Database
psycopg2-binary: 2.9.9
sqlalchemy: 2.0.23
pgvector: 0.2.3

# ML/Clustering
scikit-learn: 1.3.2
umap-learn: 0.5.5
hdbscan: 0.8.33

# LLM
llama-cpp-python: 0.2.32  # For local LLM
openai: 1.6.1  # Optional fallback

# Visualization
matplotlib: 3.8.2
seaborn: 0.13.0
reportlab: 4.0.8
plotly: 5.18.0  # For static exports only

# Utilities
python-dotenv: 1.0.0
pydantic: 2.5.3
typer: 0.9.0  # CLI
tqdm: 4.66.1
requests: 2.31.0
fake-useragent: 1.4.0
```

### 3.2 ESCO Integration

```yaml
# ESCO API Configuration
esco_version: 1.1.0
esco_endpoint: https://ec.europa.eu/esco/api
languages: ['es', 'en']  # Spanish primary, English fallback
skill_types: ['skill/competence', 'knowledge']
```

---

## 4. Module Specifications

### 4.1 Module 1: Web Scraper

**Purpose**: Extract job postings from Latin American portals with integrated parsing

**Files**:
- `scraper/spiders/computrabajo_spider.py`
- `scraper/spiders/bumeran_spider.py`
- `scraper/spiders/elempleo_spider.py`
- `scraper/items.py`
- `scraper/pipelines.py`
- `scraper/settings.py`

**Key Features**:
- Concurrent scraping with rate limiting
- Automatic retry with exponential backoff
- User-agent rotation
- Integrated parsing to structured format
- Duplicate detection via content hash

**Database Output**: `raw_jobs` table

---

### 4.2 Module 2: Skill Extractor

**Purpose**: Extract explicit skills using NER, regex, and ESCO taxonomy

**Files**:
- `extractor/ner_extractor.py`
- `extractor/regex_patterns.py`
- `extractor/esco_matcher.py`
- `extractor/pipeline.py`

**Process**:
1. Load spaCy Spanish model
2. Apply custom NER for tech entities
3. Run regex patterns on key sections
4. Match against ESCO taxonomy
5. Store initial skill list

**Database Output**: `extracted_skills` table

---

### 4.3 Module 3: LLM Processor

**Purpose**: Deduplicate, infer implicit skills, and normalize using ESCO

**Files**:
- `llm_processor/llm_handler.py`
- `llm_processor/prompts.py`
- `llm_processor/esco_normalizer.py`
- `llm_processor/validator.py`

**Key Innovation**:
- Custom prompts for Spanish tech context
- ESCO-guided normalization
- Implicit skill inference
- Confidence scoring

**Database Output**: `enhanced_skills` table

---

### 4.4 Module 4: Embedding Generator

**Purpose**: Create semantic vectors for skills and job profiles

**Files**:
- `embedder/vectorizer.py`
- `embedder/model_loader.py`
- `embedder/batch_processor.py`

**Models**:
- Primary: `intfloat/multilingual-e5-base`
- Fallback: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

**Database Output**: `skill_embeddings` table (using pgvector)

---

### 4.5 Module 5: Analysis & Visualization

**Purpose**: Cluster skills and generate static reports

**Files**:
- `analyzer/clustering.py`
- `analyzer/dimension_reducer.py`
- `analyzer/report_generator.py`
- `analyzer/visualizations.py`

**Outputs**:
- PDF reports with charts
- PNG visualizations
- CSV data exports

---

## 5. Database Design

### 5.1 Schema Overview

```sql
-- Main database
CREATE DATABASE labor_observatory
  WITH ENCODING 'UTF8'
  LC_COLLATE = 'en_US.UTF-8'
  LC_CTYPE = 'en_US.UTF-8';

-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
```

### 5.2 Tables Structure

#### raw_jobs
```sql
CREATE TABLE raw_jobs (
    job_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    portal VARCHAR(50) NOT NULL,
    country CHAR(2) NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT,
    location TEXT,
    description TEXT NOT NULL,
    requirements TEXT,
    salary_raw TEXT,
    contract_type VARCHAR(50),
    remote_type VARCHAR(50),
    posted_date DATE,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    content_hash VARCHAR(64) UNIQUE,
    raw_html TEXT,
    is_processed BOOLEAN DEFAULT FALSE,
    
    INDEX idx_portal_country (portal, country),
    INDEX idx_scraped_at (scraped_at),
    INDEX idx_processed (is_processed)
);
```

#### extracted_skills
```sql
CREATE TABLE extracted_skills (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id),
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(50), -- 'explicit', 'regex_match'
    extraction_method VARCHAR(50), -- 'ner', 'regex', 'esco_match'
    confidence_score FLOAT,
    source_section VARCHAR(50), -- 'title', 'description', 'requirements'
    span_start INTEGER,
    span_end INTEGER,
    esco_uri TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_job_skills (job_id),
    INDEX idx_skill_text (skill_text)
);
```

#### enhanced_skills
```sql
CREATE TABLE enhanced_skills (
    enhancement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id),
    original_skill_text TEXT,
    normalized_skill TEXT NOT NULL,
    skill_type VARCHAR(50), -- 'explicit', 'implicit', 'normalized'
    esco_concept_uri TEXT,
    esco_preferred_label TEXT,
    llm_confidence FLOAT,
    llm_reasoning TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID,
    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model VARCHAR(100),
    
    INDEX idx_job_enhanced (job_id),
    INDEX idx_normalized (normalized_skill)
);
```

#### skill_embeddings
```sql
CREATE TABLE skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT UNIQUE NOT NULL,
    embedding vector(768) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_skill_lookup (skill_text)
);

-- Create vector similarity index
CREATE INDEX ON skill_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### analysis_results
```sql
CREATE TABLE analysis_results (
    analysis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_type VARCHAR(50), -- 'clustering', 'trends', 'profile'
    country CHAR(2),
    date_range_start DATE,
    date_range_end DATE,
    parameters JSONB,
    results JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_analysis_type (analysis_type),
    INDEX idx_analysis_date (created_at)
);
```

---

## 6. API Specifications

### 6.1 Internal Module APIs

Since modules communicate via database, we define internal Python interfaces:

```python
# Base module interface
class BaseModule(ABC):
    @abstractmethod
    def process(self, batch_size: int = 100) -> ProcessResult:
        pass
    
    @abstractmethod
    def validate_input(self) -> bool:
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        pass
```

### 6.2 Orchestrator Commands

```bash
# CLI commands (using Typer)
python orchestrator.py scrape --country CO --portal computrabajo
python orchestrator.py extract --batch-size 100
python orchestrator.py enhance --llm-model mistral-7b
python orchestrator.py embed --model e5-multilingual
python orchestrator.py analyze --method hdbscan
python orchestrator.py report --format pdf --output-dir outputs/
```

---

## 7. Data Flow Formats

### 7.1 Module 1 Output (Scraper → Database)

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "portal": "computrabajo",
  "country": "CO",
  "url": "https://www.computrabajo.com.co/ofertas/12345",
  "title": "Desarrollador Full Stack Senior",
  "company": "TechCorp Colombia SAS",
  "location": "Bogotá, Colombia",
  "description": "Buscamos un desarrollador full stack con experiencia...",
  "requirements": "- 5 años de experiencia en desarrollo web\n- Dominio de React y Node.js\n- Conocimientos en AWS",
  "salary_raw": "$6.000.000 - $8.000.000 COP",
  "contract_type": "Tiempo completo",
  "remote_type": "Híbrido",
  "posted_date": "2025-01-15",
  "scraped_at": "2025-01-20T10:30:00Z",
  "content_hash": "a8f5f167f4e7c41e489e2f95a87c3e5d"
}
```

### 7.2 Module 2 Output (Extractor → Database)

```json
{
  "extraction_id": "660e8400-e29b-41d4-a716-446655440001",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "extracted_skills": [
    {
      "skill_text": "React",
      "skill_type": "explicit",
      "extraction_method": "ner",
      "confidence_score": 0.95,
      "source_section": "requirements",
      "span_start": 156,
      "span_end": 161,
      "esco_uri": "http://data.europa.eu/esco/skill/123"
    },
    {
      "skill_text": "Node.js",
      "skill_type": "explicit",
      "extraction_method": "regex",
      "confidence_score": 0.90,
      "source_section": "requirements",
      "span_start": 164,
      "span_end": 171,
      "esco_uri": "http://data.europa.eu/esco/skill/456"
    }
  ]
}
```

### 7.3 Module 3 Output (LLM → Database)

```json
{
  "enhancement_id": "770e8400-e29b-41d4-a716-446655440002",
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "enhanced_skills": [
    {
      "original_skill_text": "React",
      "normalized_skill": "React.js",
      "skill_type": "explicit",
      "esco_concept_uri": "http://data.europa.eu/esco/skill/123",
      "esco_preferred_label": "React.js framework",
      "llm_confidence": 0.98,
      "is_duplicate": false
    },
    {
      "original_skill_text": null,
      "normalized_skill": "Git",
      "skill_type": "implicit",
      "esco_concept_uri": "http://data.europa.eu/esco/skill/789",
      "esco_preferred_label": "use version control system Git",
      "llm_confidence": 0.85,
      "llm_reasoning": "Full stack development with team collaboration implies Git usage",
      "is_duplicate": false
    }
  ],
  "llm_model": "mistral-7b-instruct",
  "processing_time_ms": 1250
}
```

### 7.4 Module 4 Output (Embedder → Database)

```json
{
  "embedding_id": "880e8400-e29b-41d4-a716-446655440003",
  "skill_text": "React.js",
  "embedding": "[0.0234, -0.1523, 0.0891, ...]",  // 768-dimensional vector
  "model_name": "intfloat/multilingual-e5-base",
  "model_version": "1.0.0",
  "processing_batch": 1,
  "created_at": "2025-01-20T11:00:00Z"
}
```

### 7.5 Module 5 Output (Analysis → Files)

```json
{
  "analysis_id": "990e8400-e29b-41d4-a716-446655440004",
  "analysis_type": "clustering",
  "parameters": {
    "algorithm": "hdbscan",
    "min_cluster_size": 5,
    "min_samples": 3,
    "metric": "euclidean"
  },
  "results": {
    "n_clusters": 12,
    "clusters": [
      {
        "cluster_id": 0,
        "label": "Frontend Development",
        "size": 145,
        "top_skills": ["React.js", "Vue.js", "CSS", "JavaScript", "HTML5"],
        "countries": {"CO": 65, "MX": 50, "AR": 30}
      }
    ],
    "noise_points": 23,
    "silhouette_score": 0.68
  },
  "output_files": [
    "outputs/2025-01-20/cluster_report.pdf",
    "outputs/2025-01-20/skill_distribution.png",
    "outputs/2025-01-20/raw_data.csv"
  ]
}
```

---

## 8. Evaluation Metrics

### 8.1 Module-Level Metrics

#### Scraper Metrics
- **Success Rate**: (successful_requests / total_requests) × 100
- **Parse Rate**: (parsed_jobs / scraped_pages) × 100
- **Duplicate Rate**: (duplicate_jobs / total_jobs) × 100
- **Coverage**: unique_jobs per portal per country

#### Extractor Metrics
- **Extraction Precision**: validated_skills / extracted_skills
- **Extraction Recall**: extracted_skills / annotated_skills
- **F1 Score**: 2 × (precision × recall) / (precision + recall)
- **ESCO Match Rate**: esco_matched_skills / total_skills

#### LLM Processor Metrics
- **Deduplication Rate**: deduplicated_skills / total_input_skills
- **Implicit Skill Discovery**: implicit_skills / total_enhanced_skills
- **Normalization Success**: normalized_with_esco / total_skills
- **Processing Time**: avg_time_per_job

#### Clustering Metrics
- **Silhouette Score**: cluster cohesion and separation
- **Davies-Bouldin Index**: cluster validity
- **Cluster Stability**: consistency across runs
- **Coverage**: jobs_in_clusters / total_jobs

### 8.2 System-Level Metrics

```python
# Metrics collection
metrics = {
    "pipeline_metrics": {
        "total_jobs_processed": 10000,
        "total_skills_extracted": 45000,
        "unique_skills_identified": 1200,
        "processing_time_hours": 24.5,
        "success_rate": 0.97
    },
    "quality_metrics": {
        "skill_extraction_f1": 0.82,
        "llm_enhancement_coverage": 0.91,
        "clustering_silhouette": 0.68,
        "esco_mapping_rate": 0.76
    },
    "performance_metrics": {
        "jobs_per_hour": 400,
        "avg_extraction_time_ms": 150,
        "avg_llm_time_ms": 1200,
        "avg_embedding_time_ms": 50
    }
}
```

---

## 9. Project Structure

### 9.1 Complete Directory Structure

```
labor-observatory/
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── requirements.txt
├── setup.py
├── docker-compose.yml
│
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   ├── logging_config.py
│   └── esco_config.yaml
│
├── src/
│   ├── __init__.py
│   │
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── scrapy.cfg
│   │   ├── items.py
│   │   ├── pipelines.py
│   │   ├── settings.py
│   │   ├── middlewares.py
│   │   └── spiders/
│   │       ├── __init__.py
│   │       ├── base_spider.py
│   │       ├── computrabajo_spider.py
│   │       ├── bumeran_spider.py
│   │       └── elempleo_spider.py
│   │
│   ├── extractor/
│   │   ├── __init__.py
│   │   ├── ner_extractor.py
│   │   ├── regex_patterns.py
│   │   ├── esco_matcher.py
│   │   ├── pipeline.py
│   │   └── models/
│   │       └── custom_ner_model/
│   │
│   ├── llm_processor/
│   │   ├── __init__.py
│   │   ├── llm_handler.py
│   │   ├── prompts.py
│   │   ├── esco_normalizer.py
│   │   ├── validator.py
│   │   └── models/
│   │       └── mistral-7b-gguf/
│   │
│   ├── embedder/
│   │   ├── __init__.py
│   │   ├── vectorizer.py
│   │   ├── model_loader.py
│   │   ├── batch_processor.py
│   │   └── cache/
│   │
│   ├── analyzer/
│   │   ├── __init__.py
│   │   ├── clustering.py
│   │   ├── dimension_reducer.py
│   │   ├── report_generator.py
│   │   ├── visualizations.py
│   │   └── templates/
│   │       └── report_template.html
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py
│   │   ├── operations.py
│   │   └── migrations/
│   │       └── 001_initial_schema.sql
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   ├── cleaners.py
│   │   ├── metrics.py
│   │   └── logger.py
│   │
│   └── orchestrator.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_scraper.py
│   ├── test_extractor.py
│   ├── test_llm_processor.py
│   ├── test_embedder.py
│   ├── test_analyzer.py
│   └── fixtures/
│       └── sample_data.json
│
├── scripts/
│   ├── setup_database.py
│   ├── download_models.py
│   ├── validate_esco.py
│   └── run_pipeline.py
│
├── data/
│   ├── esco/
│   │   ├── skills_es.csv
│   │   └── occupations_es.csv
│   ├── models/
│   │   ├── mistral-7b-instruct.Q4_K_M.gguf
│   │   └── multilingual-e5-base/
│   └── cache/
│
├── outputs/
│   └── 2025-01-20/
│       ├── analysis_report.pdf
│       ├── cluster_visualization.png
│       ├── skill_frequency.png
│       └── raw_results.csv
│
├── docs/
│   ├── architecture.md
│   ├── setup_guide.md
│   ├── api_reference.md
│   └── troubleshooting.md
│
└── notebooks/
    ├── 01_exploratory_analysis.ipynb
    ├── 02_llm_prompt_testing.ipynb
    └── 03_visualization_experiments.ipynb
```

### 9.2 Git Workflow

```bash
# Branch structure
main
├── develop
│   ├── feature/scraper-module
│   ├── feature/ner-extraction
│   ├── feature/llm-integration
│   ├── feature/clustering
│   └── feature/reporting
└── hotfix/critical-bug-fix

# Commit message format
<type>: <description>

# Types
feat: New feature
fix: Bug fix
docs: Documentation changes
test: Test additions or changes
refactor: Code refactoring
perf: Performance improvements
chore: Maintenance tasks

# Examples
feat: Add Computrabajo spider for Colombia
fix: Handle null salary fields in parser
docs: Update setup instructions for Windows
test: Add unit tests for ESCO matcher
```

---

**Next Documents**:
1. Complete Implementation Guide (with all production-ready code)
2. Development Environment Setup Guide (step-by-step)
3. Data Flow and Sample JSONs Reference

This master specification provides the complete technical blueprint. Should I proceed with creating the detailed implementation files and setup guides?