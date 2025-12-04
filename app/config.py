"""Configuration management using pydantic-settings"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gpt-oss:20b"
    ollama_timeout: int = 120

    # Phoenix
    phoenix_project_name: str = "quantum-wiki-rag"
    phoenix_endpoint: str = "http://localhost:6006"
    phoenix_collector_endpoint: str = "http://localhost:6006/v1/traces"

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"

    # ChromaDB
    chroma_persist_dir: str = ".chroma/quantum_wiki"
    chroma_collection_name: str = "quantum_wiki"

    # Scraper
    scraper_user_agent: str = "QuantumPhoenixBot/1.0 (Educational Demo)"
    scraper_delay_seconds: float = 2.0
    scraper_max_pages: int = 200
    scraper_timeout: int = 30

    # RAG
    rag_chunk_size: int = 800
    rag_chunk_overlap: int = 100
    rag_top_k: int = 5

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Chat
    max_chat_history: int = 10


# Global settings instance
settings = Settings()
