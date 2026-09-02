from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime
from app.database import get_session
from app.config import settings
from app.models.character import Character, CharacterCreate, CharacterUpdate, CharacterRead
from app.services.character_meta.source import BooruTagSource
from app.services.character_meta.resolver import OnlineCharacterResolver
from app.services.llm.lm_studio import LMStudioProvider

router = APIRouter(prefix="/characters", tags=["characters"])


class ResolveOnlineRequest(BaseModel):
    name: str
    candidate_index: Optional[int] = None  # 多候选时用户选中的下标（确认后写缓存）
    force: bool = False                    # True = “重新解析并替换”（可覆盖 manual）


def _build_online_resolver(session: Session) -> OnlineCharacterResolver:
    llm = None
    try:
        llm = LMStudioProvider(base_url=settings.LM_STUDIO_BASE_URL, api_key=settings.LM_STUDIO_API_KEY)
    except Exception:
        llm = None
    return OnlineCharacterResolver(
        session=session,
        source=BooruTagSource(),
        llm_provider=llm,
        write_cache=settings.ONLINE_RESOLVE_CACHE_WRITE,
        model=settings.LM_STUDIO_MODEL or None,
    )


@router.post("/resolve-online")
async def resolve_online(req: ResolveOnlineRequest, session: Session = Depends(get_session)):
    """Character metadata online lookup (V1).

    status: resolved | ambiguous | not_found | offline
    唯一结果 → 直接写缓存；多候选 → 返回 candidates，由前端让用户选择后
    带 candidate_index 再次调用确认并写缓存。"""
    name = (req.name or "").strip()
    if not name:
        return {"status": "offline", "reason": "empty name"}
    resolver = _build_online_resolver(session)
    try:
        outcome = await resolver.resolve(name)
    except Exception as e:
        return {"status": "offline", "reason": f"{type(e).__name__}: {str(e)[:120]}"}

    if outcome.get("status") == "ambiguous" and req.candidate_index is not None:
        cands = outcome.get("candidates") or []
        if 0 <= req.candidate_index < len(cands):
            confirmed = await resolver.confirm(name, cands[req.candidate_index])
            return confirmed
    return outcome

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
