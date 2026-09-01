from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Dict, Any
from app.database import get_session
from app.models.setting import AppSetting
from app.config import settings, EDITABLE_SETTING_KEYS

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
def get_all_settings(session: Session = Depends(get_session)) -> Dict[str, Any]:
    db_settings = session.exec(select(AppSetting)).all()
    res = {k: getattr(settings, k) for k in EDITABLE_SETTING_KEYS if hasattr(settings, k)}
    for s in db_settings:
        if s.key in EDITABLE_SETTING_KEYS:
            val = s.value
            if val.lower() in ["true", "false"]:
                res[s.key] = val.lower() == "true"
            else:
                res[s.key] = val
    return res

@router.post("")
def update_settings(payload: Dict[str, Any], session: Session = Depends(get_session)):
    for k, v in payload.items():
        if k in EDITABLE_SETTING_KEYS and hasattr(settings, k):
            val_str = str(v)
            setting = session.exec(select(AppSetting).where(AppSetting.key == k)).first()
            if not setting:
                setting = AppSetting(key=k, value=val_str)
                session.add(setting)
            else:
                setting.value = val_str
                session.add(setting)
            if isinstance(getattr(settings, k), bool):
                setattr(settings, k, v in [True, "True", "true", 1, "1"])
            else:
                setattr(settings, k, v)
    session.commit()
    return {"status": "ok"}
