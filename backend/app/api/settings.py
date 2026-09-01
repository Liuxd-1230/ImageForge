from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Dict, Any
from app.database import get_session
from app.models.setting import AppSetting
from app.config import settings

router = APIRouter(prefix="/settings", tags=["settings"])

@router.get("")
def get_all_settings(session: Session = Depends(get_session)) -> Dict[str, Any]:
    db_settings = session.exec(select(AppSetting)).all()
    res = {
        "ACTIVE_PROVIDER": settings.ACTIVE_PROVIDER,
        "LM_STUDIO_BASE_URL": settings.LM_STUDIO_BASE_URL,
        "LM_STUDIO_API_KEY": settings.LM_STUDIO_API_KEY,
        "LM_STUDIO_MODEL": settings.LM_STUDIO_MODEL,
        "LM_STUDIO_AUTO_LOAD": settings.LM_STUDIO_AUTO_LOAD,
        "LM_STUDIO_AUTO_UNLOAD": settings.LM_STUDIO_AUTO_UNLOAD,
        "LM_STUDIO_ENABLE_THINKING": settings.LM_STUDIO_ENABLE_THINKING,
        "LM_STUDIO_REASONING_EFFORT": settings.LM_STUDIO_REASONING_EFFORT,
        
        "CLOUD_API_NAME": settings.CLOUD_API_NAME,
        "CLOUD_API_BASE_URL": settings.CLOUD_API_BASE_URL,
        "CLOUD_API_KEY": settings.CLOUD_API_KEY,
        "CLOUD_MODEL": settings.CLOUD_MODEL,
        "CLOUD_REASONING_EFFORT": settings.CLOUD_REASONING_EFFORT,
        
        "COMFYUI_BASE_URL": settings.COMFYUI_BASE_URL,
        "DEFAULT_SAFETY": settings.DEFAULT_SAFETY,
    }
    for s in db_settings:
        # Cast booleans if needed
        val = s.value
        if val.lower() in ["true", "false"]:
            res[s.key] = val.lower() == "true"
        else:
            res[s.key] = val
    return res

@router.post("")
def update_settings(payload: Dict[str, Any], session: Session = Depends(get_session)):
    for k, v in payload.items():
        val_str = str(v)
        setting = session.exec(select(AppSetting).where(AppSetting.key == k)).first()
        if not setting:
            setting = AppSetting(key=k, value=val_str)
            session.add(setting)
        else:
            setting.value = val_str
            session.add(setting)
        if hasattr(settings, k):
            if isinstance(getattr(settings, k), bool):
                setattr(settings, k, v in [True, "True", "true", 1, "1"])
            else:
                setattr(settings, k, v)
    session.commit()
    return {"status": "ok"}
