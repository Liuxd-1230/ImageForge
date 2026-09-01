from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_session
from app.models.history import GenerationHistory, GenerationHistoryBase, GenerationHistoryRead

router = APIRouter(prefix="/history", tags=["history"])

@router.get("", response_model=List[GenerationHistoryRead])
def list_history(session: Session = Depends(get_session)):
    stmt = select(GenerationHistory).order_by(GenerationHistory.created_at.desc()).limit(50)
    return session.exec(stmt).all()

@router.post("", response_model=GenerationHistoryRead)
def add_history(item: GenerationHistoryBase, session: Session = Depends(get_session)):
    record = GenerationHistory.model_validate(item)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record

@router.delete("/{history_id}")
def delete_history(history_id: int, session: Session = Depends(get_session)):
    record = session.get(GenerationHistory, history_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    session.delete(record)
    session.commit()
    return {"status": "ok"}
