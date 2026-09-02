import asyncio
import json
import os
import time
import uuid
import httpx
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from app.config import settings
from app.services.comfyui.client import ComfyUIClient, ComfyUIValidationError
from app.services.comfyui.workflow import build_anima_29b_workflow
from app.services.comfyui.monitor import get_monitor, CLIENT_ID
from app.models.prompt_engine import LoraBuildItem

router = APIRouter(prefix="/comfyui", tags=["comfyui"])

class GenerateRequest(BaseModel):
    positive_prompt: str
    negative_prompt: str
    unet_name: str = "anima29BInt8Convrot_v10.safetensors"
    clip_name: str = "qwen_3_06b_base.safetensors"
    vae_name: str = "qwen_image_vae.safetensors"
    loras: List[LoraBuildItem] = []
    width: int = 1024
    height: int = 1536
    batch_size: int = 1
    steps: int = 12
    cfg: float = 1.0
    sampler_name: str = "euler"
    scheduler: str = "beta57"
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
    monitor = get_monitor(settings.COMFYUI_BASE_URL)
    try:
        # 先确保 WS 就绪（与提交使用同一 client_id），再提交，避免错过早期状态
        await asyncio.wait_for(monitor.ensure_ws().wait(), timeout=5.0)
        res = await client.queue_prompt(workflow, CLIENT_ID)
        monitor.register(res.get("prompt_id", ""))
        return res
    except asyncio.TimeoutError:
        raise HTTPException(status_code=503, detail={
            "kind": "connection",
            "summary": "ComfyUI 未连接（无法建立状态通道）",
            "detail": "连接 ComfyUI WebSocket 失败",
        })
    except ComfyUIValidationError as e:
        raise HTTPException(status_code=502, detail=parse_validation_error(e.body))
    except (httpx.ConnectError, httpx.ConnectTimeout, OSError) as e:
        raise HTTPException(status_code=503, detail={
            "kind": "connection",
            "summary": "ComfyUI 未连接",
            "detail": str(e),
        })
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail={
            "kind": "comfy_error",
            "summary": f"ComfyUI 提交失败（HTTP {e.response.status_code}）",
            "detail": e.response.text[:2000],
        })


def parse_validation_error(body: str) -> Dict[str, Any]:
    """把 ComfyUI 提交期 400 的 node_errors 变成用户可读分类（A8）。"""
    raw = body
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return {"kind": "workflow_validation", "summary": "Workflow 校验失败", "detail": raw[:2000]}
    node_errors = data.get("node_errors") or {}
    missing = []
    for nid, ne in node_errors.items():
        for err in ne.get("errors", []):
            details = str(err.get("details") or "")
            if "not in list" in (err.get("type") or ""):
                # details like "unet_name: 'foo.safetensors' not in ['a', 'b']"
                missing.append(details[:300])
            else:
                missing.append(details[:300] or str(err.get("message") or details)[:200])
    summary = "Workflow 校验失败"
    if missing:
        first = missing[0]
        if "unet_name" in first or "ckpt_name" in first:
            summary = f"找不到模型：{first.split('not in')[0].strip()}"
        elif "clip_name" in first:
            summary = f"找不到 CLIP 模型：{first.split('not in')[0].strip()}"
        elif "vae_name" in first:
            summary = f"找不到 VAE：{first.split('not in')[0].strip()}"
        elif "lora_name" in first:
            summary = f"找不到 LoRA：{first.split('not in')[0].strip()}"
    return {
        "kind": "workflow_validation",
        "summary": summary,
        "detail": json.dumps(data, ensure_ascii=False)[:3000],
        "missing": missing[:8],
    }


def _queue_prompt_ids(items: List[Any]) -> List[str]:
    out = []
    for it in items or []:
        if isinstance(it, (list, tuple)) and len(it) > 1:
            out.append(str(it[1]))
        elif isinstance(it, dict) and it.get("prompt_id"):
            out.append(str(it["prompt_id"]))
    return out


@router.get("/queue")
async def comfyui_queue():
    client = ComfyUIClient()
    try:
        q = await client.get_queue()
    except Exception as e:
        raise HTTPException(status_code=503, detail={"kind": "connection", "summary": "ComfyUI 未连接", "detail": str(e)})
    running = _queue_prompt_ids(q.get("queue_running", []))
    pending = _queue_prompt_ids(q.get("queue_pending", []))
    return {"queue_running": running, "queue_pending": pending}


@router.get("/status/{prompt_id}")
async def comfyui_status(prompt_id: str):
    monitor = get_monitor(settings.COMFYUI_BASE_URL)
    st = monitor.status(prompt_id)
    client = ComfyUIClient()
    queue_position = None
    try:
        q = await client.get_queue()
        running = _queue_prompt_ids(q.get("queue_running", []))
        pending = _queue_prompt_ids(q.get("queue_pending", []))
        if prompt_id in pending:
            queue_position = pending.index(prompt_id)
        elif prompt_id in running:
            queue_position = 0
    except Exception:
        pass
    if st is None:
        return {
            "prompt_id": prompt_id,
            "stage": "unknown",
            "queue_position": queue_position,
            "is_running": False,
            "is_queued": False,
        }
    return {
        "prompt_id": prompt_id,
        "stage": st["stage"],
        "progress_value": st["progress_value"],
        "progress_max": st["progress_max"],
        "node": st["node"],
        "message": st["message"],
        "error_type": st["error_type"],
        "error_summary": st["error_summary"],
        "error_detail": st["error_detail"],
        "terminal": st["terminal"],
        "queue_position": queue_position,
        "is_running": prompt_id in running,
        "is_queued": prompt_id in pending,
    }


@router.post("/interrupt")
async def comfyui_interrupt():
    """全局 interrupt（ComfyUI 0.34.2 无 task-scoped cancel，DELETE /queue/{id}=405）。
    前端必须仅在本任务确实在运行（queue_running 含本 prompt_id）时才调用，并向用户
    明示这是对 ComfyUI 当前执行任务的全局中断。"""
    client = ComfyUIClient()
    try:
        await client.interrupt()
    except Exception as e:
        raise HTTPException(status_code=502, detail={"kind": "comfy_error", "summary": "中断失败", "detail": str(e)})
    return {"status": "ok"}

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
