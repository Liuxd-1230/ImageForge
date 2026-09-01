from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class ArtistBase(SQLModel):
    name: str = Field(index=True)
    tags: str = Field(description="Artist tags, e.g. artist:abc or artist_name")
    category: Optional[str] = Field(default="综合")
    is_favorite: bool = Field(default=False)
    is_custom: bool = Field(default=False)
    preview_url: Optional[str] = Field(default="")
    description: Optional[str] = Field(default="")

class Artist(ArtistBase, table=True):
    __tablename__ = "artists"
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ArtistCreate(ArtistBase):
    pass

class ArtistUpdate(SQLModel):
    name: Optional[str] = None
    tags: Optional[str] = None
    category: Optional[str] = None
    is_favorite: Optional[bool] = None
    is_custom: Optional[bool] = None
    preview_url: Optional[str] = None
    description: Optional[str] = None

class ArtistRead(ArtistBase):
    id: int
    created_at: datetime
    updated_at: datetime
