from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class PresetBase(SQLModel):
    name: str = Field(index=True)
    positive_prefix: str = Field(default="masterpiece, newest, high quality, anime style")
    default_negative: str = Field(default="lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry")
    default_safety: str = Field(default="Safe")
    is_default: bool = Field(default=False)

class Preset(PresetBase, table=True):
    __tablename__ = "presets"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PresetCreate(PresetBase):
    pass

class PresetUpdate(SQLModel):
    name: Optional[str] = None
    positive_prefix: Optional[str] = None
    default_negative: Optional[str] = None
    default_safety: Optional[str] = None
    is_default: Optional[bool] = None

class PresetRead(PresetBase):
    id: int
    created_at: datetime
    updated_at: datetime
