from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List, Optional
from app.database import get_session
from app.models.lora import Lora, LoraCreate, LoraUpdate, LoraRead
from app.services.comfyui.client import ComfyUIClient

router = APIRouter(prefix="/loras", tags=["loras"])

@router.get("", response_model=List[LoraRead])
def list_loras(
    category: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    stmt = select(Lora)
    if category:
        stmt = stmt.where(Lora.category == category)
    if is_favorite is not None:
        stmt = stmt.where(Lora.is_favorite == is_favorite)
    return session.exec(stmt).all()

@router.post("", response_model=LoraRead)
def create_lora(lora_in: LoraCreate, session: Session = Depends(get_session)):
    lora = Lora.model_validate(lora_in)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    return lora

@router.put("/{lora_id}", response_model=LoraRead)
def update_lora(
    lora_id: int,
    lora_in: LoraUpdate,
    session: Session = Depends(get_session)
):
    lora = session.get(Lora, lora_id)
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA不存在")
    data = lora_in.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(lora, key, value)
    session.add(lora)
    session.commit()
    session.refresh(lora)
    return lora

@router.delete("/{lora_id}")
def delete_lora(lora_id: int, session: Session = Depends(get_session)):
    lora = session.get(Lora, lora_id)
    if not lora:
        raise HTTPException(status_code=404, detail="LoRA不存在")
    session.delete(lora)
    session.commit()
    return {"status": "ok"}

@router.post("/sync-comfyui")
async def sync_comfyui_loras(session: Session = Depends(get_session)):
    client = ComfyUIClient()
    comfy_loras = await client.get_loras()
    
    existing = {l.filename: l for l in session.exec(select(Lora)).all()}
    
    for lora_file in comfy_loras:
        if lora_file not in existing:
            # Add new discovered LoRA
            name_guess = lora_file.replace(".safetensors", "").replace("_", " ").title()
            new_lora = Lora(
                name=name_guess,
                filename=lora_file,
                trigger_words="",
                default_strength=0.8,
                category="通用",
                is_valid_file=True
            )
            session.add(new_lora)
        else:
            # Existing LoRA: update file validity without overwriting user customizations
            existing_lora = existing[lora_file]
            if not existing_lora.is_valid_file:
                existing_lora.is_valid_file = True
                session.add(existing_lora)

    for fn, lora_obj in existing.items():
        if fn not in comfy_loras:
            lora_obj.is_valid_file = False
            session.add(lora_obj)
            
    session.commit()
    return {"status": "ok", "total_scanned": len(comfy_loras)}
