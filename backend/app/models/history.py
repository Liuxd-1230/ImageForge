from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class GenerationHistoryBase(SQLModel):
    raw_input: str
    parsed_facts_json: str = Field(default="{}")
    prompt: str = Field(default="")
    negative_prompt: str = Field(default="")
    safety: str = Field(default="Safe")
    artists_json: str = Field(default="[]")
    loras_json: str = Field(default="[]")
    comfy_params_json: str = Field(default="{}")
    image_path: Optional[str] = Field(default=None)

class GenerationHistory(GenerationHistoryBase, table=True):
    __tablename__ = "generation_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class GenerationHistoryRead(GenerationHistoryBase):
    id: int
    created_at: datetime
