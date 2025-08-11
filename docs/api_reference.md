# 🔌 API Reference - Labor Market Observatory

> **Complete API documentation for all modules and functions**

## 📋 Table of Contents

- [🏗️ Core Modules](#️-core-modules)
- [🗄️ Database Operations](#-database-operations)
- [🕷️ Scraping Module](#️-scraping-module)
- [🔍 Skill Extraction](#-skill-extraction)
- [🤖 LLM Processing](#-llm-processing)
- [📊 Analysis & Clustering](#-analysis--clustering)
- [📈 Visualization](#-visualization)
- [⚙️ Configuration](#️-configuration)
- [🛠️ Utilities](#️-utilities)

## 🏗️ Core Modules

### **Orchestrator (`src/orchestrator.py`)**

The main pipeline controller that orchestrates all operations.

#### **Commands**

```bash
# Scrape jobs from a portal
python src/orchestrator.py scrape <country> <portal> [--pages N]

# Extract skills from scraped jobs
python src/orchestrator.py extract [--batch-size N]

# Enhance skills using LLM
python src/orchestrator.py enhance [--batch-size N]

# Generate embeddings
python src/orchestrator.py embed

# Run clustering analysis
python src/orchestrator.py analyze [--method METHOD]

# Generate reports
python src/orchestrator.py report [--country CODE] [--format FORMAT]

# Run full pipeline
python src/orchestrator.py pipeline <country> <portal> [--full]

# Check system status
python src/orchestrator.py status
```

#### **Parameters**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `country` | str | Country code (CO, MX, AR) | Required |
| `portal` | str | Portal name | Required |
| `--pages` | int | Number of pages to scrape | 1 |
| `--batch-size` | int | Batch size for processing | 100 |
| `--method` | str | Clustering method | hdbscan |
| `--format` | str | Report format (pdf, png, csv) | pdf |
| `--full` | flag | Run complete pipeline | False |

## 🗄️ Database Operations

### **DatabaseOperations Class**

Main interface for database interactions.

#### **Methods**

```python
class DatabaseOperations:
    def __init__(self, database_url: Optional[str] = None)
    def get_session(self) -> Session
    def insert_job(self, job_data: Dict[str, Any]) -> Optional[str]
    def get_unprocessed_jobs(self, limit: int = 100) -> List[RawJob]
    def mark_job_processed(self, job_id: str)
    def insert_extracted_skills(self, job_id: str, skills: List[Dict[str, Any]])
    def get_extracted_skills_for_processing(self, limit: int = 100) -> List[Dict[str, Any]]
    def insert_enhanced_skills(self, job_id: str, skills: List[Dict[str, Any]])
    def get_unique_skills_for_embedding(self) -> List[str]
    def insert_skill_embeddings(self, embeddings: List[Dict[str, Any]])
    def get_all_embeddings(self) -> List[Dict[str, Any]]
    def save_analysis_results(self, analysis_type: str, results: Dict[str, Any], 
                            parameters: Dict[str, Any], country: Optional[str] = None)
    def get_skill_statistics(self, country: Optional[str] = None) -> Dict[str, Any]
```

#### **Usage Example**

```python
from database.operations import DatabaseOperations

# Initialize
db_ops = DatabaseOperations()

# Insert a job
job_data = {
    "portal": "computrabajo",
    "country": "CO",
    "url": "https://example.com/job/1",
    "title": "Software Developer",
    "description": "Python developer needed"
}
job_id = db_ops.insert_job(job_data)

# Get unprocessed jobs
jobs = db_ops.get_unprocessed_jobs(limit=50)
```

## 🕷️ Scraping Module

### **BaseSpider Class**

Abstract base class for all job spiders.

#### **Methods**

```python
class BaseSpider(scrapy.Spider):
    def parse_job(self, response) -> JobItem
    def extract_text(self, selector, default="") -> str
    def build_absolute_url(self, relative_url: str) -> str
    def log_progress(self, current: int, total: int)
```

#### **Usage Example**

```python
from scraper.spiders.base_spider import BaseSpider

class CustomSpider(BaseSpider):
    name = 'custom_spider'
    
    def parse_job(self, response):
        return JobItem(
            title=self.extract_text(response.css('h1::text')),
            description=self.extract_text(response.css('.description::text')),
            # ... other fields
        )
```

### **JobItem Class**

Data model for job postings.

#### **Fields**

```python
class JobItem(scrapy.Item):
    job_id = scrapy.Field()
    portal = scrapy.Field()
    country = scrapy.Field()
    url = scrapy.Field()
    title = scrapy.Field()
    company = scrapy.Field()
    location = scrapy.Field()
    description = scrapy.Field()
    requirements = scrapy.Field()
    salary_raw = scrapy.Field()
    contract_type = scrapy.Field()
    remote_type = scrapy.Field()
    posted_date = scrapy.Field()
    scraped_at = scrapy.Field()
    content_hash = scrapy.Field()
    raw_html = scrapy.Field()
    is_processed = scrapy.Field()
```

## 🔍 Skill Extraction

### **ExtractionPipeline Class**

Orchestrates skill extraction using multiple methods.

#### **Methods**

```python
class ExtractionPipeline:
    def __init__(self)
    def extract_skills_from_job(self, job_data: Dict[str, Any]) -> List[Dict[str, Any]]
    def process_batch(self, batch_size: int = 100) -> Dict[str, Any]
```

### **NERExtractor Class**

Extract skills using Named Entity Recognition.

#### **Methods**

```python
class NERExtractor:
    def __init__(self, model_path: Optional[str] = None)
    def extract_skills(self, text: str) -> List[Dict[str, Any]]
```

### **RegexExtractor Class**

Extract skills using regular expressions.

#### **Methods**

```python
class RegexExtractor:
    def __init__(self)
    def extract_skills(self, text: str) -> List[Dict[str, Any]]
```

### **ESCOMatcher Class**

Match skills to ESCO taxonomy.

#### **Methods**

```python
class ESCOMatcher:
    def __init__(self)
    def match_skill(self, skill_text: str) -> Optional[Dict[str, Any]]
    def search_skills(self, query: str) -> List[Dict[str, Any]]
```

## 🤖 LLM Processing

### **LLMProcessingPipeline Class**

Processes skills using LLM for enhancement.

#### **Methods**

```python
class LLMProcessingPipeline:
    def __init__(self, model_type: str = "local")
    def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]
    def process_batch(self, batch_size: int = 50) -> Dict[str, Any]
```

### **LLMHandler Class**

Manages LLM interactions.

#### **Methods**

```python
class LLMHandler:
    def __init__(self, model_type: str = "local")
    def generate(self, prompt: str) -> Dict[str, Any]
```

### **PromptTemplates Class**

Manages prompt templates.

#### **Methods**

```python
class PromptTemplates:
    def __init__(self)
    def get_prompt(self, template_name: str, **kwargs) -> str
```

### **ESCONormalizer Class**

Normalizes skills using ESCO taxonomy.

#### **Methods**

```python
class ESCONormalizer:
    def __init__(self)
    def normalize_skill(self, skill_text: str) -> Optional[Dict[str, Any]]
    def normalize_skills(self, skills: List[str]) -> List[Dict[str, Any]]
```

### **SkillValidator Class**

Validates and filters skills.

#### **Methods**

```python
class SkillValidator:
    def __init__(self)
    def validate_skill(self, skill: str) -> Dict[str, Any]
    def validate_skills(self, skills: List[str]) -> List[Dict[str, Any]]
```

## 📊 Analysis & Clustering

### **SkillClusterer Class**

Clusters skills using HDBSCAN and UMAP.

#### **Methods**

```python
class SkillClusterer:
    def __init__(self)
    def run_clustering_pipeline(self) -> Dict[str, Any]
    def _analyze_clusters(self, labels: List[int], embeddings: List[List[float]]) -> List[Dict[str, Any]]
    def _calculate_metrics(self, coordinates: np.ndarray, labels: List[int]) -> Dict[str, float]
```

### **DimensionReducer Class**

Reduces embedding dimensions using UMAP.

#### **Methods**

```python
class DimensionReducer:
    def __init__(self)
    def reduce_dimensions(self, embeddings: List[List[float]], n_components: int = 2) -> np.ndarray
    def fit_transform(self, embeddings: List[List[float]]) -> np.ndarray
```

### **ReportGenerator Class**

Generates analysis reports.

#### **Methods**

```python
class ReportGenerator:
    def __init__(self)
    def generate_full_report(self, country: Optional[str] = None, 
                           include_visualizations: bool = True) -> str
    def _create_pdf_report(self, data: Dict[str, Any], country: Optional[str] = None) -> str
```

## 📈 Visualization

### **VisualizationGenerator Class**

Generates static visualizations.

#### **Methods**

```python
class VisualizationGenerator:
    def __init__(self, output_dir: str = None)
    def create_all_visualizations(self, analysis_data: Dict[str, Any],
                                country: Optional[str] = None) -> List[str]
    def create_skill_frequency_chart(self, skill_stats: Dict[str, Any],
                                   country: Optional[str] = None,
                                   top_n: int = 20) -> Optional[str]
```

## ⚙️ Configuration

### **Settings Class**

Application configuration management.

#### **Fields**

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    database_pool_size: int = 20
    
    # Scraping
    scraper_user_agent: str
    scraper_concurrent_requests: int = 16
    scraper_download_delay: float = 1.0
    scraper_retry_times: int = 3
    
    # ESCO
    esco_api_url: str = 'https://ec.europa.eu/esco/api'
    esco_version: str = '1.1.0'
    esco_language: str = 'es'
    
    # LLM
    llm_model_path: str
    llm_context_length: int = 4096
    llm_max_tokens: int = 512
    llm_temperature: float = 0.7
    llm_n_gpu_layers: int = 35
    
    # OpenAI (Optional)
    openai_api_key: Optional[str] = None
    openai_model: str = 'gpt-3.5-turbo'
    
    # Embeddings
    embedding_model: str = 'intfloat/multilingual-e5-base'
    embedding_batch_size: int = 32
    embedding_cache_dir: str = './data/cache/embeddings'
    
    # Analysis
    cluster_min_size: int = 5
    cluster_min_samples: int = 3
    umap_n_neighbors: int = 15
    umap_min_dist: float = 0.1
    
    # Output
    output_dir: str = './outputs'
    report_format: str = 'pdf'
    log_level: str = 'INFO'
    log_file: str = './logs/labor_observatory.log'
    
    # Supported countries and portals
    supported_countries: List[str] = ['CO', 'MX', 'AR']
    supported_portals: List[str] = ['computrabajo', 'bumeran', 'elempleo']
```

#### **Usage Example**

```python
from config.settings import get_settings

settings = get_settings()
print(f"Database: {settings.database_url}")
print(f"LLM Model: {settings.llm_model_path}")
```

### **Database Configuration**

```python
from config.database import get_database_url, get_database_config

# Get database URL
db_url = get_database_url()

# Get parsed configuration
db_config = get_database_config()
print(f"Host: {db_config['host']}")
print(f"Port: {db_config['port']}")
```

### **Logging Configuration**

```python
from config.logging_config import setup_logging

# Setup logging
logger = setup_logging(log_level='DEBUG', log_file='./logs/app.log')
```

## 🛠️ Utilities

### **Validation Functions**

```python
from utils.validators import validate_country, validate_portal, validate_skill

# Validate inputs
assert validate_country("CO") == True
assert validate_portal("computrabajo") == True
assert validate_skill("Python") == True
```

### **Text Cleaning Functions**

```python
from utils.cleaners import clean_text, normalize_text, remove_html

# Clean text
clean_text("  Hello   World  ")  # "Hello World"
normalize_text("Python & Django!")  # "python django"
remove_html("<p>Hello</p>")  # "Hello"
```

### **Metrics Functions**

```python
from utils.metrics import calculate_metrics

# Calculate statistics
data = [1, 2, 3, 4, 5]
stats = calculate_metrics(data)
print(f"Mean: {stats['mean']}")
print(f"Std: {stats['std']}")
```

### **Logging Utilities**

```python
from utils.logger import get_logger

# Get logger
logger = get_logger(__name__)
logger.info("Processing started")
logger.error("An error occurred")
```

## 🔧 Environment Variables

### **Required Variables**

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/labor_observatory

# Scraping
SCRAPER_USER_AGENT="Mozilla/5.0 (compatible; LaborObservatory/1.0)"

# LLM
LLM_MODEL_PATH=/path/to/mistral-7b-instruct.gguf

# OpenAI (Optional)
OPENAI_API_KEY=your_openai_key_here
```

### **Optional Variables**

```bash
# Database
DATABASE_POOL_SIZE=20

# Scraping
SCRAPER_CONCURRENT_REQUESTS=16
SCRAPER_DOWNLOAD_DELAY=1.0
SCRAPER_RETRY_TIMES=3

# ESCO
ESCO_API_URL=https://ec.europa.eu/esco/api
ESCO_VERSION=1.1.0
ESCO_LANGUAGE=es

# LLM
LLM_CONTEXT_LENGTH=4096
LLM_MAX_TOKENS=512
LLM_TEMPERATURE=0.7
LLM_N_GPU_LAYERS=35

# OpenAI
OPENAI_MODEL=gpt-3.5-turbo

# Embeddings
EMBEDDING_MODEL=intfloat/multilingual-e5-base
EMBEDDING_BATCH_SIZE=32
EMBEDDING_CACHE_DIR=./data/cache/embeddings

# Analysis
CLUSTER_MIN_SIZE=5
CLUSTER_MIN_SAMPLES=3
UMAP_N_NEIGHBORS=15
UMAP_MIN_DIST=0.1

# Output
OUTPUT_DIR=./outputs
REPORT_FORMAT=pdf
LOG_LEVEL=INFO
LOG_FILE=./logs/labor_observatory.log
```

## 📝 Error Handling

### **Common Exceptions**

```python
from sqlalchemy.exc import IntegrityError, OperationalError
from requests.exceptions import RequestException

try:
    # Database operation
    db_ops.insert_job(job_data)
except IntegrityError:
    logger.warning("Duplicate job detected")
except OperationalError:
    logger.error("Database connection failed")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

### **Retry Mechanisms**

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def api_call():
    # API call with automatic retry
    pass
```

## 🚀 Performance Considerations

### **Batch Processing**

```python
# Process in batches for memory efficiency
batch_size = 100
for i in range(0, total_items, batch_size):
    batch = items[i:i + batch_size]
    process_batch(batch)
```

### **Connection Pooling**

```python
# Database connection pooling
engine = create_engine(
    database_url,
    pool_size=20,
    max_overflow=0,
    pool_pre_ping=True
)
```

### **Caching**

```python
# Model caching
@lru_cache(maxsize=128)
def load_model(model_name):
    # Load and cache model
    pass
```

---

**This API reference provides comprehensive documentation for all modules and functions in the Labor Market Observatory system.** 🚀
