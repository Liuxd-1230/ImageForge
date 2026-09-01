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
    is_enabled: Optional[bool] = None,
    session: Session = Depends(get_session)
):
    stmt = select(Lora)
    if category:
        stmt = stmt.where(Lora.category == category)
    if is_favorite is not None:
        stmt = stmt.where(Lora.is_favorite == is_favorite)
    if is_enabled is not None:
        stmt = stmt.where(Lora.is_enabled == is_enabled)
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
    """Scans LoRAs from ComfyUI and synchronizes with local DB."""
    client = ComfyUIClient()
    comfy_loras = await client.get_loras()
    
    existing_loras = {l.filename: l for l in session.exec(select(Lora)).all()}
    added = 0
    
    for filename in comfy_loras:
        if filename not in existing_loras:
            name = filename.rsplit(".", 1)[0]
            new_lora = Lora(
                name=name,
                filename=filename,
                trigger_words="",
                default_strength=0.8,
                is_enabled=False,
                is_valid_file=True
            )
            session.add(new_lora)
            added += 1
        else:
            existing_loras[filename].is_valid_file = True
            session.add(existing_loras[filename])

    # Mark missing loras
    for filename, lora in existing_loras.items():
        if filename not in comfy_loras:
            lora.is_valid_file = False
            session.add(lora)

    session.commit()
    return {"status": "ok", "added": added, "total_in_comfyui": len(comfy_loras)}
