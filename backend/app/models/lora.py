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

class Lora(LoraBase, table=True):
    __tablename__ = "loras"
    id: Optional[int] = Field(default=None, primary_key=True)
    is_enabled: Optional[bool] = Field(default=None)  # Deprecated legacy column, session isEnabled is managed in workbench
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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

class LoraRead(LoraBase):
    id: int
    created_at: datetime
    updated_at: datetime
