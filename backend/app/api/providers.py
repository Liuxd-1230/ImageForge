from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlmodel import Session, select
from app.config import settings
from app.database import get_session
from app.models.setting import AppSetting
from app.services.llm.lm_studio import LMStudioProvider
from app.services.llm.openai_compat import OpenAICompatibleProvider

router = APIRouter(prefix="/providers", tags=["providers"])

class LoadModelRequest(BaseModel):
    model: str
    options: Optional[Dict[str, Any]] = None

class UnloadModelRequest(BaseModel):
    model: Optional[str] = None

def get_lm_studio():
    return LMStudioProvider(base_url=settings.LM_STUDIO_BASE_URL, api_key=settings.LM_STUDIO_API_KEY)

def get_cloud_provider():
    return OpenAICompatibleProvider(base_url=settings.CLOUD_API_BASE_URL, api_key=settings.CLOUD_API_KEY)

@router.get("/lm-studio/health")
async def lm_studio_health():
    return await get_lm_studio().check_health()

@router.get("/lm-studio/models")
async def lm_studio_models():
    provider = get_lm_studio()
    try:
        models = await provider.list_models()
        return {"data": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch LM Studio models: {str(e)}")

@router.post("/lm-studio/load")
async def lm_studio_load(req: LoadModelRequest):
    provider = get_lm_studio()
    try:
        return await provider.load_model(req.model, req.options)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to load model: {str(e)}")

@router.post("/lm-studio/unload")
async def lm_studio_unload(req: UnloadModelRequest):
    provider = get_lm_studio()
    try:
        return await provider.unload_model(req.model)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to unload model: {str(e)}")

@router.get("/cloud/health")
async def cloud_health():
    return await get_cloud_provider().check_health()

@router.get("/cloud/models")
async def cloud_models():
    provider = get_cloud_provider()
    try:
        models = await provider.list_models()
        return {"data": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Cloud models: {str(e)}")
