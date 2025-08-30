# 🚀 Labor Market Observatory for Latin America

> **An automated system for monitoring technical skill demands in Latin American labor markets using AI, NLP, and data analysis.**

## 🆕 **NEW DEVELOPER? READ THIS FIRST!**

**If you're new to this project, start with the [ONBOARDING GUIDE](docs/ONBOARDING_GUIDE.md) - it will tell you exactly what to do, where to find everything, and how to continue development.**

**For immediate guidance, see [QUICK_START.md](QUICK_START.md)**

**Current Status: ✅ Phases 1 & 2 Complete - Foundation & Database Working**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![Status: Development](https://img.shields.io/badge/Status-Development-orange.svg)](https://github.com/yourusername/observatorio-demanda-laboral)

## 📋 Table of Contents

- [🎯 Project Overview](#-project-overview)
- [🏗️ System Architecture](#️-system-architecture)
- [🚀 Quick Start](#-quick-start)
- [📚 Documentation](#-documentation)
- [🔧 Installation](#-installation)
- [💻 Usage Examples](#-usage-examples)
- [📊 Data Flow](#-data-flow)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

## 🎯 Project Overview

The **Labor Market Observatory** is an intelligent system designed to automatically monitor and analyze technical skill demands across Latin American countries. By scraping job postings, extracting skills using AI, and analyzing trends, it provides actionable insights into labor market dynamics.

### **What Problem Does This Solve?**

- **Skill Gap Analysis**: Identify which technical skills are most in demand
- **Geographic Insights**: Understand regional differences in skill requirements
- **Temporal Trends**: Track how skill demands evolve over time
- **Market Intelligence**: Provide data-driven insights for career planning and education

### **Target Countries**
- 🇨🇴 **Colombia** (CO)
- 🇲🇽 **México** (MX)  
- 🇦🇷 **Argentina** (AR)

### **Supported Job Portals**
- **Computrabajo** - Major Latin American job portal
- **Bumeran** - Popular in Mexico and Argentina
- **ElEmpleo** - Colombian job market specialist

## 🏗️ System Architecture

The system follows a **linear pipeline architecture** where each module processes data and passes it to the next:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Scraping  │───▶│  Skill Extraction│───▶│  LLM Processing │
│   (Scrapy)      │    │  (NER + Regex)  │    │  (Mistral 7B)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL DB  │    │  PostgreSQL DB  │    │  PostgreSQL DB  │
│   (Raw Jobs)    │    │ (Extracted Skills)│  │ (Enhanced Skills)│
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                                                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Embedding     │◀───│  PostgreSQL DB  │    │   Analysis &    │
│  Generation     │    │ (Enhanced Skills)│   │ Visualization   │
│ (E5 Multilingual)│   │                 │    │ (Clustering)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL DB  │    ┌─────────────────┐    │   Static Reports│
│ (Skill Vectors) │    │   Orchestrator  │    │ (PDF/PNG/CSV)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### **Core Components**

| Component | Purpose | Status | How to Use |
|-----------|---------|---------|------------|
| **Orchestrator** | Main CLI controller | ✅ Working | `python -m src.orchestrator` |
| **Intelligent Scheduler** | Auto-run spiders | ✅ Working | `start-automation` command |
| **Pipeline Automator** | Auto-process jobs | ✅ Working | Runs automatically |
| **Scrapy Spiders** | Extract job data | ✅ Working | `run` or `run-once` commands |
| **ESCO Taxonomy** | Skill classification | ✅ Working | 13,000+ skills loaded |
| **Skill Extraction** | NER + Regex | ✅ Working | Automatic pipeline |
| **Database** | PostgreSQL + pgvector | ✅ Working | 123+ jobs stored, 3 migrations applied |

## 🔄 Complete Pipeline Components

| Stage | Component | Status | Implementation | How to Use |
|-------|-----------|---------|----------------|------------|
| **1. Scraping** | Scrapy Spiders | ✅ **Complete** | All spiders working, anti-detection | `run-once` or `run` commands |
| **2. Extraction** | NER + Regex + ESCO | ✅ **Complete** | Automatic pipeline, 123+ jobs processed | `process-jobs` command |
| **3. LLM Processing** | Mistral 7B + OpenAI | 🔄 **In Development** | Framework ready, models pending | Not yet available |
| **4. Embedding** | E5 Multilingual | 🔄 **In Development** | Architecture ready, model loading pending | Not yet available |
| **5. Dimension Reduction** | UMAP | 🔄 **In Development** | Framework ready, implementation pending | Not yet available |
| **6. Clustering** | HDBSCAN | 🔄 **In Development** | Framework ready, algorithm pending | Not yet available |
| **7. Visualization** | Static Web Pages | 🔄 **In Development** | Framework ready, templates pending | Not yet available |
| **8. Reports** | PDF/PNG/CSV | 🔄 **In Development** | Framework ready, generation pending | Not yet available |

## 🔄 Complete Data Pipeline

Your system implements a **comprehensive 8-stage pipeline** for labor market analysis:

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    1.       │ │    2.       │ │    3.       │ │    4.       │
│  SCRAPING   │ │  EXTRACTION │ │    LLM      │ │  EMBEDDING  │
│             │ │             │ │ PROCESSING  │ │             │
│ • Scrapy    │ │ • NER       │ │ • Mistral   │ │ • E5 Model  │
│ • Selenium  │ │ • Regex     │ │ • OpenAI    │ │ • 768D      │
│ • Anti-det  │ │ • ESCO Map  │ │ • Normalize │ │ • Batch     │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
       │               │               │               │
       ▼               ▼               ▼               ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│    5.       │ │    6.       │ │    7.       │ │    8.       │
│ DIMENSION   │ │ CLUSTERING  │ │VISUALIZATION│ │   REPORTS   │
│ REDUCTION   │ │             │ │             │ │             │
│ • UMAP      │ │ • HDBSCAN   │ │ • Static    │ │ • PDF/PNG   │
│ • 2D/3D     │ │ • Skill     │ │ • Web Pages │ │ • CSV/JSON  │
│ • Preserve  │ │ • Groups    │ │ • Charts    │ │ • Insights  │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### **What's Actually Working Right Now**

✅ **Stages 1-2 Complete**: You can scrape jobs and extract skills automatically  
✅ **Database Ready**: All data structures in place for the full pipeline  
✅ **Database Schema**: 3 migrations applied (001, 004, 005)  
✅ **Automation Ready**: System can run 24/7 and process new jobs automatically  
✅ **ESCO Integration**: 13,000+ skills mapped and searchable  

### **What's Next to Implement**

🔄 **Stage 3**: LLM model loading and skill enhancement  
🔄 **Stage 4**: E5 embedding model integration  
🔄 **Stage 5**: UMAP dimension reduction  
🔄 **Stage 6**: HDBSCAN clustering algorithm  
🔄 **Stage 7**: Web visualization templates  
🔄 **Stage 8**: Report generation engine

## 🚀 Quick Start

### **Prerequisites**

- **Python 3.10+** with pip
- **PostgreSQL 15+** with pgvector extension
- **8GB+ RAM** (for LLM processing)
- **Git** for version control

### **1. Clone and Setup**

```bash
# Clone the repository
git clone https://github.com/yourusername/observatorio-demanda-laboral.git
cd observatorio-demanda-laboral

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### **2. Database Setup**

```bash
# Start PostgreSQL with Docker (recommended)
docker-compose up -d postgres

# Wait for database to be ready, then setup schema
python scripts/setup_database.py

# Import ESCO taxonomy (13,000+ skills)
python scripts/import_real_esco.py
```

**Alternative Manual Setup:**
```bash
# Install PostgreSQL extensions
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS pgvector;"

# Run all 3 migrations in order
psql -U postgres -f src/database/migrations/001_initial_schema.sql
psql -U postgres -f src/database/migrations/004_add_esco_taxonomy.sql
psql -U postgres -f src/database/migrations/005_fix_esco_function.sql

# Import ESCO taxonomy data
python scripts/import_real_esco.py
```

### **3. Environment Configuration**

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your database credentials and API keys
nano .env
```

### **4. Test the System**

```bash
# Check system status
python -m src.orchestrator status

# List available spiders
python -m src.orchestrator list-spiders

# Test a single spider
python -m src.orchestrator run-once bumeran CO --limit 5 --max-pages 2

# Check automation system
python -m src.orchestrator automation-status
```

## 💻 How to Use the System

### **Manual Spider Execution**

```bash
# Run a single spider once
python -m src.orchestrator run-once bumeran CO --limit 10 --max-pages 3

# Run multiple spiders
python -m src.orchestrator run "bumeran,computrabajo" CO --limit 50 --max-pages 5

# Run with specific parameters
python -m src.orchestrator run-once infojobs MX --limit 20 --max-pages 2
```

### **Automated System**

```bash
# Start the complete automation system
python -m src.orchestrator start-automation

# Check automation status
python -m src.orchestrator automation-status

# List scheduled jobs
python -m src.orchestrator list-jobs

# Check system health
python -m src.orchestrator health

# Force run a specific job
python -m src.orchestrator force-job bumeran_CO_cron
```

### **Pipeline Processing**

```bash
# Manually process pending jobs through the pipeline
python -m src.orchestrator process-jobs

# Check what's in the pipeline
python -m src.orchestrator status
```

## 📚 Documentation

### **🚀 NEW DEVELOPER? START HERE!**
- **[ONBOARDING GUIDE](docs/ONBOARDING_GUIDE.md)** ← **READ THIS FIRST!** - Complete guide for new developers

### **📋 Core Documentation**
- **[Master Technical Specification](docs/technical-specification.md)** - Complete system blueprint
- **[Complete Implementation Guide](docs/implementation-guide.md)** - All production-ready code
- **[Data Flow Reference](docs/data-flow-reference.md)** - Inter-module communication patterns
- **[Architecture Overview](docs/architecture.md)** - System design and components

### **API Reference**

- **[API Documentation](docs/api_reference.md)** - Function and module references
- **[Setup Guide](docs/setup_guide.md)** - Installation and configuration
- **[Troubleshooting](docs/troubleshooting.md)** - Common issues and solutions

## 🔧 Installation

### **Detailed Setup Instructions**

```bash
# 1. System Dependencies
sudo apt-get update  # Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib python3-dev

# 2. Python Dependencies
pip install -r requirements.txt

# 3. spaCy Spanish Model
python -m spacy download es_core_news_lg

# 4. Download LLM Models
mkdir -p data/models
# Download Mistral 7B GGUF model to data/models/
```

### **Configuration Files**

- **`.env`** - Environment variables and API keys
- **`config/esco_config.yaml`** - ESCO taxonomy configuration
- **`src/scraper/settings.py`** - Scrapy configuration
- **`src/config/settings.py`** - Application settings

## 💻 Usage Examples

### **Command Line Interface**

The system provides a comprehensive CLI through the orchestrator:

```bash
# Check system status
python -m src.orchestrator status

# Run complete pipeline for a country
python -m src.orchestrator run "computrabajo" CO --limit 100 --max-pages 5

# Generate specific analysis
python -m src.orchestrator process-jobs
python -m src.orchestrator health
```

### **Python API**

```python
from src.orchestrator import run_pipeline
from src.analyzer import SkillClusterer

# Run analysis programmatically
clusterer = SkillClusterer()
results = clusterer.run_clustering_pipeline()

# Access results
print(f"Found {results['n_clusters']} skill clusters")
```

### **Data Access**

```python
from src.database.operations import DatabaseOperations

db = DatabaseOperations()

# Get skill statistics
stats = db.get_skill_statistics(country='CO')
print(f"Top skills in Colombia: {stats['top_skills'][:5]}")
```

## 📊 Data Flow

### **Data Transformation Pipeline**

1. **Raw HTML** → **Structured Job Data** (Scraper)
2. **Job Text** → **Skill Entities** (NER + Regex)
3. **Raw Skills** → **Normalized Skills** (LLM + ESCO)
4. **Skill Text** → **Vector Embeddings** (E5 Model)
5. **Vectors** → **Skill Clusters** (UMAP + HDBSCAN)
6. **Analysis** → **Static Reports** (PDF/PNG/CSV)

### **Sample Data Formats**

```json
// Raw Job Posting
{
  "job_id": "uuid",
  "portal": "computrabajo",
  "country": "CO",
  "title": "Desarrollador Full Stack Senior",
  "description": "Buscamos desarrollador con React, Node.js...",
  "requirements": "5+ años experiencia, React, AWS...",
  "scraped_at": "2025-01-20T10:30:00Z"
}

// Enhanced Skills
{
  "skill": "React.js",
  "type": "explicit",
  "esco_uri": "http://data.europa.eu/esco/skill/react-framework",
  "llm_confidence": 0.95,
  "category": "frontend_framework"
}

// Skill Clusters
{
  "cluster_id": 0,
  "label": "Frontend Development",
  "size": 89,
  "top_skills": ["React.js", "Vue.js", "JavaScript"],
  "cohesion_score": 0.78
}
```

## 🤝 Contributing

### **Development Setup**

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Run tests
pytest tests/

# Code formatting
black src/
flake8 src/
```

### **Project Structure**

```
observatorio-demanda-laboral/
├── src/                    # Source code
│   ├── scraper/           # Web scraping module
│   ├── extractor/         # Skill extraction
│   ├── llm_processor/     # LLM enhancement
│   ├── embedder/          # Vector generation
│   ├── analyzer/          # Analysis & clustering
│   ├── database/          # Database operations
│   └── orchestrator.py    # Main pipeline controller
├── config/                 # Configuration files
├── docs/                   # Documentation
├── tests/                  # Test suite
├── notebooks/              # Jupyter notebooks
└── outputs/                # Generated reports
```

### **Contributing Guidelines**

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** your changes (`git commit -m 'Add amazing feature'`)
4. **Push** to the branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **ESCO Taxonomy** - European Skills, Competences, Qualifications and Occupations
- **spaCy** - Industrial-strength Natural Language Processing
- **Hugging Face** - Transformers and sentence embeddings
- **Scrapy** - Web scraping framework
- **PostgreSQL + pgvector** - Vector database capabilities

---

**Built with ❤️ for the Latin American tech community**

*Developed as part of a Master's thesis in Systems Engineering at Pontificia Universidad Javeriana, Colombia*
