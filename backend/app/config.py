from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Modify"
    debug: bool = False

    # CORS
    cors_origins: str = "http://localhost:4200,http://localhost"

    # Database
    database_url: str = "postgresql+asyncpg://modify:modify@localhost:5432/modify"

    # Nexus Mods
    nexus_api_key: str = ""

    # LLM Provider
    llm_provider: str = "ollama"  # ollama, groq, together, huggingface

    # Ollama
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_model: str = "llama3.1:8b"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Together AI
    together_api_key: str = ""
    together_model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

    # HuggingFace
    huggingface_api_key: str = ""
    huggingface_model: str = "meta-llama/Llama-3.1-8B-Instruct"

    # Custom Mod Source
    custom_source_api_url: str = ""
    custom_source_api_key: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
