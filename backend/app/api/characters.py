from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models.character import Character, CharacterCreate, CharacterUpdate, CharacterRead
from datetime import datetime

router = APIRouter(prefix="/characters", tags=["characters"])

@router.get("", response_model=List[CharacterRead])
def list_characters(
    category: Optional[str] = None,
    search: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    stmt = select(Character)
    if category:
        stmt = stmt.where(Character.category == category)
    if is_favorite is not None:
        stmt = stmt.where(Character.is_favorite == is_favorite)
    if search:
        stmt = stmt.where(Character.name.contains(search) | Character.aliases.contains(search))
    return session.exec(stmt).all()

@router.post("", response_model=CharacterRead)
def create_character(
    char_in: CharacterCreate,
    session: Session = Depends(get_session)
):
    # Check duplicate name
    existing = session.exec(select(Character).where(Character.name == char_in.name)).first()
    if existing:
        raise HTTPException(status_code=400, detail="角色名已存在")
    char = Character.model_validate(char_in)
    session.add(char)
    session.commit()
    session.refresh(char)
    return char

@router.get("/{char_id}", response_model=CharacterRead)
def get_character(char_id: int, session: Session = Depends(get_session)):
    char = session.get(Character, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    return char

@router.put("/{char_id}", response_model=CharacterRead)
def update_character(
    char_id: int,
    char_in: CharacterUpdate,
    session: Session = Depends(get_session)
):
    char = session.get(Character, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    char_data = char_in.model_dump(exclude_unset=True)
    for key, value in char_data.items():
        setattr(char, key, value)
    char.updated_at = datetime.utcnow()
    session.add(char)
    session.commit()
    session.refresh(char)
    return char

@router.delete("/{char_id}")
def delete_character(char_id: int, session: Session = Depends(get_session)):
    char = session.get(Character, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="角色不存在")
    session.delete(char)
    session.commit()
    return {"status": "ok"}
