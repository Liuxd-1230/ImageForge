from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CharacterTriggerCacheBase(SQLModel):
    name: str = Field(index=True, unique=True)
    canonical_tag: str = Field(description="Used in tag section, e.g. suisui")
    caption_name: str = Field(description="Used in natural language caption, e.g. Suisui")
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
    notes: Optional[str] = None

class CharacterTriggerCacheRead(CharacterTriggerCacheBase):
    id: int
    updated_at: datetime
