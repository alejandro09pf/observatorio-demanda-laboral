# 📁 Project Structure - Labor Market Observatory

> **Complete overview of the project directory structure and file organization**

## 📋 Table of Contents

- [🏗️ Overall Structure](#️-overall-structure)
- [📁 Root Directory](#-root-directory)
- [🔧 Source Code (`src/`)](#-source-code-src)
- [📚 Documentation (`docs/`)](#-documentation-docs)
- [📖 Documentation (`documentation/`)](#-documentation-documentation)
- [🧪 Testing (`tests/`)](#-testing-tests)
- [📓 Notebooks (`notebooks/`)](#-notebooks-notebooks)
- [⚙️ Configuration (`config/`)](#️-configuration-config)
- [🗄️ Data and Outputs](#-data-and-outputs)
- [🚀 Scripts and Tools](#-scripts-and-tools)
- [📦 Package Management](#-package-management)

## 🏗️ Overall Structure

The Labor Market Observatory follows a **modular, well-organized structure** that separates concerns and makes the system easy to understand, maintain, and extend.

```
observatorio-demanda-laboral/
├── 📁 src/                    # Source code (main application)
├── 📁 docs/                   # User documentation
├── 📁 documentation/          # Technical specifications
├── 📁 tests/                  # Test suite
├── 📁 notebooks/              # Jupyter notebooks
├── 📁 config/                 # Configuration files
├── 📁 data/                   # Data storage and models
├── 📁 outputs/                # Generated reports and visualizations
├── 📁 scripts/                # Utility scripts
├── 📁 logs/                   # Application logs
├── 📄 README.md               # Project overview
├── 📄 requirements.txt        # Python dependencies
├── 📄 setup.py                # Package configuration
├── 📄 .env.example            # Environment template
├── 📄 .gitignore              # Git ignore rules
├── 📄 LICENSE                 # Project license
└── 📄 docker-compose.yml      # Docker configuration
```

## 📁 Root Directory

### **Core Project Files**

| File | Purpose | Status |
|------|---------|---------|
| `README.md` | **Project overview and quick start guide** | ✅ **Complete** |
| `requirements.txt` | **Python dependencies and versions** | ✅ **Complete** |
| `setup.py` | **Package installation configuration** | ❌ **Missing** |
| `.env.example` | **Environment variables template** | ❌ **Missing** |
| `.gitignore` | **Git ignore patterns** | ❌ **Missing** |
| `LICENSE` | **Project license (MIT)** | ✅ **Exists** |
| `docker-compose.yml` | **Docker orchestration** | ❌ **Missing** |

### **Required Root Files**

Based on your original documentation, we need to create:

#### **1. setup.py**
```python
from setuptools import setup, find_packages

setup(
    name="labor-observatory",
    version="1.0.0",
    author="Nicolas Francisco Camacho Alarcon",
    description="Automated Labor Market Observatory for Latin America",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        line.strip()
        for line in open("requirements.txt")
        if line.strip() and not line.startswith("#")
    ],
    entry_points={
        "console_scripts": [
            "labor-observatory=orchestrator:app",
        ],
    },
)
```

#### **2. .gitignore**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Data and Models
data/models/*.gguf
data/models/*/
data/cache/
outputs/
logs/

# Database
*.db
*.sqlite3

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db

# Testing
.coverage
htmlcov/
.pytest_cache/

# Scrapy
.scrapy/

# Notebooks
.ipynb_checkpoints/
```

#### **3. docker-compose.yml**
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: labor_observatory
      POSTGRES_USER: labor_user
      POSTGRES_PASSWORD: your_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./src/database/migrations:/docker-entrypoint-initdb.d
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements,pgvector
      -c pg_stat_statements.track=all

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  app:
    build: .
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://labor_user:your_password@postgres:5432/labor_observatory
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data:/app/data
      - ./outputs:/app/outputs
      - ./logs:/app/logs

volumes:
  postgres_data:
  redis_data:
```

## 🔧 Source Code (`src/`)

### **Current Structure**
```
src/
├── 📁 scraper/                # Web scraping module
│   ├── 📁 spiders/           # Scrapy spiders
│   ├── 📄 items.py           # Data models
│   ├── 📄 pipelines.py       # Data processing
│   ├── 📄 settings.py        # Scrapy configuration
│   ├── 📄 middlewares.py     # Request middleware
│   └── 📄 scrapy.cfg         # Scrapy project config
├── 📁 extractor/              # Skill extraction module
├── 📁 llm_processor/          # LLM enhancement module
├── 📁 embedder/               # Vector generation module
├── 📁 analyzer/               # Analysis and clustering
├── 📁 database/               # Database operations
├── 📁 utils/                  # Utility functions
├── 📄 orchestrator.py         # Main pipeline controller
└── 📄 __init__.py             # Package initialization
```

### **Missing Components**

Based on your documentation, we need to create:

#### **1. Configuration Module (`src/config/`)**
```
src/config/
├── 📄 __init__.py
├── 📄 settings.py             # Application settings
├── 📄 database.py             # Database configuration
├── 📄 logging_config.py       # Logging setup
└── 📄 esco_config.yaml        # ESCO taxonomy config
```

#### **2. Database Module (`src/database/`)**
```
src/database/
├── 📄 __init__.py
├── 📄 models.py               # SQLAlchemy models
├── 📄 operations.py           # Database operations
└── 📁 migrations/             # Database migrations
    └── 📄 001_initial_schema.sql
```

#### **3. Module Implementations**
```
src/extractor/
├── 📄 __init__.py
├── 📄 ner_extractor.py        # NER-based extraction
├── 📄 regex_patterns.py       # Regex patterns
├── 📄 esco_matcher.py         # ESCO taxonomy matching
└── 📄 pipeline.py             # Extraction pipeline

src/llm_processor/
├── 📄 __init__.py
├── 📄 llm_handler.py          # LLM interaction
├── 📄 prompts.py              # Prompt templates
├── 📄 esco_normalizer.py      # ESCO normalization
└── 📄 validator.py            # Skill validation

src/embedder/
├── 📄 __init__.py
├── 📄 vectorizer.py           # Embedding generation
├── 📄 model_loader.py         # Model management
└── 📄 batch_processor.py      # Batch processing

src/analyzer/
├── 📄 __init__.py
├── 📄 clustering.py           # Skill clustering
├── 📄 dimension_reducer.py    # UMAP reduction
├── 📄 report_generator.py     # Report generation
└── 📄 visualizations.py       # Chart generation
```

## 📚 Documentation (`docs/`)

### **Current Status**
```
docs/
├── 📄 setup_guide.md          # ✅ **Complete**
├── 📄 architecture.md          # ✅ **Complete**
└── 📄 project_overview.md      # ✅ **Complete**
```

### **Missing Documentation**
```
docs/
├── 📄 api_reference.md         # ❌ **Missing**
├── 📄 troubleshooting.md       # ❌ **Missing**
└── 📄 contributing.md          # ❌ **Missing**
```

## 📖 Documentation (`documentation/`)

### **Current Status**
```
documentation/
├── 📄 master-tech-spec.md     # ✅ **Complete**
├── 📄 complete-implementation-guide.md # ✅ **Complete**
└── 📄 data-flow-reference.md  # ✅ **Complete**
```

## 🧪 Testing (`tests/`)

### **Current Structure**
```
tests/
├── 📄 __init__.py
└── 📁 fixtures/
    └── 📄 __init__.py
```

### **Missing Test Files**
```
tests/
├── 📄 conftest.py              # Test configuration
├── 📄 test_scraper.py          # Scraper tests
├── 📄 test_extractor.py        # Extractor tests
├── 📄 test_llm_processor.py    # LLM processor tests
├── 📄 test_embedder.py         # Embedder tests
├── 📄 test_analyzer.py         # Analyzer tests
├── 📄 test_database.py         # Database tests
└── 📄 test_orchestrator.py     # Orchestrator tests
```

## 📓 Notebooks (`notebooks/`)

### **Current Status**
```
notebooks/
├── 📄 01_exploratory_analysis.ipynb      # ❌ **Empty**
├── 📄 02_llm_prompt_testing.ipynb        # ❌ **Empty**
└── 📄 03_visualization_experiments.ipynb # ❌ **Empty**
```

## ⚙️ Configuration (`config/`)

### **Current Status**
```
config/
└── 📄 __init__.py              # ❌ **Empty**
```

### **Required Configuration**
```
config/
├── 📄 __init__.py
├── 📄 settings.py              # Application settings
├── 📄 database.py              # Database configuration
├── 📄 logging_config.py        # Logging setup
└── 📄 esco_config.yaml         # ESCO taxonomy
```

## 🗄️ Data and Outputs

### **Required Directories**
```
data/
├── 📁 models/                  # LLM models
├── 📁 cache/                   # Embedding cache
└── 📁 esco/                    # ESCO taxonomy data

outputs/                        # Generated reports
logs/                           # Application logs
```

## 🚀 Scripts and Tools

### **Required Scripts**
```
scripts/
├── 📄 setup_database.py        # Database initialization
├── 📄 download_models.py       # Model download
├── 📄 validate_esco.py         # ESCO validation
└── 📄 run_pipeline.py          # Pipeline execution
```

## 📦 Package Management

### **Development Dependencies**
```
requirements-dev.txt             # ❌ **Missing**
```

**Required content:**
```txt
# Development dependencies
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
black==23.12.1
flake8==7.0.0
mypy==1.8.0
pre-commit==3.6.0
```

## 🔍 Missing Files Summary

### **Critical Missing Files**
1. **`setup.py`** - Package configuration
2. **`.env.example`** - Environment template
3. **`.gitignore`** - Git ignore patterns
4. **`docker-compose.yml`** - Docker orchestration
5. **`requirements-dev.txt`** - Development dependencies

### **Missing Source Code**
1. **`src/config/`** - Configuration module
2. **`src/database/`** - Database models and operations
3. **Module implementations** - Core functionality

### **Missing Documentation**
1. **`docs/api_reference.md`** - API documentation
2. **`docs/troubleshooting.md`** - Problem solving guide
3. **`docs/contributing.md`** - Contribution guidelines

### **Missing Tests**
1. **Test files** for all modules
2. **Test configuration** and fixtures
3. **Integration tests** for the pipeline

## 🚀 Next Steps

### **Immediate Actions (Priority 1)**
1. Create missing configuration files
2. Implement core module functionality
3. Set up database schema and operations

### **Short Term (Priority 2)**
1. Complete test suite
2. Add missing documentation
3. Create utility scripts

### **Medium Term (Priority 3)**
1. Docker containerization
2. CI/CD pipeline setup
3. Performance optimization

---

## 📊 Structure Completeness

| Category | Files | Complete | Missing | Completion |
|----------|-------|----------|---------|------------|
| **Root Files** | 7 | 3 | 4 | 43% |
| **Source Code** | 25+ | 8 | 17+ | 32% |
| **Documentation** | 6 | 3 | 3 | 50% |
| **Configuration** | 5 | 1 | 4 | 20% |
| **Testing** | 8 | 2 | 6 | 25% |
| **Scripts** | 4 | 0 | 4 | 0% |

**Overall Project Completion: ~30%**

---

**The foundation is solid, but significant implementation work is needed to complete the system.** 🚀 