# 🏗️ System Architecture - Labor Market Observatory

> **Comprehensive overview of the system design, components, and data flow**

## 📋 Table of Contents

- [🎯 System Overview](#-system-overview)
- [🏗️ Architecture Principles](#️-architecture-principles)
- [🔧 Core Components](#-core-components)
- [📊 Data Flow](#-data-flow)
- [🗄️ Database Design](#️-database-design)
- [🔌 Module Interfaces](#-module-interfaces)
- [🚀 Performance Considerations](#-performance-considerations)
- [🔒 Security & Compliance](#-security--compliance)
- [📈 Scalability](#-scalability)

## 🎯 System Overview

The **Labor Market Observatory** is designed as a **linear data processing pipeline** that transforms raw job postings into actionable insights about skill demands. The system follows a **modular architecture** where each component has a single responsibility and communicates through well-defined interfaces.

### **High-Level Architecture**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           LABOR MARKET OBSERVATORY                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   SCRAPER   │───▶│  EXTRACTOR  │───▶│ LLM PROCESS │───▶│  EMBEDDER   │  │
│  │             │    │             │    │             │    │             │  │
│  │ • Web       │    │ • NER       │    │ • Dedup     │    │ • Vectorize │  │
│  │ • Parsing   │    │ • Regex     │    │ • Infer     │    │ • Cache     │  │
│  │ • Storage   │    │ • ESCO      │    │ • Normalize │    │ • Store     │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘  │
│           │                   │                   │                   │    │
│           ▼                   ▼                   ▼                   ▼    │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │                        POSTGRESQL DATABASE                          │    │
│  │                                                                     │    │
│  │  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │    │
│  │  │  raw_jobs   │ │extracted_   │ │enhanced_   │ │skill_       │   │    │
│  │  │             │ │skills       │ │skills      │ │embeddings   │   │    │
│  │  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                   │                                        │
│                                   ▼                                        │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                    │
│  │  ANALYZER   │    │  REPORTS    │    │  ORCHESTRATOR│                    │
│  │             │    │             │    │             │                    │
│  │ • Clustering│    │ • PDF       │    │ • Pipeline  │                    │
│  │ • UMAP      │    │ • Charts    │    │ • Monitoring│                    │
│  │ • HDBSCAN   │    │ • CSV       │    │ • Scheduling│                    │
│  └─────────────┘    └─────────────┘    └─────────────┘                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 🏗️ Architecture Principles

### **1. Single Responsibility Principle**
Each module has one clear purpose:
- **Scraper**: Extract job data from web sources
- **Extractor**: Identify skills in text
- **LLM Processor**: Enhance and normalize skills
- **Embedder**: Generate vector representations
- **Analyzer**: Perform clustering and analysis

### **2. Linear Pipeline Design**
Data flows in one direction through the system:
```
Raw HTML → Structured Data → Skills → Enhanced Skills → Vectors → Analysis → Reports
```

### **3. Database-Centric Communication**
All modules communicate through PostgreSQL:
- **No direct API calls** between modules
- **Centralized data store** with defined schemas
- **ACID compliance** for data integrity
- **Vector operations** via pgvector extension

### **4. Fault Tolerance**
- **Retry mechanisms** with exponential backoff
- **Graceful degradation** when services fail
- **Data validation** at each stage
- **Comprehensive logging** for debugging

### **5. Extensibility**
- **Plugin architecture** for new job portals
- **Configurable skill extraction** patterns
- **Modular analysis** algorithms
- **Customizable reporting** templates

## 🔧 Core Components

### **1. Scraper Module**

#### **Purpose**
Extract job postings from Latin American job portals with integrated parsing and validation.

#### **Components**
- **Spider Classes**: `ComputrabajoSpider`, `BumeranSpider`, `ElempleoSpider`
- **Item Pipeline**: Validation, normalization, and database storage
- **Middleware**: User agent rotation, retry logic, rate limiting

#### **Key Features**
```python
class BaseJobSpider(scrapy.Spider, ABC):
    """Base spider with common functionality for all job portals."""
    
    def __init__(self, country=None, *args, **kwargs):
        self.country = country
        self.total_scraped = 0
    
    @abstractmethod
    def parse_job(self, response):
        """Parse individual job posting. Must be implemented by subclasses."""
        pass
```

#### **Data Output**
```json
{
  "job_id": "uuid",
  "portal": "computrabajo",
  "country": "CO",
  "title": "Desarrollador Full Stack Senior",
  "description": "Buscamos desarrollador con React, Node.js...",
  "requirements": "5+ años experiencia, React, AWS...",
  "scraped_at": "2025-01-20T10:30:00Z"
}
```

### **2. Extractor Module**

#### **Purpose**
Identify technical skills using multiple extraction methods: NER, regex patterns, and ESCO taxonomy matching.

#### **Components**
- **NERExtractor**: Custom spaCy-based entity recognition
- **RegexExtractor**: Pattern-based skill identification
- **ESCOMatcher**: Taxonomy-based skill mapping
- **ExtractionPipeline**: Orchestrates all extraction methods

#### **Key Features**
```python
class NERExtractor:
    """Extract skills using Named Entity Recognition."""
    
    def __init__(self, model_path: Optional[str] = None):
        self.nlp = spacy.load("es_core_news_lg")
        self._add_tech_entity_ruler()
    
    def extract_skills(self, text: str) -> List[Dict[str, Any]]:
        """Extract skills from text using NER."""
        doc = self.nlp(text)
        skills = []
        
        for ent in doc.ents:
            if ent.label_ in ['SKILL', 'FRAMEWORK', 'PLATFORM']:
                skills.append({
                    'skill_text': ent.text,
                    'confidence_score': ent.prob,
                    'span_start': ent.start_char,
                    'span_end': ent.end_char
                })
        
        return skills
```

#### **Data Output**
```json
{
  "extraction_id": "uuid",
  "job_id": "uuid",
  "extracted_skills": [
    {
      "skill_text": "React",
      "skill_type": "explicit",
      "extraction_method": "ner",
      "confidence_score": 0.95,
      "esco_uri": "http://data.europa.eu/esco/skill/react-framework"
    }
  ]
}
```

### **3. LLM Processor Module**

#### **Purpose**
Enhance extracted skills using Large Language Models for deduplication, implicit skill inference, and ESCO normalization.

#### **Components**
- **LLMHandler**: Manages local and cloud LLM interactions
- **PromptTemplates**: Structured prompts for skill processing
- **ESCONormalizer**: Maps skills to ESCO taxonomy
- **SkillValidator**: Validates and filters skills

#### **Key Features**
```python
class LLMProcessingPipeline:
    """Process skills using LLM for enhancement and normalization."""
    
    def __init__(self, model_type: str = "local"):
        self.llm_handler = LLMHandler(model_type)
        self.esco_normalizer = ESCONormalizer()
    
    def process_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single job's skills through LLM pipeline."""
        
        # Prepare prompt
        prompt = self._build_prompt(job_data)
        
        # Get LLM response
        response = self.llm_handler.generate(prompt)
        
        # Parse and validate response
        enhanced_skills = self._parse_llm_response(response)
        
        # Normalize with ESCO
        normalized_skills = self.esco_normalizer.normalize(enhanced_skills)
        
        return {
            'job_id': job_data['job_id'],
            'enhanced_skills': normalized_skills,
            'processing_time_ms': response['processing_time']
        }
```

#### **Data Output**
```json
{
  "enhancement_id": "uuid",
  "job_id": "uuid",
  "enhanced_skills": [
    {
      "skill": "React.js",
      "type": "explicit",
      "esco_uri": "http://data.europa.eu/esco/skill/react-framework",
      "llm_confidence": 0.95,
      "category": "frontend_framework"
    },
    {
      "skill": "JavaScript",
      "type": "implicit",
      "reasoning": "React requires JavaScript knowledge",
      "llm_confidence": 0.88
    }
  ]
}
```

### **4. Embedder Module**

#### **Purpose**
Generate semantic vector representations for skills using multilingual embedding models.

#### **Components**
- **Vectorizer**: Manages embedding model loading and inference
- **ModelLoader**: Handles model caching and versioning
- **BatchProcessor**: Processes skills in batches for efficiency
- **SimilarityCalculator**: Computes skill similarities

#### **Key Features**
```python
class BatchProcessor:
    """Process skills in batches for embedding generation."""
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        self.vectorizer = Vectorizer(model_name)
        self.cache_dir = "./data/cache/embeddings"
    
    def process_all_skills(self) -> Dict[str, Any]:
        """Generate embeddings for all unique skills."""
        
        # Get skills without embeddings
        skills = self._get_unprocessed_skills()
        
        # Process in batches
        embeddings = []
        for batch in self._create_batches(skills, batch_size=32):
            batch_embeddings = self.vectorizer.embed_batch(batch)
            embeddings.extend(batch_embeddings)
        
        # Store in database
        self._store_embeddings(embeddings)
        
        return {
            'skills_processed': len(skills),
            'embeddings_created': len(embeddings),
            'processing_time': time.time() - start_time
        }
```

#### **Data Output**
```json
{
  "embedding_id": "uuid",
  "skill_text": "React.js",
  "embedding": [0.0234, -0.1523, 0.0891, ...],
  "model_name": "intfloat/multilingual-e5-base",
  "model_version": "1.0.0"
}
```

### **5. Analyzer Module**

#### **Purpose**
Perform clustering analysis on skill embeddings to identify skill groups and generate insights.

#### **Components**
- **SkillClusterer**: Main clustering orchestration
- **DimensionReducer**: UMAP-based dimensionality reduction
- **ReportGenerator**: Creates analysis reports
- **VisualizationGenerator**: Generates charts and graphs

#### **Key Features**
```python
class SkillClusterer:
    """Cluster skills using HDBSCAN and UMAP."""
    
    def __init__(self):
        self.umap = UMAP(
            n_neighbors=15,
            min_dist=0.1,
            n_components=2,
            random_state=42
        )
        self.clusterer = HDBSCAN(
            min_cluster_size=5,
            min_samples=3,
            metric='euclidean'
        )
    
    def run_clustering_pipeline(self) -> Dict[str, Any]:
        """Run complete clustering pipeline."""
        
        # Get embeddings from database
        embeddings = self._get_embeddings()
        
        # Reduce dimensionality
        coords_2d = self.umap.fit_transform(embeddings)
        
        # Perform clustering
        labels = self.clusterer.fit_predict(coords_2d)
        
        # Analyze results
        cluster_info = self._analyze_clusters(labels, embeddings)
        
        # Calculate quality metrics
        metrics = self._calculate_metrics(coords_2d, labels)
        
        return {
            'n_clusters': len(set(labels)) - (1 if -1 in labels else 0),
            'n_noise': list(labels).count(-1),
            'coordinates_2d': coords_2d,
            'labels': labels,
            'cluster_info': cluster_info,
            'metrics': metrics
        }
```

#### **Data Output**
```json
{
  "analysis_id": "uuid",
  "analysis_type": "clustering",
  "results": {
    "n_clusters": 12,
    "clusters": [
      {
        "cluster_id": 0,
        "label": "Frontend Development",
        "size": 89,
        "top_skills": ["React.js", "Vue.js", "JavaScript"],
        "cohesion_score": 0.78
      }
    ],
    "quality_metrics": {
      "silhouette_score": 0.68,
      "davies_bouldin_index": 0.92
    }
  }
}
```

## 📊 Data Flow

### **1. Data Transformation Pipeline**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Raw HTML      │───▶│ Structured Jobs │───▶│ Extracted Skills│
│                 │    │                 │    │                 │
│ • Job listings  │    │ • Title         │    │ • NER entities  │
│ • Search pages  │    │ • Description   │    │ • Regex matches │
│ • Detail pages  │    │ • Requirements  │    │ • ESCO mappings │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │  PostgreSQL     │    │  PostgreSQL     │
│   raw_jobs      │    │ extracted_skills│    │ enhanced_skills │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Enhanced Skills │───▶│ Skill Vectors   │───▶│ Skill Clusters  │
│                 │    │                 │    │                 │
│ • Normalized    │    │ • 768D vectors  │    │ • UMAP coords   │
│ • Deduplicated  │    │ • Similarities  │    │ • HDBSCAN labels│
│ • ESCO mapped   │    │ • Cached        │    │ • Analysis      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  PostgreSQL     │    │  PostgreSQL     │    │ Static Reports  │
│ enhanced_skills │    │ skill_embeddings│    │                 │
└─────────────────┘    └─────────────────┘    │ • PDF reports   │
                                              │ • PNG charts    │
                                              │ • CSV data      │
                                              └─────────────────┘
```

### **2. Module Communication Patterns**

#### **Database-First Communication**
- All modules read from and write to PostgreSQL
- No direct inter-module API calls
- Data consistency through database transactions
- Easy to debug and monitor data flow

#### **Batch Processing**
- Skills processed in configurable batch sizes
- Efficient resource utilization
- Progress tracking and error handling
- Configurable retry mechanisms

#### **Event-Driven Updates**
- Database triggers for processing status updates
- Orchestrator monitors table changes
- Automatic pipeline progression
- Real-time status monitoring

## 🗄️ Database Design

### **1. Core Tables**

#### **raw_jobs**
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
    is_processed BOOLEAN DEFAULT FALSE
);
```

#### **extracted_skills**
```sql
CREATE TABLE extracted_skills (
    extraction_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id),
    skill_text TEXT NOT NULL,
    skill_type VARCHAR(50),
    extraction_method VARCHAR(50),
    confidence_score FLOAT,
    source_section VARCHAR(50),
    span_start INTEGER,
    span_end INTEGER,
    esco_uri TEXT,
    extracted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **enhanced_skills**
```sql
CREATE TABLE enhanced_skills (
    enhancement_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_id UUID REFERENCES raw_jobs(job_id),
    original_skill_text TEXT,
    normalized_skill TEXT NOT NULL,
    skill_type VARCHAR(50),
    esco_concept_uri TEXT,
    esco_preferred_label TEXT,
    llm_confidence FLOAT,
    llm_reasoning TEXT,
    is_duplicate BOOLEAN DEFAULT FALSE,
    duplicate_of_id UUID,
    enhanced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    llm_model VARCHAR(100)
);
```

#### **skill_embeddings**
```sql
CREATE TABLE skill_embeddings (
    embedding_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    skill_text TEXT UNIQUE NOT NULL,
    embedding vector(768) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    model_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Vector similarity index
CREATE INDEX ON skill_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

### **2. Database Views**

#### **skill_frequency**
```sql
CREATE VIEW skill_frequency AS
SELECT 
    es.normalized_skill,
    COUNT(DISTINCT es.job_id) as job_count,
    COUNT(*) as total_mentions,
    ARRAY_AGG(DISTINCT rj.country) as countries
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
WHERE es.is_duplicate = FALSE
GROUP BY es.normalized_skill
ORDER BY job_count DESC;
```

#### **country_skill_distribution**
```sql
CREATE VIEW country_skill_distribution AS
SELECT 
    rj.country,
    es.normalized_skill,
    COUNT(DISTINCT es.job_id) as job_count
FROM enhanced_skills es
JOIN raw_jobs rj ON es.job_id = rj.job_id
WHERE es.is_duplicate = FALSE
GROUP BY rj.country, es.normalized_skill
ORDER BY rj.country, job_count DESC;
```

### **3. Performance Optimizations**

#### **Indexing Strategy**
```sql
-- Portal and country queries
CREATE INDEX idx_portal_country ON raw_jobs(portal, country);

-- Processing status
CREATE INDEX idx_processed ON raw_jobs(is_processed);

-- Skill lookups
CREATE INDEX idx_skill_text ON extracted_skills(skill_text);
CREATE INDEX idx_normalized ON enhanced_skills(normalized_skill);

-- Temporal queries
CREATE INDEX idx_scraped_at ON raw_jobs(scraped_at);
CREATE INDEX idx_enhanced_at ON enhanced_skills(enhanced_at);
```

#### **Partitioning Strategy**
```sql
-- Partition by country for large datasets
CREATE TABLE raw_jobs_CO PARTITION OF raw_jobs
FOR VALUES IN ('CO');

CREATE TABLE raw_jobs_MX PARTITION OF raw_jobs
FOR VALUES IN ('MX');

CREATE TABLE raw_jobs_AR PARTITION OF raw_jobs
FOR VALUES IN ('AR');
```

## 🔌 Module Interfaces

### **1. Base Module Interface**

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class BaseModule(ABC):
    """Base interface for all system modules."""
    
    @abstractmethod
    def process(self, batch_size: int = 100) -> Dict[str, Any]:
        """Process a batch of items."""
        pass
    
    @abstractmethod
    def validate_input(self) -> bool:
        """Validate input data."""
        pass
    
    @abstractmethod
    def get_metrics(self) -> Dict[str, Any]:
        """Get processing metrics."""
        pass
    
    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass
```

### **2. Module Configuration**

```python
from pydantic import BaseModel
from typing import Optional, List

class ModuleConfig(BaseModel):
    """Configuration for a module."""
    
    name: str
    enabled: bool = True
    batch_size: int = 100
    max_retries: int = 3
    timeout: int = 300
    
    # Module-specific settings
    settings: Dict[str, Any] = {}
    
    class Config:
        extra = "allow"
```

### **3. Module Communication**

```python
class ModuleMessage:
    """Message format for inter-module communication."""
    
    def __init__(self, 
                 message_type: str,
                 source_module: str,
                 target_module: str,
                 payload: Dict[str, Any]):
        self.message_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow()
        self.message_type = message_type
        self.source_module = source_module
        self.target_module = target_module
        self.payload = payload
        self.retry_count = 0
        self.max_retries = 3
```

## 🚀 Performance Considerations

### **1. Scraping Performance**

#### **Concurrent Requests**
```python
# Scrapy settings for optimal performance
CONCURRENT_REQUESTS = 16
CONCURRENT_REQUESTS_PER_DOMAIN = 8
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
```

#### **Rate Limiting**
```python
# Respectful scraping with rate limiting
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 10
AUTOTHROTTLE_TARGET_CONCURRENCY = 8.0
```

### **2. Processing Performance**

#### **Batch Processing**
```python
# Efficient batch processing
BATCH_SIZE = 100
MAX_WORKERS = 4
CHUNK_SIZE = 1000
```

#### **Caching Strategy**
```python
# Multi-level caching
CACHE_LEVELS = {
    'memory': {'max_size': 1000, 'ttl': 3600},
    'disk': {'max_size': 10000, 'ttl': 86400},
    'database': {'max_size': 100000, 'ttl': 604800}
}
```

### **3. Database Performance**

#### **Connection Pooling**
```python
# Database connection optimization
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 0
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

#### **Query Optimization**
```python
# Efficient queries with pagination
def get_unprocessed_jobs(limit: int = 100, offset: int = 0):
    query = """
    SELECT * FROM raw_jobs 
    WHERE is_processed = FALSE 
    ORDER BY scraped_at 
    LIMIT %s OFFSET %s
    """
    return execute_query(query, (limit, offset))
```

## 🔒 Security & Compliance

### **1. Data Privacy**

#### **Personal Information Handling**
- **No PII storage**: Job descriptions are anonymized
- **Content hashing**: Prevents duplicate storage
- **Data retention**: Configurable cleanup policies
- **Access control**: Role-based database permissions

#### **Compliance Measures**
- **GDPR compliance**: Right to be forgotten
- **Data minimization**: Only necessary data collected
- **Transparency**: Clear data usage policies
- **Consent**: Respectful scraping practices

### **2. Security Measures**

#### **Input Validation**
```python
def validate_job_data(job_data: Dict[str, Any]) -> bool:
    """Validate job data before processing."""
    
    # Check required fields
    required_fields = ['title', 'description', 'portal', 'country']
    for field in required_fields:
        if not job_data.get(field):
            return False
    
    # Validate country code
    if job_data['country'] not in ['CO', 'MX', 'AR']:
        return False
    
    # Sanitize HTML content
    job_data['description'] = clean_html(job_data['description'])
    
    return True
```

#### **SQL Injection Prevention**
```python
# Use parameterized queries
def insert_job(job_data: Dict[str, Any]):
    query = """
    INSERT INTO raw_jobs (title, description, portal, country)
    VALUES (%s, %s, %s, %s)
    """
    execute_query(query, (
        job_data['title'],
        job_data['description'],
        job_data['portal'],
        job_data['country']
    ))
```

### **3. Access Control**

#### **Database Security**
```sql
-- Create read-only user for analysis
CREATE USER analyst_user WITH PASSWORD 'secure_password';
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analyst_user;

-- Create write user for processing
CREATE USER processor_user WITH PASSWORD 'secure_password';
GRANT INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO processor_user;
```

## 📈 Scalability

### **1. Horizontal Scaling**

#### **Worker Processes**
```python
# Multiple worker processes
NUM_WORKERS = 4
WORKER_PROCESSES = {
    'scraper': 2,
    'extractor': 2,
    'llm_processor': 1,
    'embedder': 1,
    'analyzer': 1
}
```

#### **Load Balancing**
```python
# Database connection load balancing
DATABASE_REPLICAS = [
    'postgresql://replica1:5432/labor_observatory',
    'postgresql://replica2:5432/labor_observatory',
    'postgresql://replica3:5432/labor_observatory'
]
```

### **2. Vertical Scaling**

#### **Resource Optimization**
```python
# Memory management
MAX_MEMORY_USAGE = '8GB'
BATCH_SIZE_ADJUSTMENT = True
CACHE_EVICTION_POLICY = 'LRU'
```

#### **GPU Acceleration**
```python
# GPU utilization for LLM processing
GPU_ENABLED = True
GPU_MEMORY_FRACTION = 0.8
MIXED_PRECISION = True
```

### **3. Caching Strategy**

#### **Multi-Level Caching**
```python
class CacheManager:
    """Multi-level caching for optimal performance."""
    
    def __init__(self):
        self.l1_cache = LRUCache(maxsize=1000)  # Memory
        self.l2_cache = DiskCache(maxsize=10000)  # Disk
        self.l3_cache = DatabaseCache()  # Database
    
    def get(self, key: str) -> Any:
        """Get value from cache hierarchy."""
        
        # Try L1 cache
        value = self.l1_cache.get(key)
        if value:
            return value
        
        # Try L2 cache
        value = self.l2_cache.get(key)
        if value:
            self.l1_cache[key] = value  # Promote to L1
            return value
        
        # Try L3 cache
        value = self.l3_cache.get(key)
        if value:
            self.l2_cache[key] = value  # Promote to L2
            self.l1_cache[key] = value  # Promote to L1
            return value
        
        return None
```

---

## 🎯 Architecture Benefits

### **1. Maintainability**
- **Clear separation of concerns**
- **Well-defined interfaces**
- **Comprehensive documentation**
- **Consistent coding patterns**

### **2. Reliability**
- **Database-centric communication**
- **Comprehensive error handling**
- **Retry mechanisms**
- **Data validation at each stage**

### **3. Performance**
- **Batch processing**
- **Efficient caching**
- **Database optimization**
- **Resource management**

### **4. Extensibility**
- **Plugin architecture**
- **Configurable components**
- **Modular design**
- **Standard interfaces**

---

**This architecture provides a solid foundation for building a scalable, maintainable, and efficient labor market observatory system.** 🚀
