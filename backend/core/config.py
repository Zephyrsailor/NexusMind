from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""
    
    # API配置
    app_name: str = "NexusMind Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = True
    
    # FastAPI配置
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Redis配置
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    
    # RabbitMQ配置
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_user: str = "nexusmind"
    rabbitmq_password: str = "nexusmind123"
    rabbitmq_vhost: str = "/"
    
    # ChromaDB配置
    chromadb_host: str = "localhost"
    chromadb_port: int = 8000
    chromadb_collection: str = "nexusmind_memory"
    
    # LLM配置
    llm_provider: str = "openai"  # 支持 openai, deepseek 等
    llm_model: str = "gpt-3.5-turbo"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # Agent配置
    orchestrator_agent_id: str = "orchestrator"
    max_concurrent_tasks: int = 100
    task_timeout_seconds: int = 300
    
    # A2A协议配置
    a2a_exchange_name: str = "nexusmind.agents"
    a2a_response_timeout: int = 30
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# 全局配置实例
settings = Settings()