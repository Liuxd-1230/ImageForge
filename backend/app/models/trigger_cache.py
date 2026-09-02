from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CharacterTriggerCacheBase(SQLModel):
    name: str = Field(index=True, unique=True)
    canonical_tag: str = Field(description="Used in tag section, e.g. lincheng")
    caption_name: str = Field(description="Used in natural language caption, e.g. Lin Cheng")
    series_tag: Optional[str] = Field(default=None, description="Copyright / series tag, e.g. honkai: star rail")
    aliases: Optional[str] = Field(default="", description="Comma-separated aliases (JSON-friendly plain list)")
    source: Optional[str] = Field(default="", description="manual | online | llm")
    resolved_at: Optional[datetime] = Field(default=None, description="Last successful online/llm resolution time")
    notes: Optional[str] = Field(default="")

class CharacterTriggerCache(CharacterTriggerCacheBase, table=True):
    __tablename__ = "character_trigger_cache"
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CharacterTriggerCacheCreate(CharacterTriggerCacheBase):
    pass

class CharacterTriggerCacheUpdate(SQLModel):
    name: Optional[str] = None
    canonical_tag: Optional[str] = None
    caption_name: Optional[str] = None
    series_tag: Optional[str] = None
    aliases: Optional[str] = None
    source: Optional[str] = None
    resolved_at: Optional[datetime] = None
    notes: Optional[str] = None

class CharacterTriggerCacheRead(CharacterTriggerCacheBase):
    id: int
    updated_at: datetime