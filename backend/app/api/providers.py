from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from app.config import settings
from app.services.llm.lm_studio import LMStudioProvider
from app.services.llm.openai_compat import OpenAICompatibleProvider

router = APIRouter(prefix="/providers", tags=["providers"])

class LoadModelRequest(BaseModel):
    model: str
    options: Optional[Dict[str, Any]] = None

class UnloadModelRequest(BaseModel):
    instance_id: Optional[str] = None
    model: Optional[str] = None

@router.get("/lm-studio/health")
async def lm_studio_health(
    base_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None)
):
    target_base = base_url or settings.LM_STUDIO_BASE_URL
    target_key = api_key if api_key is not None else settings.LM_STUDIO_API_KEY
    provider = LMStudioProvider(base_url=target_base, api_key=target_key)
    return await provider.check_health()

@router.get("/lm-studio/models")
async def lm_studio_models(
    base_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None)
):
    target_base = base_url or settings.LM_STUDIO_BASE_URL
    target_key = api_key if api_key is not None else settings.LM_STUDIO_API_KEY
    provider = LMStudioProvider(base_url=target_base, api_key=target_key)
    try:
        models = await provider.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch LM Studio models: {str(e)}")

@router.post("/lm-studio/load")
async def lm_studio_load(req: LoadModelRequest):
    provider = LMStudioProvider(base_url=settings.LM_STUDIO_BASE_URL, api_key=settings.LM_STUDIO_API_KEY)
    try:
        return await provider.load_model(req.model, req.options)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to load model: {str(e)}")

@router.post("/lm-studio/unload")
async def lm_studio_unload(req: UnloadModelRequest):
    provider = LMStudioProvider(base_url=settings.LM_STUDIO_BASE_URL, api_key=settings.LM_STUDIO_API_KEY)
    target_id = req.instance_id or req.model
    if not target_id:
        raise HTTPException(status_code=400, detail="必须提供 instance_id")
    try:
        return await provider.unload_model(target_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to unload model: {str(e)}")

@router.get("/cloud/health")
async def cloud_health(
    base_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None)
):
    target_base = base_url or settings.CLOUD_API_BASE_URL
    target_key = api_key if api_key is not None else settings.CLOUD_API_KEY
    provider = OpenAICompatibleProvider(base_url=target_base, api_key=target_key)
    return await provider.check_health()

@router.get("/cloud/models")
async def cloud_models(
    base_url: Optional[str] = Query(None),
    api_key: Optional[str] = Query(None)
):
    target_base = base_url or settings.CLOUD_API_BASE_URL
    target_key = api_key if api_key is not None else settings.CLOUD_API_KEY
    provider = OpenAICompatibleProvider(base_url=target_base, api_key=target_key)
    try:
        models = await provider.list_models()
        return {"models": models}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch Cloud models: {str(e)}")
