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
    llm_provider: str = "deepseek"  # 支持 openai, deepseek 等
    llm_model: str = "deepseek-chat"
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = "https://api.deepseek.com"
    llm_temperature: float = 0.7
    llm_max_tokens: int = 2048
    
    # 多模态服务配置
    # HuggingFace服务 (推荐，经济实用)
    huggingface_token: Optional[str] = None
    use_local_hf_models: bool = True  # 是否使用本地HF模型
    hf_cache_dir: Optional[str] = None  # HF模型缓存目录
    
    # OpenAI服务 (可选，高质量)
    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None
    
    # Anthropic Claude服务 (可选)
    anthropic_api_key: Optional[str] = None
    
    # Google Cloud服务 (可选)
    google_credentials_path: Optional[str] = None
    google_project_id: Optional[str] = None
    
    # Azure服务 (可选)
    azure_speech_key: Optional[str] = None
    azure_speech_region: Optional[str] = None
    azure_vision_key: Optional[str] = None
    azure_vision_endpoint: Optional[str] = None
    
    # 本地模型配置
    whisper_model_size: str = "medium"  # tiny, base, small, medium, large - medium对中文支持更好
    enable_local_whisper: bool = True
    whisper_language: str = "zh"  # 默认语言设置为中文
    
    # Ollama 视觉模型配置
    ollama_vision_model: str = "qwen2.5vl:2b"  # 可选: qwen2.5vl:2b (快速), qwen2.5vl:7b (准确), llava:7b
    ollama_vision_timeout: int = 120  # 视觉模型超时时间（秒）
    ollama_max_image_size: int = 768  # 最大图像尺寸
    
    # 多模态模型配置 (与.env中的配置对应)
    multimodal_model: str = "Qwen/Qwen-VL-Chat"  # 多模态大模型
    use_local_models: bool = True  # 启用本地模型
    
    # 多模态处理配置
    max_image_size_mb: int = 10
    max_audio_duration_seconds: int = 300
    max_video_duration_seconds: int = 600
    temp_dir: str = "/tmp/nexusmind"
    
    # 服务质量配置
    high_quality_threshold: float = 0.8
    enable_fallback_providers: bool = True
    max_processing_time_seconds: int = 60
    
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


def get_settings() -> Settings:
    """获取配置实例"""
    return settings