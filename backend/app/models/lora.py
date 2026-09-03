from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class LoraBase(SQLModel):
    name: str = Field(index=True)
    filename: str = Field(index=True)
    trigger_words: Optional[str] = Field(default="")
    default_strength: float = Field(default=0.8)
    is_favorite: bool = Field(default=False)
    category: Optional[str] = Field(default="通用")
    is_valid_file: bool = Field(default=True)
    source_path: Optional[str] = Field(default=None)  # 实际来源文件路径（来自来源扫描导入）

    # ── 本地信息（LoRA Metadata V1） ──
    description: str = Field(default="")      # 用户本地描述（Local First：远端永不覆盖）
    cover_hidden: bool = Field(default=False) # 隐藏封面（Card 视图 collapse cover region）

class Lora(LoraBase, table=True):
    __tablename__ = "loras"
    id: Optional[int] = Field(default=None, primary_key=True)
    is_enabled: Optional[bool] = Field(default=None)  # Deprecated legacy column, session isEnabled is managed in workbench
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # ── SHA256 本地缓存（避免每次 GET /api/loras 都 hash 大文件） ──
    sha256: Optional[str] = Field(default=None, index=True)
    sha256_file_size: Optional[int] = Field(default=None)
    sha256_mtime_ns: Optional[int] = Field(default=None)

    # ── Civitai 远端 metadata（V1 仅 Civitai Red/Green） ──
    metadata_provider: Optional[str] = Field(default=None)   # "civitai"
    metadata_host: Optional[str] = Field(default=None)       # "civitai.red" | "civitai.com"
    metadata_status: Optional[str] = Field(default=None)     # matched|not_found|remote_error|rate_limited|local_file_not_found|local_file_ambiguous|hash_file_mismatch
    remote_model_id: Optional[int] = Field(default=None)
    remote_version_id: Optional[int] = Field(default=None)
    remote_file_id: Optional[int] = Field(default=None)
    remote_model_name: Optional[str] = Field(default=None)
    remote_version_name: Optional[str] = Field(default=None)
    remote_file_name: Optional[str] = Field(default=None)    # 仅 metadata，绝不覆盖 Lora.filename
    remote_base_model: Optional[str] = Field(default=None)
    remote_trained_words: Optional[str] = Field(default=None)  # JSON array 字符串（Civitai trainedWords 推荐）
    remote_description: Optional[str] = Field(default=None)    # sanitized plain text（禁止执行远端 HTML）
    remote_creator: Optional[str] = Field(default=None)
    remote_tags: Optional[str] = Field(default=None)           # JSON array 字符串
    remote_nsfw_level: Optional[int] = Field(default=None)
    cached_cover_path: Optional[str] = Field(default=None)     # 本地封面缓存路径（backend/data/cache/lora_metadata/<sha256>/cover.*）
    metadata_fetched_at: Optional[datetime] = Field(default=None)
    metadata_json: Optional[str] = Field(default=None)         # raw normalized payload（不含 token / 本地绝对路径）

class LoraCreate(LoraBase):
    pass

class LoraUpdate(SQLModel):
    name: Optional[str] = None
    filename: Optional[str] = None
    trigger_words: Optional[str] = None
    default_strength: Optional[float] = None
    is_favorite: Optional[bool] = None
    category: Optional[str] = None
    is_valid_file: Optional[bool] = None
    source_path: Optional[str] = None
    description: Optional[str] = None
    cover_hidden: Optional[bool] = None

class LoraRead(LoraBase):
    id: int
    created_at: datetime
    updated_at: datetime
    sha256: Optional[str] = None
    sha256_file_size: Optional[int] = None
    sha256_mtime_ns: Optional[int] = None
    metadata_provider: Optional[str] = None
    metadata_host: Optional[str] = None
    metadata_status: Optional[str] = None
    remote_model_id: Optional[int] = None
    remote_version_id: Optional[int] = None
    remote_file_id: Optional[int] = None
    remote_model_name: Optional[str] = None
    remote_version_name: Optional[str] = None
    remote_file_name: Optional[str] = None
    remote_base_model: Optional[str] = None
    remote_trained_words: Optional[str] = None
    remote_description: Optional[str] = None
    remote_creator: Optional[str] = None
    remote_tags: Optional[str] = None
    remote_nsfw_level: Optional[int] = None
    cached_cover_path: Optional[str] = None
    metadata_fetched_at: Optional[datetime] = None
    metadata_json: Optional[str] = None
