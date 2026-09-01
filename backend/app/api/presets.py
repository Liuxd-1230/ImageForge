from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.preset import Preset, PresetCreate, PresetUpdate, PresetRead
from datetime import datetime

router = APIRouter(prefix="/presets", tags=["presets"])

@router.get("", response_model=List[PresetRead])
def list_presets(session: Session = Depends(get_session)):
    stmt = select(Preset).order_by(Preset.id)
    return session.exec(stmt).all()

@router.post("", response_model=PresetRead)
def create_preset(preset_in: PresetCreate, session: Session = Depends(get_session)):
    if preset_in.is_default:
        # Reset other default presets
        presets = session.exec(select(Preset).where(Preset.is_default == True)).all()
        for p in presets:
            p.is_default = False
            session.add(p)
    preset = Preset.model_validate(preset_in)
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset

@router.put("/{preset_id}", response_model=PresetRead)
def update_preset(
    preset_id: int,
    preset_in: PresetUpdate,
    session: Session = Depends(get_session)
):
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")
    if preset_in.is_default:
        presets = session.exec(select(Preset).where(Preset.is_default == True)).all()
        for p in presets:
            if p.id != preset_id:
                p.is_default = False
                session.add(p)
    data = preset_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(preset, key, value)
    preset.updated_at = datetime.utcnow()
    session.add(preset)
    session.commit()
    session.refresh(preset)
    return preset

@router.delete("/{preset_id}")
def delete_preset(preset_id: int, session: Session = Depends(get_session)):
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="预设不存在")
    session.delete(preset)
    session.commit()
    return {"status": "ok"}
