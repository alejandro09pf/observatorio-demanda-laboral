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
    
    # LLM
    llm_model_path: str = Field(..., env='LLM_MODEL_PATH')
    llm_context_length: int = Field(4096, env='LLM_CONTEXT_LENGTH')
    llm_max_tokens: int = Field(512, env='LLM_MAX_TOKENS')
    llm_temperature: float = Field(0.7, env='LLM_TEMPERATURE')
    llm_n_gpu_layers: int = Field(35, env='LLM_N_GPU_LAYERS')
    
    # OpenAI (Optional)
    openai_api_key: Optional[str] = Field(None, env='OPENAI_API_KEY')
    openai_model: str = Field('gpt-3.5-turbo', env='OPENAI_MODEL')
    
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
    
    @validator('output_dir', 'log_file', 'embedding_cache_dir')
    def create_directories(cls, v):
        os.makedirs(os.path.dirname(v) if os.path.dirname(v) else v, exist_ok=True)
        return v

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings() 