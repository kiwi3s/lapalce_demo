from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    qwen_api_key: Optional[str] = None
    qwen_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    ollama_base: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"
    chroma_path: str = "./chroma_db"
    sqlite_db: str = "./knowledge.db"
    bge_m3_path: str = "./models/bge-m3"
    reranker_path: str = "./models/bge-reranker-large"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
