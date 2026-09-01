from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class RuleFileBase(SQLModel):
    name: str = Field(index=True)
    file_type: str = Field(default=".md")
    content: str = Field(default="")
    is_enabled: bool = Field(default=True)
    sort_order: int = Field(default=0)

class RuleFile(RuleFileBase, table=True):
    __tablename__ = "rule_files"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class RuleFileCreate(RuleFileBase):
    pass

class RuleFileUpdate(SQLModel):
    name: Optional[str] = None
    file_type: Optional[str] = None
    content: Optional[str] = None
    is_enabled: Optional[bool] = None
    sort_order: Optional[int] = None

class RuleFileRead(RuleFileBase):
    id: int
    created_at: datetime
    updated_at: datetime
