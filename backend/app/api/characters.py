from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from app.database import get_session
from app.models.character import Character, CharacterCreate, CharacterUpdate, CharacterRead

router = APIRouter(prefix="/characters", tags=["characters"])

@router.get("", response_model=List[CharacterRead])
def get_characters(session: Session = Depends(get_session)):
    stmt = select(Character).order_by(Character.updated_at.desc())
    return session.exec(stmt).all()

@router.get("/{char_id}", response_model=CharacterRead)
def get_character(char_id: int, session: Session = Depends(get_session)):
    char = session.get(Character, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")
    return char

@router.post("", response_model=CharacterRead)
def create_character(char_in: CharacterCreate, session: Session = Depends(get_session)):
    stmt = select(Character).where(Character.name == char_in.name)
    existing = session.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=400, detail="Character with this name already exists")
    
    char = Character.model_validate(char_in)
    session.add(char)
    session.commit()
    session.refresh(char)
    return char

@router.put("/{char_id}", response_model=CharacterRead)
def update_character(char_id: int, char_in: CharacterUpdate, session: Session = Depends(get_session)):
    char = session.get(Character, char_id)
    if not char:
        raise HTTPException(status_code=404, detail="Character not found")

    update_data = char_in.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] != char.name:
        existing = session.exec(select(Character).where(Character.name == update_data["name"])).first()
        if existing and existing.id != char_id:
            raise HTTPException(status_code=400, detail="另一个同名角色已存在")

    for key, value in update_data.items():
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
        raise HTTPException(status_code=404, detail="Character not found")
    session.delete(char)
    session.commit()
    return {"status": "ok"}
