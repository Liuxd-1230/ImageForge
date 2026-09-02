from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import Dict, Any
from app.database import get_session
from app.models.setting import AppSetting
from app.config import settings, EDITABLE_SETTING_KEYS

router = APIRouter(prefix="/settings", tags=["settings"])

def _coerce(key: str, raw) -> Any:
    """按 Setting 的声明类型转换（GET 从 DB 读字符串 / POST 收任意 JSON 值共用）。

    - bool：接受 True/1/"true"/"1"/"yes"；
    - int：GENERATE_TIMEOUT_SECONDS 即使收到字符串 "300" 也转成 int；
    - str：数字形式的 API Key / model 名保持 string，绝不无差别 int 化。
    """
    field_type = type(getattr(settings, key, ""))
    if field_type == bool:
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes")
    if field_type == int:
        try:
            return int(raw)
        except (TypeError, ValueError):
            return getattr(settings, key)
    if field_type == str:
        return raw if isinstance(raw, str) else str(raw)
    return raw

@router.get("")
def get_all_settings(session: Session = Depends(get_session)) -> Dict[str, Any]:
    db_settings = session.exec(select(AppSetting)).all()
    res = {k: getattr(settings, k) for k in EDITABLE_SETTING_KEYS if hasattr(settings, k)}
    for s in db_settings:
        if s.key in EDITABLE_SETTING_KEYS:
            res[s.key] = _coerce(s.key, s.value)
    return res

@router.post("")
def update_settings(payload: Dict[str, Any], session: Session = Depends(get_session)):
    for k, v in payload.items():
        if k in EDITABLE_SETTING_KEYS and hasattr(settings, k):
            coerced = _coerce(k, v)  # 运行时与存储均按声明类型
            setting = session.exec(select(AppSetting).where(AppSetting.key == k)).first()
            if not setting:
                setting = AppSetting(key=k, value=str(coerced))
                session.add(setting)
            else:
                setting.value = str(coerced)
                session.add(setting)
            setattr(settings, k, coerced)
    session.commit()
    return {"status": "ok"}
