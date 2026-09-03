from pydantic_settings import BaseSettings, SettingsConfigDict
import os

# ImageForge 项目根目录：backend/app/config.py -> <root>/backend/app -> <root>
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "ImageForge"
    DEBUG: bool = True
    # 相对路径会经 DATABASE_URL_ABS 锚定到 PROJECT_ROOT，与启动 cwd 无关
    DATABASE_URL: str = "sqlite:///./imageforge.db"

    @property
    def DATABASE_URL_ABS(self) -> str:
        """数据库绝对 URL：SQLite 相对路径一律解析到项目根目录，
        repo root 启动或 `cd backend` 启动打开同一个数据库文件。"""
        if "sqlite" in self.DATABASE_URL:
            path = self.DATABASE_URL.replace("sqlite:///", "").split("?")[0]
            if not os.path.isabs(path):
                path = os.path.join(PROJECT_ROOT, path)
            return f"sqlite:///{os.path.abspath(path)}"
        return self.DATABASE_URL
    
    # Active Provider: "lm_studio" or "cloud"
    ACTIVE_PROVIDER: str = "lm_studio"
    
    # LM Studio Settings
    LM_STUDIO_BASE_URL: str = "http://localhost:1234"
    LM_STUDIO_API_KEY: str = ""
    LM_STUDIO_MODEL: str = ""
    LM_STUDIO_AUTO_LOAD: bool = True
    LM_STUDIO_AUTO_UNLOAD: bool = False
    
    # Cloud Provider Settings (OpenAI Compatible)
    CLOUD_API_NAME: str = "自定义云端 API"
    CLOUD_API_BASE_URL: str = "https://api.openai.com/v1"
    CLOUD_API_KEY: str = ""
    CLOUD_MODEL: str = ""
    
    # ComfyUI Settings
    COMFYUI_BASE_URL: str = "http://127.0.0.1:8188"
    # 角色联网解析（Character Online Resolver V1）
    ONLINE_RESOLVE_ENABLED: bool = False
    ONLINE_RESOLVE_CACHE_WRITE: bool = True
    ONLINE_RESOLVE_AMBIGUOUS: str = "ask"

    # ── Civitai Metadata（LoRA Metadata V1） ──
    # 仅允许两个官方 host 之一：red → https://civitai.red，com → https://civitai.com
    CIVITAI_API_HOST: str = "red"
    # 可选 API Token：只允许后端使用（Bearer 头），前端不得直接访问 Civitai API；
    # 不填也能查询公开 metadata。禁止把 token 发给任意第三方 host。
    CIVITAI_API_TOKEN: str = ""

    # Generation
    GENERATE_TIMEOUT_SECONDS: int = 300  # 前端等待 ComfyUI 生成的最长秒数（慢 GPU/高分辨率可调）

    # Local data (ImageForge-owned files)
    DATA_DIR: str = "data"

    @property
    def GENERATED_DIR(self) -> str:
        """ImageForge 自己的生成图目录——锚定在数据库文件所在目录下，
        与启动 cwd 无关（repo root 启动或 cd backend 启动都指向同一目录）。"""
        db_path = self.DATABASE_URL_ABS.replace("sqlite:///", "").split("?")[0]
        base = os.path.dirname(os.path.abspath(db_path)) or PROJECT_ROOT
        return os.path.join(base, self.DATA_DIR, "generated")

    @property
    def LORA_METADATA_DIR(self) -> str:
        """LoRA metadata 本地缓存根目录（封面等）——锚定项目 root，禁止使用 cwd。"""
        db_path = self.DATABASE_URL_ABS.replace("sqlite:///", "").split("?")[0]
        base = os.path.dirname(os.path.abspath(db_path)) or PROJECT_ROOT
        return os.path.join(base, self.DATA_DIR, "cache", "lora_metadata")
    
    # Defaults
    DEFAULT_SAFETY: str = "Safe"

settings = Settings()

EDITABLE_SETTING_KEYS = {
    "ACTIVE_PROVIDER",
    "LM_STUDIO_BASE_URL",
    "LM_STUDIO_API_KEY",
    "LM_STUDIO_MODEL",
    "LM_STUDIO_AUTO_LOAD",
    "LM_STUDIO_AUTO_UNLOAD",
    "CLOUD_API_NAME",
    "CLOUD_API_BASE_URL",
    "CLOUD_API_KEY",
    "CLOUD_MODEL",
    "COMFYUI_BASE_URL",
    "DEFAULT_SAFETY",
    "GENERATE_TIMEOUT_SECONDS",
    "ONLINE_RESOLVE_ENABLED",
    "ONLINE_RESOLVE_CACHE_WRITE",
    "ONLINE_RESOLVE_AMBIGUOUS",
    "CIVITAI_API_HOST",
    "CIVITAI_API_TOKEN",
}

# Civitai 双域：只允许这两个官方 host（防止 token 被发给任意第三方）
CIVITAI_HOSTS = {
    "red": "https://civitai.red",
    "com": "https://civitai.com",
}

# metadata_host 存裸 host（spec §60：外部链接用 https://{metadata_host}/models/{id}）
CIVITAI_HOST_NAMES = {
    "red": "civitai.red",
    "com": "civitai.com",
}
_CIVITAI_KEY_BY_HOST = {v: k for k, v in CIVITAI_HOST_NAMES.items()}

# 允许下载封面的图片 host（Civitai API 返回的 HTTPS image URL）
CIVITAI_COVER_ALLOWED_HOSTS = {
    "civitai.com",
    "civitai.red",
    "image.civitai.com",
    "www.civitai.com",
}
