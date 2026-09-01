from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class AppSettingBase(SQLModel):
    key: str = Field(index=True, unique=True)
    value: str = Field(default="")

class AppSetting(AppSettingBase, table=True):
    __tablename__ = "settings"
    id: Optional[int] = Field(default=None, primary_key=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AppSettingRead(AppSettingBase):
    id: int
    updated_at: datetime
