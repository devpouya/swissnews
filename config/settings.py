import os
from typing import List, Optional
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/swissnews"
    
    # Vector Database
    VECTOR_DB_TYPE: str = "pinecone"  # Options: pinecone, weaviate, faiss
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None
    WEAVIATE_URL: Optional[str] = None
    
    # Scraping
    SCRAPE_INTERVAL_HOURS: int = 4
    MAX_ARTICLES_PER_OUTLET: int = 50
    USER_AGENT: str = "SwissNewsAggregator/1.0"
    
    # Embeddings
    EMBEDDING_MODEL: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    EMBEDDING_DIMENSION: int = 384
    
    # Translation
    OPENAI_API_KEY: Optional[str] = None
    TRANSLATION_MODEL: str = "gpt-3.5-turbo"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 4
    
    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    
    # Supported languages
    SUPPORTED_LANGUAGES: List[str] = ["de", "fr", "it", "en"]
    DEFAULT_LANGUAGE: str = "de"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/swissnews.log"
    
    # Redis (for Celery)
    REDIS_URL: str = "redis://localhost:6379/0"
    
    class Config:
        env_file = ".env"