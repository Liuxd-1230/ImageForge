from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class CharacterBase(SQLModel):
    name: str = Field(index=True, unique=True)
    aliases: Optional[str] = Field(default="")  # Comma-separated or JSON
    gender: Optional[str] = Field(default="")
    age_group: Optional[str] = Field(default="")
    body: Optional[str] = Field(default="")
    hair_color: Optional[str] = Field(default="")
    hair_style: Optional[str] = Field(default="")
    hair_length: Optional[str] = Field(default="")
    eye_color: Optional[str] = Field(default="")
    facial_features: Optional[str] = Field(default="")
    headwear: Optional[str] = Field(default="")
    top: Optional[str] = Field(default="")
    outer: Optional[str] = Field(default="")
    bottom: Optional[str] = Field(default="")
    socks: Optional[str] = Field(default="")
    shoes: Optional[str] = Field(default="")
    accessories: Optional[str] = Field(default="")
    default_expression: Optional[str] = Field(default="")
    default_pose: Optional[str] = Field(default="")
    negative_traits: Optional[str] = Field(default="")
    extra_description: Optional[str] = Field(default="")
    category: Optional[str] = Field(default="默认")
    is_favorite: bool = Field(default=False)

class Character(CharacterBase, table=True):
    __tablename__ = "characters"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CharacterCreate(CharacterBase):
    pass

class CharacterUpdate(SQLModel):
    name: Optional[str] = None
    aliases: Optional[str] = None
    gender: Optional[str] = None
    age_group: Optional[str] = None
    body: Optional[str] = None
    hair_color: Optional[str] = None
    hair_style: Optional[str] = None
    hair_length: Optional[str] = None
    eye_color: Optional[str] = None
    facial_features: Optional[str] = None
    headwear: Optional[str] = None
    top: Optional[str] = None
    outer: Optional[str] = None
    bottom: Optional[str] = None
    socks: Optional[str] = None
    shoes: Optional[str] = None
    accessories: Optional[str] = None
    default_expression: Optional[str] = None
    default_pose: Optional[str] = None
    negative_traits: Optional[str] = None
    extra_description: Optional[str] = None
    category: Optional[str] = None
    is_favorite: Optional[bool] = None

class CharacterRead(CharacterBase):
    id: int
    created_at: datetime
    updated_at: datetime
