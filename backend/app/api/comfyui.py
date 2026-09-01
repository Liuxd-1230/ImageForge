import os
import time
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.config import settings
from app.services.comfyui.client import ComfyUIClient
from app.services.comfyui.workflow import build_anima_29b_workflow
from app.models.prompt_engine import LoraBuildItem

router = APIRouter(prefix="/comfyui", tags=["comfyui"])

class GenerateRequest(BaseModel):
    positive_prompt: str
    negative_prompt: str
    unet_name: str = "anima29B_v10.safetensors"
    clip_name: str = "qwen_3_06b_base.safetensors"
    vae_name: str = "qwen_image_vae.safetensors"
    loras: List[LoraBuildItem] = []
    width: int = 1024
    height: int = 1536
    batch_size: int = 1
    steps: int = 28
    cfg: float = 4.5
    sampler_name: str = "euler"
    scheduler: str = "sgm_uniform"
    seed: Optional[int] = -1
    client_id: str = "imageforge_client"
    custom_template: Optional[Dict[str, Any]] = None
    override_models: bool = False

class TestComfyRequest(BaseModel):
    base_url: Optional[str] = None

@router.post("/test")
async def comfyui_test(req: TestComfyRequest):
    target_base = req.base_url or settings.COMFYUI_BASE_URL
    client = ComfyUIClient(base_url=target_base)
    return await client.check_health()

@router.get("/health")
async def comfyui_health():
    client = ComfyUIClient()
    return await client.check_health()

@router.get("/checkpoints")
async def comfyui_checkpoints():
    client = ComfyUIClient()
    checkpoints = await client.get_checkpoints()
    return {"checkpoints": checkpoints}

@router.get("/loras")
async def comfyui_loras():
    client = ComfyUIClient()
    loras = await client.get_loras()
    return {"loras": loras}

@router.post("/generate")
async def comfyui_generate(req: GenerateRequest):
    client = ComfyUIClient()
    workflow = build_anima_29b_workflow(
        positive_prompt=req.positive_prompt,
        negative_prompt=req.negative_prompt,
        unet_name=req.unet_name,
        clip_name=req.clip_name,
        vae_name=req.vae_name,
        loras=req.loras,
        width=req.width,
        height=req.height,
        batch_size=req.batch_size,
        steps=req.steps,
        cfg=req.cfg,
        sampler_name=req.sampler_name,
        scheduler=req.scheduler,
        seed=req.seed,
        custom_template=req.custom_template,
        override_models=req.override_models
    )
    try:
        res = await client.queue_prompt(workflow, req.client_id)
        return res
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ComfyUI 生图任务提交失败: {str(e)}")

@router.get("/history/{prompt_id}")
async def comfyui_history(prompt_id: str):
    client = ComfyUIClient()
    try:
        return await client.get_history(prompt_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取 ComfyUI 历史失败: {str(e)}")

@router.get("/view")
async def comfyui_view_image(
    filename: str = Query(...),
    subfolder: str = Query(""),
    type: str = Query("output")
):
    base_url = settings.COMFYUI_BASE_URL.rstrip("/")
    target_url = f"{base_url}/view?filename={filename}&subfolder={subfolder}&type={type}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(target_url)
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "image/png")
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"获取 ComfyUI 图像失败: {str(e)}")


class PersistImageRequest(BaseModel):
    filename: str
    subfolder: str = ""
    type: str = "output"


@router.post("/persist-image")
async def persist_image(req: PersistImageRequest):
    """Download a finished image from ComfyUI into ImageForge's own
    data/generated directory so history survives ComfyUI output cleanup.
    The original ComfyUI view URL is returned as metadata."""
    base_url = settings.COMFYUI_BASE_URL.rstrip("/")
    target_url = f"{base_url}/view?filename={req.filename}&subfolder={req.subfolder}&type={req.type}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(target_url)
            resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"从 ComfyUI 下载图像失败: {str(e)}")

    os.makedirs(settings.GENERATED_DIR, exist_ok=True)
    ext = os.path.splitext(req.filename)[1] or ".png"
    if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        ext = ".png"
    saved = f"anima_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}{ext}"
    local_path = os.path.join(settings.GENERATED_DIR, saved)
    try:
        with open(local_path, "wb") as f:
            f.write(resp.content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存图像失败: {str(e)}")

    return {
        "image_path": f"/api/comfyui/generated/{saved}",
        "local_path": local_path,
        "comfy_view_url": target_url,
        "original_filename": req.filename,
    }


@router.get("/generated/{filename}")
async def generated_image(filename: str):
    """Serve ImageForge's own persisted generated image (safe filename check)."""
    safe = os.path.basename(filename)
    if safe != filename or not safe:
        raise HTTPException(status_code=400, detail="非法文件名")
    path = os.path.join(settings.GENERATED_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="图像不存在")
    return FileResponse(path)
