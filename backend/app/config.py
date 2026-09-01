from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "ImageForge"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./imageforge.db"
    
    # Active Provider: "lm_studio" or "cloud"
    ACTIVE_PROVIDER: str = "lm_studio"
    
    # LM Studio Settings
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    LM_STUDIO_API_KEY: str = ""
    LM_STUDIO_MODEL: str = ""
    LM_STUDIO_AUTO_LOAD: bool = True
    LM_STUDIO_AUTO_UNLOAD: bool = False
    LM_STUDIO_ENABLE_THINKING: bool = False
    LM_STUDIO_REASONING_EFFORT: str = "medium"  # instruct, low, medium, high, xhigh, max
    
    # Cloud Provider Settings (OpenAI Compatible)
    CLOUD_API_NAME: str = "自定义云端 API"
    CLOUD_API_BASE_URL: str = "https://api.openai.com/v1"
    CLOUD_API_KEY: str = ""
    CLOUD_MODEL: str = ""
    CLOUD_REASONING_EFFORT: str = "medium"
    
    # ComfyUI Settings
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"
    
    # Defaults
    DEFAULT_SAFETY: str = "Safe"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
