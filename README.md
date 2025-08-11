# 🚀 Labor Market Observatory for Latin America

> **An automated system for monitoring technical skill demands in Latin American labor markets using AI, NLP, and data analysis.**

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

### **Core Modules**

| Module | Purpose | Technology | Output |
|--------|---------|------------|---------|
| **Scraper** | Extract job postings from portals | Scrapy + BeautifulSoup | Raw job data |
| **Extractor** | Identify technical skills | spaCy NER + Regex + ESCO | Skill entities |
| **LLM Processor** | Enhance and normalize skills | Mistral 7B + OpenAI | Enhanced skills |
| **Embedder** | Generate skill vectors | E5 Multilingual | 768D embeddings |
| **Analyzer** | Cluster and analyze skills | UMAP + HDBSCAN | Skill clusters |

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
# Install PostgreSQL extensions
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS pgvector;"

# Create database and run migrations
psql -U postgres -f src/database/migrations/001_initial_schema.sql
```

### **3. Environment Configuration**

```bash
# Copy and edit environment file
cp .env.example .env

# Edit .env with your database credentials and API keys
nano .env
```

### **4. Run Your First Pipeline**

```bash
# Scrape jobs from Computrabajo Colombia
python src/orchestrator.py scrape CO computrabajo --pages 5

# Extract skills from scraped jobs
python src/orchestrator.py extract --batch-size 100

# Enhance skills using LLM
python src/orchestrator.py enhance --batch-size 50

# Generate embeddings
python src/orchestrator.py embed

# Run analysis and generate reports
python src/orchestrator.py analyze
python src/orchestrator.py report --country CO
```

## 📚 Documentation

### **Comprehensive Guides**

- **[Master Technical Specification](documentation/master-tech-spec.md)** - Complete system blueprint
- **[Complete Implementation Guide](documentation/complete-implementation-guide.md)** - All production-ready code
- **[Data Flow Reference](documentation/data-flow-reference.md)** - Inter-module communication patterns
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
python src/orchestrator.py status

# Run complete pipeline for a country
python src/orchestrator.py pipeline CO computrabajo --full

# Generate specific analysis
python src/orchestrator.py analyze --method hdbscan
python src/orchestrator.py report --format pdf --country MX
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
