from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class LoraSourceBase(SQLModel):
    display_path: str = Field(index=True)
    resolved_path: str = Field(default="", index=True)
    enabled: bool = Field(default=True)
    recursive: bool = Field(default=True)

class LoraSource(LoraSourceBase, table=True):
    __tablename__ = "lora_sources"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class LoraSourceCreate(SQLModel):
    display_path: str
    enabled: bool = True
    recursive: bool = True

class LoraSourceUpdate(SQLModel):
    enabled: Optional[bool] = None
    recursive: Optional[bool] = None

class LoraSourceRead(LoraSourceBase):
    id: int
    created_at: datetime
