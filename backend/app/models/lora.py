from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class LoraBase(SQLModel):
    name: str = Field(index=True)
    filename: str = Field(index=True)
    trigger_words: Optional[str] = Field(default="")
    default_strength: float = Field(default=0.8)
    is_enabled: bool = Field(default=False)
    is_favorite: bool = Field(default=False)
    category: Optional[str] = Field(default="通用")
    is_valid_file: bool = Field(default=True)

class Lora(LoraBase, table=True):
    __tablename__ = "loras"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class LoraCreate(LoraBase):
    pass

class LoraUpdate(SQLModel):
    name: Optional[str] = None
    filename: Optional[str] = None
    trigger_words: Optional[str] = None
    default_strength: Optional[float] = None
    is_enabled: Optional[bool] = None
    is_favorite: Optional[bool] = None
    category: Optional[str] = None
    is_valid_file: Optional[bool] = None

class LoraRead(LoraBase):
    id: int
    created_at: datetime
    updated_at: datetime
