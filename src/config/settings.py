from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import Optional, List
import os
from functools import lru_cache

class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env='DATABASE_URL')
    database_pool_size: int = Field(20, env='DATABASE_POOL_SIZE')
    
    # Scraping
    scraper_user_agent: str = Field(..., env='SCRAPER_USER_AGENT')
    scraper_concurrent_requests: int = Field(16, env='SCRAPER_CONCURRENT_REQUESTS')
    scraper_download_delay: float = Field(1.0, env='SCRAPER_DOWNLOAD_DELAY')
    scraper_retry_times: int = Field(3, env='SCRAPER_RETRY_TIMES')
    
    # ESCO
    esco_api_url: str = Field('https://ec.europa.eu/esco/api', env='ESCO_API_URL')
    esco_version: str = Field('1.1.0', env='ESCO_VERSION')
    esco_language: str = Field('es', env='ESCO_LANGUAGE')
    
    # LLM Configuration
    llm_model_name: str = Field('gemma-2-3b-instruct', env='LLM_MODEL_NAME')  # gemma-2-3b-instruct, llama-3.2-3b-instruct, mistral-7b-instruct
    llm_models_dir: str = Field('./data/models', env='LLM_MODELS_DIR')
    llm_context_length: int = Field(16384, env='LLM_CONTEXT_LENGTH')  # Increased from 8192 for Mistral
    llm_max_tokens: int = Field(2048, env='LLM_MAX_TOKENS')  # Increased from 512 for long job descriptions
    llm_temperature: float = Field(0.3, env='LLM_TEMPERATURE')  # Lower for more deterministic skill extraction
    llm_top_p: float = Field(0.9, env='LLM_TOP_P')
    llm_top_k: int = Field(40, env='LLM_TOP_K')
    llm_repeat_penalty: float = Field(1.1, env='LLM_REPEAT_PENALTY')

    # GPU Configuration
    llm_n_gpu_layers: int = Field(-1, env='LLM_N_GPU_LAYERS')  # 0 = CPU only, -1 = all layers to GPU (Metal on Mac)
    llm_n_threads: int = Field(8, env='LLM_N_THREADS')  # CPU threads when using CPU
    llm_n_batch: int = Field(512, env='LLM_N_BATCH')
    llm_use_mmap: bool = Field(True, env='LLM_USE_MMAP')
    llm_use_mlock: bool = Field(False, env='LLM_USE_MLOCK')

    # Inference Engine
    llm_backend: str = Field('llama-cpp', env='LLM_BACKEND')  # llama-cpp, vllm, transformers
    llm_quantization: str = Field('Q4_K_M', env='LLM_QUANTIZATION')  # Q4_K_M, Q5_K_M, Q8_0, fp16

    # OpenAI (Optional Fallback)
    openai_api_key: Optional[str] = Field(None, env='OPENAI_API_KEY')
    openai_model: str = Field('gpt-3.5-turbo', env='OPENAI_MODEL')

    # Benchmarking
    benchmark_enabled: bool = Field(False, env='BENCHMARK_ENABLED')
    benchmark_sample_size: int = Field(50, env='BENCHMARK_SAMPLE_SIZE')
    benchmark_output_dir: str = Field('./outputs/benchmarks', env='BENCHMARK_OUTPUT_DIR')
    
    # Embeddings
    embedding_model: str = Field('intfloat/multilingual-e5-base', env='EMBEDDING_MODEL')
    embedding_batch_size: int = Field(32, env='EMBEDDING_BATCH_SIZE')
    embedding_cache_dir: str = Field('./data/cache/embeddings', env='EMBEDDING_CACHE_DIR')
    
    # Analysis
    cluster_min_size: int = Field(5, env='CLUSTER_MIN_SIZE')
    cluster_min_samples: int = Field(3, env='CLUSTER_MIN_SAMPLES')
    umap_n_neighbors: int = Field(15, env='UMAP_N_NEIGHBORS')
    umap_min_dist: float = Field(0.1, env='UMAP_MIN_DIST')
    
    # Output
    output_dir: str = Field('./outputs', env='OUTPUT_DIR')
    report_format: str = Field('pdf', env='REPORT_FORMAT')
    log_level: str = Field('INFO', env='LOG_LEVEL')
    log_file: str = Field('./logs/labor_observatory.log', env='LOG_FILE')
    
    # Supported countries and portals
    supported_countries: List[str] = ['CO', 'MX', 'AR']
    supported_portals: List[str] = ['computrabajo', 'bumeran', 'elempleo']
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Allow extra fields from environment
    
    @validator('output_dir', 'log_file', 'embedding_cache_dir')
    def create_directories(cls, v):
        os.makedirs(os.path.dirname(v) if os.path.dirname(v) else v, exist_ok=True)
        return v 

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 