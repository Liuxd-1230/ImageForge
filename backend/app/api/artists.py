from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models.artist import Artist, ArtistCreate, ArtistUpdate, ArtistRead

router = APIRouter(prefix="/artists", tags=["artists"])

@router.get("", response_model=List[ArtistRead])
def list_artists(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    stmt = select(Artist)
    if category:
        stmt = stmt.where(Artist.category == category)
    if is_favorite is not None:
        stmt = stmt.where(Artist.is_favorite == is_favorite)
    if search:
        stmt = stmt.where(Artist.name.contains(search) | Artist.tags.contains(search))
    return session.exec(stmt).all()

@router.post("", response_model=ArtistRead)
def create_artist(
    artist_in: ArtistCreate,
    session: Session = Depends(get_session)
):
    artist = Artist.model_validate(artist_in)
    session.add(artist)
    session.commit()
    session.refresh(artist)
    return artist

@router.put("/{artist_id}", response_model=ArtistRead)
def update_artist(
    artist_id: int,
    artist_in: ArtistUpdate,
    session: Session = Depends(get_session)
):
    artist = session.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="画师不存在")
    data = artist_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(artist, key, value)
    session.add(artist)
    session.commit()
    session.refresh(artist)
    return artist

@router.delete("/{artist_id}")
def delete_artist(artist_id: int, session: Session = Depends(get_session)):
    artist = session.get(Artist, artist_id)
    if not artist:
        raise HTTPException(status_code=404, detail="画师不存在")
    session.delete(artist)
    session.commit()
    return {"status": "ok"}
